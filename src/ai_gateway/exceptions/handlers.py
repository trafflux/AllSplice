from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import AppError, AuthError, InternalError


def _json_response(
    payload: dict[str, Any], status_code: int, headers: dict[str, str] | None = None
) -> JSONResponse:
    """Return a JSONResponse with standardized payload and optional headers.

    Adds x-request-id header if available from correlation middleware to align with OpenAI SDK.
    """
    from ai_gateway.middleware.correlation import get_request_id

    hdrs = dict(headers or {})
    req_id = get_request_id()
    if req_id and "x-request-id" not in {k.lower(): v for k, v in hdrs.items()}:
        # ensure both casings present for maximum interoperability
        hdrs.setdefault("X-Request-ID", req_id)
        hdrs.setdefault("x-request-id", req_id)
    return JSONResponse(content=payload, status_code=status_code, headers=hdrs)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers that normalize error responses.

    Handled:
      - AppError subclasses → standardized payload and HTTP code.
      - Starlette HTTPException → 5xx normalized to InternalError (no leak); 4xx passed through.
      - Fallback Exception → InternalError(500) standardized payload.
    """

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
        headers: dict[str, str] = {}
        if isinstance(exc, AuthError):
            # Enforce Bearer auth header per RFC6750
            headers["WWW-Authenticate"] = "Bearer"
        return _json_response(exc.to_payload(), status_code=exc.status_code, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def handle_starlette_http_exception(
        request: Request,
        exc: StarletteHTTPException,  # noqa: ARG001
    ) -> JSONResponse:
        # For any server-side HTTP errors, normalize to InternalError without leaking details.
        if exc.status_code >= 500:
            internal = InternalError("An internal error occurred.")
            return _json_response(internal.to_payload(), status_code=internal.status_code)
        # For client errors (4xx), preserve status code but standardize payload shape.
        payload = {
            "error": {
                "type": "http_error",
                "message": exc.detail if isinstance(exc.detail, str) else "Request error",
                "details": {"status_code": exc.status_code},
            }
        }
        return _json_response(payload, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
        # Avoid leaking internals; log elsewhere via middleware/logging if needed.
        internal = InternalError("An internal error occurred.")
        return _json_response(internal.to_payload(), status_code=internal.status_code)
