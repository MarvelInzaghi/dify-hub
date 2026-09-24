from __future__ import annotations

from typing import Any, Literal

from app.dify_adapter.client import DifyConsoleClient

AppMode = Literal["chat", "agent-chat", "advanced-chat", "workflow", "completion"]


class AppsClient:
    """Console API wrapper for application creation and model-config.

    Shapes mirror ``api/controllers/console/app/app.py`` (CreateAppPayload) and
    ``api/controllers/console/app/model_config.py`` (ModelConfigRequest).
    """

    def __init__(self, client: DifyConsoleClient) -> None:
        self._c = client

    def create(
        self,
        *,
        name: str,
        mode: AppMode,
        description: str | None = None,
        icon: str | None = None,
        icon_background: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "mode": mode}
        if description is not None:
            body["description"] = description
        if icon is not None:
            body["icon"] = icon
        if icon_background is not None:
            body["icon_background"] = icon_background
        return self._c.request("POST", "/apps", json=body).json()

    def get(self, app_id: str) -> dict[str, Any]:
        return self._c.request("GET", f"/apps/{app_id}").json()

    def set_model_config(self, app_id: str, *, config: dict[str, Any]) -> dict[str, Any]:
        """Write the app's model config (prompt + model + params) in one request.

        ``config`` is the full Dify model-config dict (``pre_prompt`` for simple prompts,
        or ``prompt_type`` + ``chat_prompt_config`` / ``completion_prompt_config`` for
        advanced prompts, plus model provider/model name/configs). A valid config requires
        the workspace's model provider settings; use :meth:`get` to inspect the default
        shape for an existing app before constructing one.
        """
        return self._c.request("POST", f"/apps/{app_id}/model-config", json=config).json()

    def list_api_keys(self, app_id: str) -> dict[str, Any]:
        """List an app's Service API keys (each ``{id, token, ...}``)."""
        return self._c.request("GET", f"/apps/{app_id}/api-keys").json()

    def create_api_key(self, app_id: str) -> dict[str, Any]:
        """Create a new Service API key for an app; returns ``{id, token, ...}``.

        Keys are capped (Dify allows max 10 per app), so callers should reuse existing keys
        via :meth:`list_api_keys` when possible.
        """
        return self._c.request("POST", f"/apps/{app_id}/api-keys").json()
