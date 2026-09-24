from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_dify
from app.schemas import PublicationOut, PublicationPublishRequest
from app.services.prompt_service import PromptNotFoundError, PromptValidationError
from app.services.publication_service import PublicationService

router = APIRouter(prefix="/publications", tags=["publications"])


@router.post("", response_model=PublicationOut, status_code=201)
def publish_prompt(payload: PublicationPublishRequest, session: Session = Depends(get_db), dify=Depends(get_dify)) -> PublicationOut:
    try:
        return PublicationService(session, dify).publish_prompt(payload.prompt_id, slug=payload.slug, changelog=payload.changelog)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc
    except PromptValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[PublicationOut])
def list_publications(session: Session = Depends(get_db)) -> list[PublicationOut]:
    items, _ = PublicationService(session).list(limit=200)
    return items
