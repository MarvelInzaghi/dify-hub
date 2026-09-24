from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Usage
from app.schemas import UsageOut

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=list[UsageOut])
def list_usage(limit: int = 200, session: Session = Depends(get_db)) -> list[UsageOut]:
    return list(session.scalars(select(Usage).order_by(Usage.created_at.desc()).limit(limit)).all())
