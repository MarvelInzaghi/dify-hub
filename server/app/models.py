from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Prompt(Base):
    """An editable prompt template (draft state). Published snapshots live in PromptVersion."""

    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    # Dify app mode this prompt renders into: "completion" | "chat"
    mode: Mapped[str] = mapped_column(String(16), default="completion")
    # The template body, containing `{{variable}}` placeholders.
    content: Mapped[str] = mapped_column(Text, default="")
    # Variable schema: list of {name, label, type, description, required, default}.
    variables: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    latest_published_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Dify app created for the latest published version (Console API).
    dify_app_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    versions: Mapped[list["PromptVersion"]] = relationship(
        back_populates="prompt", order_by="PromptVersion.version_number"
    )


class PromptVersion(Base):
    """Immutable published snapshot of a prompt template."""

    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("prompt_id", "version_number", name="uq_prompt_version_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    variables: Mapped[list] = mapped_column(JSON, default=list)
    changelog: Mapped[str] = mapped_column(Text, default="")
    # Dify app id this version was rendered into (nullable if render was skipped/failed).
    dify_app_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    prompt: Mapped["Prompt"] = relationship(back_populates="versions")


class Skill(Base):
    """Our registry entry for a Dify-managed skill.

    Dify owns the skill content and versions (via Console API); this table stores the
    platform-level metadata (category, share info) plus the mapping to Dify's skill id
    and the pinned published version.
    """

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dify_skill_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    latest_dify_skill_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Publication(Base):
    """An execution contract exposed to external consumers.

    Maps a published prompt/agent to the Dify app that runs it (``dify_app_id``) plus its
    Service API token, the mode (completion/chat) and the variable schema for validation.
    """

    __tablename__ = "publications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    item_type: Mapped[str] = mapped_column(String(16), default="prompt")  # "prompt" | "agent"
    item_id: Mapped[str] = mapped_column(String(36), index=True)
    pinned_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="completion")  # "completion" | "chat"
    dify_app_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Service API token for the Dify app. TODO: encrypt at rest before prod.
    service_api_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variable_schema: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="published")  # published | archived
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ApiKey(Base):
    """External consumer credential for the public (run-only) API.

    Only a sha256 hash of the key is stored; the plaintext is returned once at creation.
    ``scopes`` is a list of publication slugs, or ``["*"]`` for all.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    key_prefix: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scopes: Mapped[list] = mapped_column(JSON, default=lambda: ["*"])
    quota: Mapped[int] = mapped_column(Integer, default=-1)  # total requests; -1 = unlimited
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | revoked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Usage(Base):
    """Audit/log row for a public API execution."""

    __tablename__ = "usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    api_key_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("api_keys.id"), nullable=True, index=True)
    publication_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok | error
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
