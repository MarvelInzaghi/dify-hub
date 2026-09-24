from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ApiKey, Usage
from app.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreated, status_code=201)
def create_api_key(payload: ApiKeyCreate, session: Session = Depends(get_db)) -> ApiKeyCreated:
    raw = "dhk_" + secrets.token_urlsafe(32)
    key = ApiKey(
        name=payload.name,
        key_prefix=raw[:12],
        key_hash=hashlib.sha256(raw.encode()).hexdigest(),
        scopes=payload.scopes,
        quota=payload.quota,
    )
    session.add(key)
    session.commit()
    session.refresh(key)
    out = ApiKeyCreated.model_validate(key)
    out.api_key = raw  # only time the plaintext is returned
    return out


@router.get("", response_model=list[ApiKeyOut])
def list_api_keys(session: Session = Depends(get_db)) -> list[ApiKeyOut]:
    return list(session.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())).all())


@router.post("/{key_id}/revoke", status_code=204, response_model=None)
def revoke_api_key(key_id: str, session: Session = Depends(get_db)) -> None:
    key = session.get(ApiKey, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    # 彻底删除：先清空用量记录对 key 的引用，再删除 key 本身。
    session.execute(update(Usage).where(Usage.api_key_id == key_id).values(api_key_id=None))
    session.delete(key)
    session.commit()
