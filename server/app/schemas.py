from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class VariableSchema(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,29}$")
    label: str | None = None
    type: Literal["string", "number", "boolean"] = "string"
    description: str | None = None
    required: bool = False
    default: str | None = None


class PromptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]([a-z0-9_-]{0,63})$")
    display_name: str = Field(min_length=1, max_length=128)
    description: str = ""
    mode: Literal["completion", "chat"] = "completion"
    content: str = ""
    variables: list[VariableSchema] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class PromptUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    mode: Literal["completion", "chat"] | None = None
    content: str | None = None
    variables: list[VariableSchema] | None = None
    tags: list[str] | None = None


class PromptPublish(BaseModel):
    changelog: str = ""


class PromptRestore(BaseModel):
    version_id: str


class PromptPreview(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class PromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    description: str
    mode: str
    content: str
    variables: list[VariableSchema]
    tags: list[str]
    latest_published_version_id: str | None
    dify_app_id: str | None
    created_at: datetime
    updated_at: datetime


class PromptVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prompt_id: str
    version_number: int
    content: str
    variables: list[VariableSchema]
    changelog: str
    dify_app_id: str | None
    created_at: datetime


class PromptListOut(BaseModel):
    data: list[PromptOut]
    page: int
    limit: int
    total: int


class VariableListOut(BaseModel):
    data: list[str]


# --- Skills -----------------------------------------------------------


class SkillCreate(BaseModel):
    name: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    display_name: str = Field(min_length=1, max_length=128)
    description: str = ""
    icon: str = "📄"
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class SkillUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    icon: str | None = None
    category: str | None = None
    tags: list[str] | None = None


class SkillFileUpsert(BaseModel):
    path: str = Field(min_length=1)
    content: str


class SkillPublish(BaseModel):
    changelog: str = ""
    version_name: str | None = None


class SkillFileOp(BaseModel):
    operation: Literal["upsert_text", "mkdir", "rename", "delete"]
    path: str = Field(min_length=1)
    target_path: str | None = None
    content: str | None = None


class SkillBind(BaseModel):
    skill_ids: list[str] = Field(default_factory=list)


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dify_skill_id: str
    name: str
    display_name: str
    description: str
    category: str | None
    tags: list[str]
    latest_dify_skill_version_id: str | None
    created_at: datetime
    updated_at: datetime


class SkillDetailOut(SkillOut):
    files: list[dict] = Field(default_factory=list)
    latest_published_version_number: int | None = None
    latest_published_at: int | None = None


class SkillListOut(BaseModel):
    data: list[SkillOut]
    page: int
    limit: int
    total: int


# --- Publications / execution ---------------------------------------


class PublicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    item_type: str
    item_id: str
    pinned_version_id: str | None
    mode: str
    dify_app_id: str | None
    variable_schema: list[VariableSchema]
    status: str
    created_at: datetime
    updated_at: datetime


class RunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    query: str | None = None
    user: str = "anonymous"
    response_mode: Literal["blocking", "streaming"] = "blocking"
    conversation_id: str | None = None


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=lambda: ["*"])
    quota: int = -1


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    quota: int
    status: str
    created_at: datetime
    last_used_at: datetime | None


class ApiKeyCreated(ApiKeyOut):
    api_key: str = ""  # plaintext secret, returned once at creation


class PublicationPublishRequest(BaseModel):
    prompt_id: str
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    changelog: str = ""


class UsageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    api_key_id: str | None
    publication_id: str | None
    mode: str | None
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    status: str
    error: str | None
    created_at: datetime


# --- MCP bridge ------------------------------------------------------


class McpServerCreate(BaseModel):
    openapi_url: str
    name: str = Field(min_length=1, max_length=64)
    port: int | None = None


class McpServerOut(BaseModel):
    name: str
    port: int
    mcp_url: str
    openapi_url: str
    started_at: datetime
