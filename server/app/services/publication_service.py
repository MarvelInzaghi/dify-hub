from __future__ import annotations

import copy

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Prompt, Publication
from app.security import encrypt_token
from app.services.prompt_service import PromptService


class PublicationNotFoundError(Exception):
    pass


class PublicationService:
    """Turns a published prompt into an external, runnable publication.

    Publishing a prompt reuses :class:`PromptService.publish` (version snapshot + render to a
    Dify app), then resolves the app's Service API token and upserts a ``Publication`` row.
    """

    def __init__(self, session: Session, dify=None) -> None:
        self._session = session
        self._dify = dify

    def publish_prompt(self, prompt_id: str, *, slug: str, changelog: str = "") -> Publication:
        version = PromptService(self._session, dify=self._dify).publish(prompt_id, changelog)
        prompt = self._session.get(Prompt, prompt_id)
        token = self._get_or_create_app_token(version.dify_app_id) if version.dify_app_id else None

        pub = self._session.scalar(select(Publication).where(Publication.slug == slug))
        if pub is None:
            pub = Publication(slug=slug, name=prompt.display_name, item_type="prompt", item_id=prompt_id)
            self._session.add(pub)
        pub.name = prompt.display_name
        pub.pinned_version_id = version.id
        pub.mode = prompt.mode
        pub.dify_app_id = version.dify_app_id
        pub.service_api_token = encrypt_token(token)
        pub.variable_schema = copy.deepcopy(prompt.variables)
        pub.status = "published"
        self._session.commit()
        self._session.refresh(pub)
        return pub

    def get_by_slug(self, slug: str) -> Publication:
        pub = self._session.scalar(select(Publication).where(Publication.slug == slug))
        if pub is None:
            raise PublicationNotFoundError(slug)
        return pub

    def list(self, *, page: int = 1, limit: int = 20) -> tuple[list[Publication], int]:
        base = select(Publication)
        total = self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self._session.scalars(
            base.order_by(Publication.updated_at.desc()).offset((page - 1) * limit).limit(limit)
        ).all()
        return list(items), total

    def _get_or_create_app_token(self, app_id: str) -> str | None:
        if self._dify is None:
            return None
        keys = (self._dify.apps.list_api_keys(app_id) or {}).get("data") or []  # type: ignore[union-attr]
        if keys:
            return keys[0].get("token")
        created = self._dify.apps.create_api_key(app_id)  # type: ignore[union-attr]
        return created.get("token")
