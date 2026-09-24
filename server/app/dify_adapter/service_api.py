from __future__ import annotations

from typing import Any

import httpx

from app.dify_adapter.errors import DifyAPIError


class DifyServiceClient:
    """Thin HTTP client for Dify's Service API (the official, stable public API).

    Execution goes through here. Auth is per-app: each published prompt/agent has its own
    Service API token (``app-`` prefix), passed as ``Authorization: Bearer <token>``.
    """

    def __init__(self, *, base_url: str, timeout: float) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout, follow_redirects=False)

    def close(self) -> None:
        self._client.close()

    def completion_message(
        self,
        app_token: str,
        *,
        inputs: dict[str, Any],
        user: str,
        response_mode: str = "blocking",
    ) -> httpx.Response:
        return self._post(
            "/v1/completion-messages",
            app_token,
            {"inputs": inputs, "user": user, "response_mode": response_mode},
        )

    def chat_message(
        self,
        app_token: str,
        *,
        inputs: dict[str, Any],
        query: str,
        user: str,
        response_mode: str = "blocking",
        conversation_id: str | None = None,
    ) -> httpx.Response:
        body: dict[str, Any] = {"inputs": inputs, "query": query, "user": user, "response_mode": response_mode}
        if conversation_id:
            body["conversation_id"] = conversation_id
        return self._post("/v1/chat-messages", app_token, body)

    def _post(self, path: str, app_token: str, body: dict[str, Any]) -> httpx.Response:
        resp = self._client.post(path, json=body, headers={"Authorization": f"Bearer {app_token}"})
        if resp.is_error:
            raise DifyAPIError.from_response("POST", str(resp.request.url), resp)
        return resp
