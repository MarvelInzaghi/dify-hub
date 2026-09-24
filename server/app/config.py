from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the dify-hub platform.

    Loaded from environment variables (see ``.env.example``). Every Dify coupling is
    declared here so the rest of the codebase never hardcodes a Dify URL or credential.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # The Dify version this adapter was written and tested against. Bumped only after
    # an upgrade smoke-test passes (see plan: "Adapter 版本映射").
    dify_target_version: str = "1.17.0"

    # Base URL of the Dify deployment (nginx entry point). Console API is served at
    # `{dify_base_url}/console/api`, Service API at `{dify_base_url}/v1`.
    dify_base_url: str = "http://localhost"

    # --- Console API auth (pick ONE strategy) -------------------------
    # Strategy A: admin API key (server-to-server, recommended). Requires Dify env:
    #   ADMIN_API_KEY_ENABLE=true  ADMIN_API_KEY=<secret>
    # Resolves to the workspace owner identified by `dify_workspace_id`.
    dify_admin_api_key: str | None = None
    dify_workspace_id: str | None = None

    # Strategy B: email/password cookie session (fallback). The password is sent
    # base64-encoded (Dify's `decrypt_password_field` == base64 decode).
    dify_email: str | None = None
    dify_password: str | None = None

    # --- Model used when rendering a prompt into a Dify app -------------
    # The model-config write only needs `pre_prompt` + `prompt_type: "simple"`; anything
    # else (model provider/name/params) is environment-specific and supplied as JSON here.
    # e.g. DIFY_DEFAULT_MODEL_CONFIG_JSON='{"model": {"provider": "openai", "name": "gpt-4o"}}'
    dify_default_model_config_json: str = "{}"

    # --- Own database (independent Postgres in prod; SQLite for dev/tests) ---
    database_url: str = "sqlite:///./dify_hub.db"

    # --- HTTP ---------------------------------------------------------
    http_timeout: float = 60.0

    # --- Security / hardening ----------------------------------------
    # Secret used to derive the key for encrypting sensitive tokens (Dify Service API
    # tokens) at rest. MUST be overridden with a strong random value in production.
    secret_key: str = "dev-insecure-change-me"

    # Per-key rate limit (requests per minute) for the public run API; <=0 disables.
    rate_limit_per_minute: int = 60

    # --- OpenAPI → MCP bridge ------------------------------------------
    # Public host used to build the returned MCP service URL (the address MCP clients use).
    mcp_public_host: str = "127.0.0.1"
    # Host the MCP worker binds to (0.0.0.0 = all interfaces).
    mcp_bind_host: str = "0.0.0.0"
    # Streamable-http mount path for each MCP service.
    mcp_path: str = "/mcp"
    # Python interpreter used to run the MCP worker (separate env with fastmcp).
    # Empty = use the backend's own interpreter (sys.executable).
    mcp_worker_python: str = ""

    @property
    def console_api_base(self) -> str:
        return self.dify_base_url.rstrip("/") + "/console/api"

    @property
    def dify_default_model_config(self) -> dict:
        """Parsed ``dify_default_model_config_json`` (empty dict on parse failure)."""
        if not self.dify_default_model_config_json:
            return {}
        try:
            parsed = json.loads(self.dify_default_model_config_json)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
