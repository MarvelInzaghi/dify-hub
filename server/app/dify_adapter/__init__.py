from __future__ import annotations

from app.config import Settings
from app.dify_adapter.apps import AppsClient
from app.dify_adapter.client import DifyConsoleClient
from app.dify_adapter.errors import DifyAdapterError, DifyAPIError, DifyAuthError, DifyConfigError
from app.dify_adapter.skills import SkillsClient


class DifyClient:
    """Top-level facade over Dify's Console API (skills + apps).

    The single entry point the rest of the platform uses to talk to Dify. Nothing outside
    ``app.dify_adapter`` imports httpx or hardcodes a Dify URL. Service API execution is
    added in Phase 3.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = DifyConsoleClient(
            base_url=settings.dify_base_url,
            timeout=settings.http_timeout,
            admin_api_key=settings.dify_admin_api_key,
            workspace_id=settings.dify_workspace_id,
            email=settings.dify_email,
            password=settings.dify_password,
        )
        self.skills = SkillsClient(self._client)
        self.apps = AppsClient(self._client)

    @property
    def auth_mode(self) -> str:
        return self._client.auth_mode

    def close(self) -> None:
        self._client.close()


__all__ = [
    "DifyClient",
    "DifyConsoleClient",
    "SkillsClient",
    "AppsClient",
    "DifyAdapterError",
    "DifyAPIError",
    "DifyAuthError",
    "DifyConfigError",
]
