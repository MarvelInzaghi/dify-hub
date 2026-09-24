from __future__ import annotations

import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.dify_adapter.errors import DifyAPIError
from app.models import ApiKey, Publication, Usage
from app.security import decrypt_token


class ExecutionError(Exception):
    pass


class ExecutionValidationError(Exception):
    pass


class ExecutionService:
    """Runs a publication against Dify's Service API and records usage.

    ``service_client`` is a :class:`~app.dify_adapter.service_api.DifyServiceClient`. For
    ``response_mode="streaming"`` the raw httpx response is returned (caller streams it);
    otherwise the parsed JSON body is returned.
    """

    def __init__(self, session: Session, service_client) -> None:
        self._session = session
        self._service = service_client

    def run(
        self,
        publication: Publication,
        *,
        inputs: dict,
        query: str | None = None,
        user: str = "anonymous",
        response_mode: str = "blocking",
        conversation_id: str | None = None,
        api_key_id: str | None = None,
    ):
        self._validate(publication, inputs)
        app_token = decrypt_token(publication.service_api_token)
        if not app_token or not publication.dify_app_id:
            raise ExecutionError("Publication is not deployed to Dify.")

        start = time.perf_counter()
        try:
            if publication.mode == "chat":
                resp = self._service.chat_message(
                    app_token,
                    inputs=inputs,
                    query=query or "",
                    user=user,
                    response_mode=response_mode,
                    conversation_id=conversation_id,
                )
            else:
                resp = self._service.completion_message(
                    app_token,
                    inputs=inputs,
                    user=user,
                    response_mode=response_mode,
                )
        except DifyAPIError as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._record(publication, api_key_id, latency_ms, "error", None, None, None, str(exc))
            raise ExecutionError(str(exc)) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        if response_mode == "streaming":
            self._record(publication, api_key_id, latency_ms, "ok", None, None, None, None)
            return resp

        data = resp.json()
        # Dify 1.x nests usage under `metadata.usage`; older releases returned a top-level
        # `usage`. Accept both so token accounting keeps working across Dify upgrades.
        usage = data.get("usage") or (data.get("metadata") or {}).get("usage") or {}
        self._record(
            publication,
            api_key_id,
            latency_ms,
            "ok",
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
            None,
        )
        return data

    def _validate(self, publication: Publication, inputs: dict) -> None:
        required = [
            v["name"]
            for v in publication.variable_schema
            if isinstance(v, dict) and v.get("required")
        ]
        missing = [r for r in required if r not in inputs or inputs[r] in (None, "")]
        if missing:
            raise ExecutionValidationError(f"Missing required inputs: {missing}")

    def _record(
        self,
        publication: Publication,
        api_key_id: str | None,
        latency_ms: int,
        status: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int | None,
        error: str | None,
    ) -> None:
        self._session.add(
            Usage(
                api_key_id=api_key_id,
                publication_id=publication.id,
                mode=publication.mode,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                status=status,
                error=error,
            )
        )
        if api_key_id:
            key = self._session.get(ApiKey, api_key_id)
            if key is not None:
                key.last_used_at = datetime.now(UTC)
        self._session.commit()
