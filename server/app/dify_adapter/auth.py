from __future__ import annotations

import base64
import logging

import httpx

from app.dify_adapter.errors import DifyAuthError, DifyConfigError

logger = logging.getLogger(__name__)

_CSRF_COOKIE_SUFFIX = "csrf_token"


class AuthStrategy:
    """Chooses and holds the Console API auth state for an httpx client.

    Strategy A (admin key): sets ``Authorization: Bearer <key>`` + ``X-WORKSPACE-ID``
        and is otherwise stateless (Dify resolves it to the workspace owner).
    Strategy B (cookie): performs email/password login, keeps the cookie jar + CSRF
        header in sync, and can refresh the session on demand.
    """

    def __init__(
        self,
        *,
        prefix: str,
        admin_api_key: str | None,
        workspace_id: str | None,
        email: str | None,
        password: str | None,
    ) -> None:
        self._prefix = prefix.rstrip("/")
        self._admin_api_key = admin_api_key
        self._workspace_id = workspace_id
        self._email = email
        self._password = password
        self.mode = "admin_key" if admin_api_key else "cookie"

    def configure_client(self, client: httpx.Client) -> None:
        if self.mode == "admin_key":
            if not self._workspace_id:
                raise DifyConfigError("dify_workspace_id is required with admin API key auth.")
            client.headers["Authorization"] = f"Bearer {self._admin_api_key}"
            client.headers["X-WORKSPACE-ID"] = self._workspace_id
            return
        self._login(client)

    def refresh(self, client: httpx.Client) -> None:
        """Re-issue cookies after the access token expires (cookie mode only)."""
        if self.mode != "cookie":
            return
        resp = client.post(f"{self._prefix}/refresh-token")
        if resp.status_code != 200:
            raise DifyAuthError(f"Token refresh failed: {resp.status_code} {resp.text[:200]}")
        self._sync_csrf_header(client)

    def _login(self, client: httpx.Client) -> None:
        if not self._email or not self._password:
            raise DifyConfigError("dify_email and dify_password are required for cookie auth.")
        # Dify's `decrypt_password_field` == base64 decode, so the password is base64-encoded.
        password_b64 = base64.b64encode(self._password.encode()).decode()
        resp = client.post(
            f"{self._prefix}/login",
            json={"email": self._email, "password": password_b64, "remember_me": True},
        )
        if resp.status_code != 200:
            raise DifyAuthError(f"Login failed: {resp.status_code} {resp.text[:200]}")
        self._sync_csrf_header(client)

    @staticmethod
    def _sync_csrf_header(client: httpx.Client) -> None:
        # The csrf_token cookie may be prefixed (`__Host-csrf_token`) when served over
        # https without a cookie domain, so match by suffix rather than exact name.
        for cookie in client.cookies.jar:
            if cookie.name.endswith(_CSRF_COOKIE_SUFFIX):
                client.headers["X-CSRF-Token"] = cookie.value
                return
        logger.warning("No csrf_token cookie found; CSRF-protected endpoints may return 401.")
