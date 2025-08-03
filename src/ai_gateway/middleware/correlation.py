from __future__ import annotations

import time
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Public contextvar to be used by logging and providers
_request_id_ctx: ContextVar[str | None] = ContextVar("_request_id_ctx", default=None)


def get_request_id() -> str | None:
    """Return the current request ID from context, if any."""
    return _request_id_ctx.get()


def _generate_request_id() -> str:
    """
    Generate a compact, sortable ID. ULID is ideal, but to avoid adding deps here,
    use a time-based monotonic-safe fallback: base36 timestamp + random suffix.
    """
    import os

    ts = int(time.time() * 1000)
    ts_b36 = _to_base36(ts)
    rand = os.urandom(4).hex()
    return f"{ts_b36}-{rand}"


def _to_base36(n: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    digits: list[str] = []
    while n:
        n, rem = divmod(n, 36)
        digits.append(chars[rem])
    return sign + "".join(reversed(digits))


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures each request has a stable request ID, sourced from
    X-Request-ID header if present or generated otherwise. The ID is stored in a
    contextvar and added to the response headers.

    Additionally, expose a lower-case 'x-request-id' header alias to align with OpenAI SDK examples
    that access response._request_id from the 'x-request-id' header. Some intermediaries may
    canonicalize headers; we explicitly set both casings to maximize compatibility.
    """

    header_name = "X-Request-ID"
    header_alias = "x-request-id"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(self.header_name) or request.headers.get(self.header_alias)
        req_id = incoming.strip() if incoming else _generate_request_id()

        token = _request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
        finally:
            # Ensure header present on response BEFORE resetting context so filters can still read it
            # (especially important for logging that formats after handler returns)
            try:
                response.headers[self.header_name] = req_id
                response.headers[self.header_alias] = req_id
            finally:
                # Always reset context to avoid leaking across requests in async server
                _request_id_ctx.reset(token)

        return response


# Dependency helper (optional)
def request_id_dependency() -> str | None:
    """FastAPI Depends-compatible getter for the current request ID."""
    return get_request_id()
