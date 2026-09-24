from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_dify
from app.prompt_template import extract_variables, render
from app.schemas import (
    PromptCreate,
    PromptListOut,
    PromptOut,
    PromptPreview,
    PromptPublish,
    PromptRestore,
    PromptUpdate,
    PromptVersionOut,
    VariableListOut,
)
from app.services.prompt_service import (
    PromptConflictError,
    PromptNotFoundError,
    PromptService,
    PromptValidationError,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=PromptOut, status_code=201)
def create_prompt(payload: PromptCreate, session: Session = Depends(get_db)) -> PromptOut:
    try:
        return PromptService(session).create(payload)
    except PromptConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=PromptListOut)
def list_prompts(
    page: int = 1,
    limit: int = 20,
    keyword: str | None = None,
    tags: list[str] | None = Query(default=None),
    session: Session = Depends(get_db),
) -> PromptListOut:
    items, total = PromptService(session).list(page=page, limit=limit, keyword=keyword, tags=tags)
    return PromptListOut(data=[PromptOut.model_validate(i) for i in items], page=page, limit=limit, total=total)


@router.get("/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: str, session: Session = Depends(get_db)) -> PromptOut:
    try:
        return PromptService(session).get(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc


@router.patch("/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: str, payload: PromptUpdate, session: Session = Depends(get_db)) -> PromptOut:
    try:
        return PromptService(session).update(prompt_id, payload)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc


@router.delete("/{prompt_id}", status_code=204, response_model=None)
def delete_prompt(prompt_id: str, session: Session = Depends(get_db)) -> None:
    try:
        PromptService(session).delete(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc


@router.post("/{prompt_id}/publish", response_model=PromptVersionOut)
def publish_prompt(
    prompt_id: str,
    payload: PromptPublish,
    session: Session = Depends(get_db),
    dify=Depends(get_dify),
) -> PromptVersionOut:
    try:
        return PromptService(session, dify=dify).publish(prompt_id, payload.changelog)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc
    except PromptValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{prompt_id}/versions", response_model=list[PromptVersionOut])
def list_versions(prompt_id: str, session: Session = Depends(get_db)) -> list[PromptVersionOut]:
    try:
        return PromptService(session).list_versions(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc


@router.get("/{prompt_id}/versions/{version_id}", response_model=PromptVersionOut)
def get_version(prompt_id: str, version_id: str, session: Session = Depends(get_db)) -> PromptVersionOut:
    try:
        return PromptService(session).get_version(prompt_id, version_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Version not found") from exc


@router.post("/{prompt_id}/restore", response_model=PromptOut)
def restore_prompt(prompt_id: str, payload: PromptRestore, session: Session = Depends(get_db)) -> PromptOut:
    try:
        return PromptService(session).restore_version(prompt_id, payload.version_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt or version not found") from exc


@router.get("/{prompt_id}/variables", response_model=VariableListOut)
def list_variables(prompt_id: str, session: Session = Depends(get_db)) -> VariableListOut:
    try:
        prompt = PromptService(session).get(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc
    return VariableListOut(data=extract_variables(prompt.content))


@router.post("/{prompt_id}/preview", response_model=dict[str, str])
def preview_prompt(prompt_id: str, payload: PromptPreview, session: Session = Depends(get_db)) -> dict[str, str]:
    try:
        prompt = PromptService(session).get(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Prompt not found") from exc
    return {"rendered": render(prompt.content, payload.values)}
