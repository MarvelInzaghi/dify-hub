from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_dify
from app.dify_adapter import DifyAPIError
from app.schemas import (
    SkillBind,
    SkillCreate,
    SkillDetailOut,
    SkillFileOp,
    SkillFileUpsert,
    SkillListOut,
    SkillOut,
    SkillPublish,
    SkillUpdate,
)
from app.services.skill_service import (
    DifyNotConfiguredError,
    SkillConflictError,
    SkillNotFoundError,
    SkillService,
)

router = APIRouter(prefix="/skills", tags=["skills"])


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SkillNotFoundError):
        return HTTPException(status_code=404, detail="Skill not found")
    if isinstance(exc, SkillConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, DifyNotConfiguredError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, DifyAPIError):
        return HTTPException(status_code=exc.status_code, detail=exc.message or str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _svc(session: Session, dify) -> SkillService:
    return SkillService(session, dify)


@router.post("", response_model=SkillOut, status_code=201)
def create_skill(payload: SkillCreate, session: Session = Depends(get_db), dify=Depends(get_dify)) -> SkillOut:
    try:
        return _svc(session, dify).create(payload)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get("", response_model=SkillListOut)
def list_skills(
    page: int = 1,
    limit: int = 20,
    keyword: str | None = None,
    category: str | None = None,
    session: Session = Depends(get_db),
    dify=Depends(get_dify),
) -> SkillListOut:
    try:
        items, total = SkillService(session, dify).list(page=page, limit=limit, keyword=keyword, category=category)
        return SkillListOut(data=[SkillOut.model_validate(i) for i in items], page=page, limit=limit, total=total)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post("/import", response_model=SkillOut, status_code=201)
def import_skill(file: UploadFile = File(...), session: Session = Depends(get_db), dify=Depends(get_dify)) -> SkillOut:
    try:
        content = file.file.read()
        return _svc(session, dify).import_skill(content=content, filename=file.filename or "skill.zip")
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get("/{skill_id}", response_model=SkillDetailOut)
def get_skill(skill_id: str, session: Session = Depends(get_db), dify=Depends(get_dify)) -> SkillDetailOut:
    try:
        return SkillDetailOut.model_validate(_svc(session, dify).detail(skill_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.patch("/{skill_id}", response_model=SkillOut)
def update_skill(skill_id: str, payload: SkillUpdate, session: Session = Depends(get_db), dify=Depends(get_dify)) -> SkillOut:
    try:
        return _svc(session, dify).update(skill_id, payload)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.delete("/{skill_id}", status_code=204, response_model=None)
def delete_skill(skill_id: str, session: Session = Depends(get_db), dify=Depends(get_dify)) -> None:
    try:
        _svc(session, dify).delete(skill_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.put("/{skill_id}/files", response_model=dict)
def upsert_file(
    skill_id: str, payload: SkillFileUpsert, session: Session = Depends(get_db), dify=Depends(get_dify)
) -> dict:
    try:
        return _svc(session, dify).upsert_file(skill_id, path=payload.path, content=payload.content)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post("/{skill_id}/file-op", response_model=dict)
def file_op(skill_id: str, payload: SkillFileOp, session: Session = Depends(get_db), dify=Depends(get_dify)) -> dict:
    try:
        return _svc(session, dify).file_op(
            skill_id, operation=payload.operation, path=payload.path, target_path=payload.target_path, content=payload.content
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post("/{skill_id}/publish", response_model=dict)
def publish_skill(skill_id: str, payload: SkillPublish, session: Session = Depends(get_db), dify=Depends(get_dify)) -> dict:
    try:
        return _svc(session, dify).publish(skill_id, changelog=payload.changelog, version_name=payload.version_name)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get("/{skill_id}/versions", response_model=dict)
def list_versions(skill_id: str, session: Session = Depends(get_db), dify=Depends(get_dify)) -> dict:
    try:
        return _svc(session, dify).list_versions(skill_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get("/{skill_id}/export")
def export_skill(skill_id: str, session: Session = Depends(get_db), dify=Depends(get_dify)) -> Response:
    try:
        content, name = _svc(session, dify).export(skill_id)
        return Response(
            content=content,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{name}.zip"'},
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get("/{skill_id}/manifest")
def skill_manifest(skill_id: str, session: Session = Depends(get_db), dify=Depends(get_dify)) -> dict:
    try:
        return _svc(session, dify).manifest(skill_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.put("/agent/{agent_id}/bind", response_model=dict)
def bind_skills(agent_id: str, payload: SkillBind, session: Session = Depends(get_db), dify=Depends(get_dify)) -> dict:
    try:
        return _svc(session, dify).bind_to_agent(agent_id, skill_ids=payload.skill_ids)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
