from __future__ import annotations


class DifyAdapterError(Exception):
    """Base error for anything raised by the Dify adapter."""


class DifyConfigError(DifyAdapterError):
    """The adapter is misconfigured (missing auth strategy, missing workspace id, ...)."""


class DifyAuthError(DifyAdapterError):
    """Login or token refresh failed."""


class DifyAPIError(DifyAdapterError):
    """Dify returned a non-2xx response."""

    def __init__(
        self,
        *,
        method: str,
        url: str,
        status_code: int,
        code: str | None,
        message: str | None,
        body: object,
    ) -> None:
        self.method = method
        self.url = url
        self.status_code = status_code
        self.code = code
        self.message = message
        self.body = body
        super().__init__(f"{method} {url} -> {status_code} {code or ''} {message or ''}".strip())

    @classmethod
    def from_response(cls, method: str, url: str, response) -> "DifyAPIError":
        body: object = None
        code: str | None = None
        message: str | None = None
        try:
            body = response.json()
        except Exception:
            body = response.text
        if isinstance(body, dict):
            code = body.get("code")
            message = body.get("message")
        return cls(method=method, url=url, status_code=response.status_code, code=code, message=message, body=body)
