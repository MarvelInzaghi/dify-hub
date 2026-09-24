from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all dify-hub ORM models."""


_engine = None
_session_factory: sessionmaker | None = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        _engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _session_factory


def init_db() -> None:
    """Apply pending Alembic migrations.

    Runs at startup for dev convenience. For multi-replica production, run
    ``alembic upgrade head`` as a separate deploy step instead of inside the app.
    """
    from alembic import command
    from alembic.config import Config

    base_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(base_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(base_dir / "migrations"))
    command.upgrade(cfg, "head")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped Session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
