from __future__ import annotations

import copy
import logging

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Prompt, PromptVersion
from app.prompt_template import extract_variables
from app.schemas import PromptCreate, PromptUpdate

logger = logging.getLogger(__name__)

_VAR_TYPE_MAP = {"string": "text-input", "number": "number", "boolean": "checkbox"}


def _build_user_input_form(variables: list) -> list[dict]:
    """Map a prompt's variable schema to Dify's ``user_input_form``.

    Without this Dify does not recognise ``{{var}}`` placeholders as variables, so the
    Service API ``inputs`` never get substituted into ``pre_prompt``.
    """
    form: list[dict] = []
    for v in variables:
        if not isinstance(v, dict) or not v.get("name"):
            continue
        name = v["name"]
        vtype = _VAR_TYPE_MAP.get(v.get("type"), "text-input")
        field: dict = {
            "variable": name,
            "label": v.get("label") or name,
            "required": bool(v.get("required")),
            "description": v.get("description") or "",
            "default": v.get("default") or "",
        }
        form.append({vtype: field})
    return form


class PromptNotFoundError(Exception):
    pass


class PromptConflictError(Exception):
    pass


class PromptValidationError(Exception):
    pass


class PromptService:
    """Business logic for the prompt library.

    ``dify`` is optional: when provided (a :class:`~app.dify_adapter.DifyClient`), publishing
    also renders the prompt into a Dify app. Without it, publishing only creates the snapshot.
    """

    def __init__(self, session: Session, dify=None) -> None:
        self._session = session
        self._dify = dify

    # --- CRUD ---------------------------------------------------------

    def create(self, data: PromptCreate) -> Prompt:
        if self._session.scalar(select(Prompt).where(Prompt.name == data.name)):
            raise PromptConflictError(f"Prompt name '{data.name}' already exists.")
        prompt = Prompt(
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            mode=data.mode,
            content=data.content,
            variables=[v.model_dump() for v in data.variables],
            tags=data.tags,
        )
        self._session.add(prompt)
        self._session.commit()
        self._session.refresh(prompt)
        return prompt

    def list(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        keyword: str | None = None,
        tags: list[str] | None = None,
    ) -> tuple[list[Prompt], int]:
        base = select(Prompt)
        if keyword:
            like = f"%{keyword}%"
            base = base.where(or_(Prompt.name.ilike(like), Prompt.display_name.ilike(like)))
        if tags:
            # Portable JSON-list tag filter (Python-side; fine at current scale).
            rows = self._session.scalars(base.order_by(Prompt.updated_at.desc())).all()
            tagset = set(tags)
            rows = [p for p in rows if tagset.intersection(p.tags or [])]
            total = len(rows)
            return rows[(page - 1) * limit : page * limit], total
        total = self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self._session.scalars(
            base.order_by(Prompt.updated_at.desc()).offset((page - 1) * limit).limit(limit)
        ).all()
        return list(items), total

    def get(self, prompt_id: str) -> Prompt:
        prompt = self._session.get(Prompt, prompt_id)
        if prompt is None:
            raise PromptNotFoundError(prompt_id)
        return prompt

    def update(self, prompt_id: str, data: PromptUpdate) -> Prompt:
        prompt = self.get(prompt_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "variables" and value is not None:
                value = [v if isinstance(v, dict) else v.model_dump() for v in value]
            setattr(prompt, field, value)
        self._session.commit()
        self._session.refresh(prompt)
        return prompt

    def delete(self, prompt_id: str) -> None:
        prompt = self.get(prompt_id)
        # Versions reference the prompt via FK without ON DELETE CASCADE; delete them first.
        self._session.execute(delete(PromptVersion).where(PromptVersion.prompt_id == prompt_id))
        self._session.delete(prompt)
        self._session.commit()

    # --- Versioning / publish ----------------------------------------

    def publish(self, prompt_id: str, changelog: str = "") -> PromptVersion:
        prompt = self.get(prompt_id)
        self._validate_variables(prompt)

        max_number = self._session.scalar(
            select(func.max(PromptVersion.version_number)).where(PromptVersion.prompt_id == prompt_id)
        )
        next_number = (max_number or 0) + 1

        version = PromptVersion(
            prompt_id=prompt_id,
            version_number=next_number,
            content=prompt.content,
            variables=copy.deepcopy(prompt.variables),
            changelog=changelog,
        )
        self._session.add(version)
        self._session.flush()  # assign version.id before the Dify render

        if self._dify is not None:
            try:
                app_id = prompt.dify_app_id or self._create_dify_app(prompt)
                version.dify_app_id = app_id
                prompt.dify_app_id = app_id
                self._write_dify_model_config(app_id, prompt)
            except Exception as exc:  # noqa: BLE001 - render failure must not block the snapshot
                logger.warning("Dify render failed for prompt %s (snapshot still created): %s", prompt_id, exc)

        prompt.latest_published_version_id = version.id
        self._session.commit()
        self._session.refresh(version)
        return version

    def list_versions(self, prompt_id: str) -> list[PromptVersion]:
        self.get(prompt_id)  # 404 if prompt missing
        return list(
            self._session.scalars(
                select(PromptVersion).where(PromptVersion.prompt_id == prompt_id).order_by(PromptVersion.version_number.desc())
            ).all()
        )

    def get_version(self, prompt_id: str, version_id: str) -> PromptVersion:
        version = self._session.get(PromptVersion, version_id)
        if version is None or version.prompt_id != prompt_id:
            raise PromptNotFoundError(version_id)
        return version

    def restore_version(self, prompt_id: str, version_id: str) -> Prompt:
        """Restore a published version's content + variables back into the editable draft."""
        prompt = self.get(prompt_id)
        version = self.get_version(prompt_id, version_id)
        prompt.content = version.content
        prompt.variables = copy.deepcopy(version.variables)
        self._session.commit()
        self._session.refresh(prompt)
        return prompt

    # --- Helpers ------------------------------------------------------

    def _validate_variables(self, prompt: Prompt) -> None:
        referenced = set(extract_variables(prompt.content))
        defined = {v.get("name") for v in prompt.variables if isinstance(v, dict)}
        missing = referenced - defined
        if missing:
            raise PromptValidationError(f"Undefined variables referenced in content: {sorted(missing)}")

    def _create_dify_app(self, prompt: Prompt) -> str:
        app = self._dify.apps.create(name=prompt.display_name, mode=prompt.mode)  # type: ignore[union-attr]
        return app["id"]

    def _write_dify_model_config(self, app_id: str, prompt: Prompt) -> None:
        settings = get_settings()
        config: dict = dict(settings.dify_default_model_config)
        config.update(
            {
                "pre_prompt": prompt.content,
                "prompt_type": "simple",
                "user_input_form": _build_user_input_form(prompt.variables),
            }
        )
        self._dify.apps.set_model_config(app_id, config=config)  # type: ignore[union-attr]
