from __future__ import annotations

from typing import Any

import httpx

from app.dify_adapter.auth import AuthStrategy
from app.dify_adapter.errors import DifyAPIError

_CONSOLE_API_PREFIX = "/console/api"


class DifyConsoleClient:
    """Thin HTTP client for Dify's Console API.

    All Dify coupling lives in this module and its siblings (auth/skills/apps). No other
    part of the platform imports httpx against Dify directly. This is the single seam that
    absorbs Console API contract drift across Dify upgrades.
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float,
        admin_api_key: str | None,
        workspace_id: str | None,
        email: str | None,
        password: str | None,
    ) -> None:
        origin = base_url.rstrip("/")
        self._client = httpx.Client(base_url=origin, timeout=timeout, follow_redirects=False)
        self._auth = AuthStrategy(
            prefix=_CONSOLE_API_PREFIX,
            admin_api_key=admin_api_key,
            workspace_id=workspace_id,
            email=email,
            password=password,
        )
        self._auth.configure_client(self._client)

    @property
    def auth_mode(self) -> str:
        return self._auth.mode

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        files: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Perform an authenticated Console API request and return the raw response.

        ``path`` is relative to the Console API prefix (``/console/api``). ``files`` is
        passed through to httpx for multipart uploads (e.g. skill package import). Raises
        :class:`DifyAPIError` on any non-2xx after a single cookie-session refresh retry.
        """
        full_path = _CONSOLE_API_PREFIX + path
        resp = self._client.request(method, full_path, params=params, json=json, files=files)
        if resp.status_code == 401 and self._auth.mode == "cookie":
            self._auth.refresh(self._client)
            resp = self._client.request(method, full_path, params=params, json=json, files=files)
        if resp.is_error:
            raise DifyAPIError.from_response(method, str(resp.request.url), resp)
        return resp
