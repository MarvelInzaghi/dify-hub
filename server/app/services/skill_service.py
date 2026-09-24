from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Skill
from app.schemas import SkillCreate, SkillUpdate


class SkillNotFoundError(Exception):
    pass


class SkillConflictError(Exception):
    pass


class DifyNotConfiguredError(Exception):
    pass


class SkillService:
    """Business logic for the skill registry, delegating content to Dify via the adapter.

    Dify is required for every operation (it owns skill content/versions). ``dify`` must be a
    :class:`~app.dify_adapter.DifyClient`; raise :class:`DifyNotConfiguredError` otherwise.
    """

    def __init__(self, session: Session, dify) -> None:
        self._session = session
        self._dify = dify

    # --- CRUD ---------------------------------------------------------

    def create(self, data: SkillCreate) -> Skill:
        self._require_dify()
        if data.name and self._session.scalar(select(Skill).where(Skill.name == data.name)):
            raise SkillConflictError(f"Skill name '{data.name}' already exists.")
        created = self._dify.skills.create(  # type: ignore[union-attr]
            name=data.name,
            display_name=data.display_name,
            icon=data.icon,
            description=data.description,
            tags=data.tags,
        )
        skill = Skill(
            dify_skill_id=created["id"],
            name=created.get("name") or created["id"],
            display_name=data.display_name,
            description=data.description,
            category=data.category,
            tags=data.tags,
            latest_dify_skill_version_id=created.get("latest_published_version_id"),
        )
        self._session.add(skill)
        self._session.commit()
        self._session.refresh(skill)
        return skill

    def import_skill(self, *, content: bytes, filename: str) -> Skill:
        """Import a skill zip package via Dify, then register it locally."""
        self._require_dify()
        imported = self._dify.skills.import_skill(content=content, filename=filename)  # type: ignore[union-attr]
        name = imported.get("name") or imported["id"]
        if self._session.scalar(select(Skill).where(Skill.name == name)):
            raise SkillConflictError(f"Skill name '{name}' already exists.")
        skill = Skill(
            dify_skill_id=imported["id"],
            name=name,
            display_name=imported.get("display_name") or name,
            description=imported.get("description") or "",
            category=None,
            tags=[],
            latest_dify_skill_version_id=None,
        )
        self._session.add(skill)
        self._session.commit()
        self._session.refresh(skill)
        return skill

    def list(self, *, page: int = 1, limit: int = 20, keyword: str | None = None, category: str | None = None) -> tuple[list[Skill], int]:
        self._require_dify()
        self._sync_from_dify()
        base = select(Skill)
        if keyword:
            like = f"%{keyword}%"
            base = base.where(or_(Skill.name.ilike(like), Skill.display_name.ilike(like)))
        if category:
            base = base.where(Skill.category == category)
        total = self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self._session.scalars(
            base.order_by(Skill.updated_at.desc()).offset((page - 1) * limit).limit(limit)
        ).all()
        return list(items), total

    def get(self, skill_id: str) -> Skill:
        skill = self._session.get(Skill, skill_id)
        if skill is None:
            raise SkillNotFoundError(skill_id)
        return skill

    def detail(self, skill_id: str) -> dict:
        """Registry metadata merged with Dify's draft detail (files, version number)."""
        skill = self.get(skill_id)
        self._require_dify()
        d = self._dify.skills.get(skill.dify_skill_id)  # type: ignore[union-attr]
        return {
            "id": skill.id,
            "dify_skill_id": skill.dify_skill_id,
            "name": skill.name,
            "display_name": skill.display_name,
            "description": skill.description,
            "category": skill.category,
            "tags": skill.tags,
            "latest_dify_skill_version_id": skill.latest_dify_skill_version_id,
            "created_at": skill.created_at,
            "updated_at": skill.updated_at,
            "files": d.get("files", []),
            "latest_published_version_number": d.get("latest_published_version_number"),
            "latest_published_at": d.get("latest_published_at"),
        }

    def update(self, skill_id: str, data: SkillUpdate) -> Skill:
        skill = self.get(skill_id)
        self._require_dify()
        self._dify.skills.update_metadata(  # type: ignore[union-attr]
            skill.dify_skill_id,
            display_name=data.display_name,
            icon=data.icon,
            tags=data.tags,
        )
        for field in ("display_name", "description", "icon", "category", "tags"):
            value = getattr(data, field)
            if value is not None:
                setattr(skill, field, value)
        self._session.commit()
        self._session.refresh(skill)
        return skill

    def delete(self, skill_id: str) -> None:
        skill = self.get(skill_id)
        self._require_dify()
        self._dify.skills.delete(skill.dify_skill_id)  # type: ignore[union-attr]
        self._session.delete(skill)
        self._session.commit()

    # --- Files / versions / binding ----------------------------------

    def upsert_file(self, skill_id: str, *, path: str, content: str) -> dict:
        skill = self.get(skill_id)
        self._require_dify()
        return self._dify.skills.upsert_text_file(skill.dify_skill_id, path=path, content=content)  # type: ignore[union-attr]

    def file_op(
        self,
        skill_id: str,
        *,
        operation: str,
        path: str,
        target_path: str | None = None,
        content: str | None = None,
    ) -> dict:
        skill = self.get(skill_id)
        self._require_dify()
        dify = self._dify.skills  # type: ignore[union-attr]
        if operation == "upsert_text":
            return dify.upsert_text_file(skill.dify_skill_id, path=path, content=content or "")
        if operation == "mkdir":
            return dify.mkdir(skill.dify_skill_id, path=path)
        if operation == "rename":
            return dify.rename_file(skill.dify_skill_id, path=path, target_path=target_path or "")
        if operation == "delete":
            return dify.delete_file(skill.dify_skill_id, path=path)
        raise ValueError(f"Unsupported file operation: {operation}")

    def publish(self, skill_id: str, *, changelog: str = "", version_name: str | None = None) -> dict:
        skill = self.get(skill_id)
        self._require_dify()
        version = self._dify.skills.publish(skill.dify_skill_id, publish_note=changelog, version_name=version_name)  # type: ignore[union-attr]
        skill.latest_dify_skill_version_id = version.get("id")
        self._session.commit()
        return version

    def list_versions(self, skill_id: str) -> dict:
        skill = self.get(skill_id)
        self._require_dify()
        return self._dify.skills.list_versions(skill.dify_skill_id)  # type: ignore[union-attr]

    def export(self, skill_id: str) -> tuple[bytes, str]:
        """Download the published skill package as a zip; returns (zip_bytes, filename)."""
        skill = self.get(skill_id)
        self._require_dify()
        content = self._dify.skills.export(skill.dify_skill_id)  # type: ignore[union-attr]
        return content, skill.name

    def manifest(self, skill_id: str) -> dict:
        """Return the skill's SKILL.md content + metadata for prompt injection by external agents."""
        d = self.detail(skill_id)
        skill_md = ""
        for f in d.get("files") or []:
            if f.get("path") == "SKILL.md":
                skill_md = f.get("content") or ""
                break
        return {
            "name": d["name"],
            "display_name": d["display_name"],
            "description": d["description"],
            "skill_md": skill_md,
            "version": d.get("latest_published_version_number"),
        }

    def bind_to_agent(self, agent_id: str, *, skill_ids: list[str]) -> dict:
        self._require_dify()
        dify_ids = [self.get(sid).dify_skill_id for sid in skill_ids]
        return self._dify.skills.replace_agent_bindings(agent_id, skill_ids=dify_ids)  # type: ignore[union-attr]

    # --- Helpers ------------------------------------------------------

    def _require_dify(self) -> None:
        if self._dify is None:
            raise DifyNotConfiguredError("Dify is not configured; skill management requires a Dify connection.")

    def _sync_from_dify(self) -> None:
        """Reconcile the local registry with Dify (the source of truth for skills).

        Adds skills created directly in Dify, updates changed fields, and drops rows whose
        ``dify_skill_id`` no longer exists in Dify.
        """
        dify_skills: list[dict] = []
        page = 1
        limit = 100
        while True:
            resp = self._dify.skills.list(page=page, limit=limit)  # type: ignore[union-attr]
            dify_skills.extend(resp.get("data") or [])
            if not resp.get("has_more"):
                break
            page += 1

        dify_ids = {s["id"] for s in dify_skills}
        for skill in self._session.scalars(select(Skill)).all():
            if skill.dify_skill_id not in dify_ids:
                self._session.delete(skill)

        for ds in dify_skills:
            ds_id = ds["id"]
            name = ds.get("name") or ds_id
            display_name = ds.get("display_name") or name
            description = ds.get("description") or ""
            tags = ds.get("tags") or []
            latest_version_id = ds.get("latest_published_version_id")
            skill = self._session.scalar(select(Skill).where(Skill.dify_skill_id == ds_id))
            if skill is None:
                skill = Skill(
                    dify_skill_id=ds_id,
                    name=name,
                    display_name=display_name,
                    description=description,
                    category=None,
                    tags=tags,
                    latest_dify_skill_version_id=latest_version_id,
                )
                self._session.add(skill)
            else:
                skill.name = name
                skill.display_name = display_name
                skill.description = description
                skill.tags = tags
                skill.latest_dify_skill_version_id = latest_version_id
        self._session.commit()
