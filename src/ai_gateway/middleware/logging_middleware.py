from __future__ import annotations

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ai_gateway.logging.setup import RequestLogger, configure_logging


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a request-scoped structured logger and emits access logs.

    It does NOT construct application settings. It reads LOG_LEVEL only via
    logging.setup.configure_logging(), which resolves from environment lazily.
    """

    def __init__(self, app: ASGIApp, *, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled
        # Ensure base logging is configured exactly once even if middleware instantiated multiple times.
        configure_logging()
        self._logger = logging.getLogger("ai_gateway.access")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Attach a per-request helper for downstream logging (optional use in routes/providers)
        request_logger = RequestLogger(request.scope)
        request.state.logger = request_logger

        start = time.perf_counter()
        try:
            response = await call_next(request)
            status_code: int = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            # Attach headers for redaction (Authorization etc.) and for test visibility
            headers = dict(request.headers)
            # Ensure request_id is included for the formatter to emit it
            from ai_gateway.middleware.correlation import get_request_id

            request_id = get_request_id()
            self._logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code if "status_code" in locals() else 500,
                    "duration_ms": round(duration_ms, 2),
                    "headers": headers,
                    "request_id": request_id,
                },
            )
