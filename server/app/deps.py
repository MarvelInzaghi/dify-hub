from __future__ import annotations

import logging

from app.config import get_settings
from app.dify_adapter import DifyAdapterError, DifyClient
from app.dify_adapter.service_api import DifyServiceClient

logger = logging.getLogger(__name__)

_dify_client: DifyClient | None = None
_dify_client_attempted = False

_service_client: DifyServiceClient | None = None


def get_dify() -> DifyClient | None:
    """Lazily build a cached DifyClient, or return None when auth is not configured.

    Cookie-session auth performs a login network call, so construction is deferred until the
    first request that actually needs Dify (publish). Admin-key auth is stateless/cheap.
    """
    global _dify_client, _dify_client_attempted
    if _dify_client_attempted:
        return _dify_client
    _dify_client_attempted = True

    settings = get_settings()
    if settings.dify_admin_api_key or (settings.dify_email and settings.dify_password):
        try:
            _dify_client = DifyClient(settings)
        except DifyAdapterError as exc:
            logger.warning("Dify client init failed; renders disabled: %s", exc)
            _dify_client = None
    return _dify_client


def get_service_client() -> DifyServiceClient:
    """Lazily build a cached Service API client (cheap; token is per-call)."""
    global _service_client
    if _service_client is None:
        settings = get_settings()
        _service_client = DifyServiceClient(base_url=settings.dify_base_url, timeout=settings.http_timeout)
    return _service_client
