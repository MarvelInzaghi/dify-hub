from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_service_client
from app.models import ApiKey, Usage
from app.schemas import RunRequest
from app.services.execution_service import ExecutionError, ExecutionService, ExecutionValidationError
from app.services.publication_service import PublicationNotFoundError, PublicationService

router = APIRouter(prefix="/v1", tags=["public"])


def _resolve_api_key(request: Request, session: Session) -> ApiKey:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    key_hash = hashlib.sha256(auth[len("Bearer ") :].encode()).hexdigest()
    key = session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if key is None or key.status != "active":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key


def _check_scope(key: ApiKey, slug: str) -> None:
    scopes = key.scopes or []
    if "*" in scopes or slug in scopes:
        return
    raise HTTPException(status_code=403, detail="API key not authorized for this publication")


def _check_quota(key: ApiKey, session: Session) -> None:
    if key.quota < 0:
        return
    used = session.scalar(select(func.count(Usage.id)).where(Usage.api_key_id == key.id)) or 0
    if used >= key.quota:
        raise HTTPException(status_code=429, detail="Quota exceeded")


def _check_rate_limit(key: ApiKey, session: Session) -> None:
    limit = get_settings().rate_limit_per_minute
    if limit <= 0:
        return
    cutoff = datetime.now(UTC) - timedelta(minutes=1)
    recent = (
        session.scalar(select(func.count(Usage.id)).where(Usage.api_key_id == key.id, Usage.created_at > cutoff)) or 0
    )
    if recent >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


@router.post("/run/{slug}")
def run(
    slug: str,
    payload: RunRequest,
    request: Request,
    session: Session = Depends(get_db),
    service_client=Depends(get_service_client),
):
    api_key = _resolve_api_key(request, session)

    try:
        publication = PublicationService(session).get_by_slug(slug)
    except PublicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Publication not found") from exc

    _check_scope(api_key, publication.slug)
    _check_quota(api_key, session)
    _check_rate_limit(api_key, session)

    executor = ExecutionService(session, service_client)
    try:
        result = executor.run(
            publication,
            inputs=payload.inputs,
            query=payload.query,
            user=payload.user,
            response_mode=payload.response_mode,
            conversation_id=payload.conversation_id,
            api_key_id=api_key.id,
        )
    except ExecutionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if payload.response_mode == "streaming":
        def gen():
            for line in result.iter_lines():
                if line:
                    yield line + "\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    return result
