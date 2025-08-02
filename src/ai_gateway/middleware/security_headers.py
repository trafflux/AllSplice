from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

DEFAULT_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "()",  # minimal safe defaults; extend per product needs
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Conditionally applies a curated set of security headers to all responses.
    Toggle via settings.ENABLE_SECURITY_HEADERS (wired in app factory).
    """

    def __init__(self, app: Any, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled: bool = enabled

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        if not self.enabled:
            return response

        for k, v in DEFAULT_SECURITY_HEADERS.items():
            # Do not overwrite if already set by downstream handlers
            response.headers.setdefault(k, v)
        return response
