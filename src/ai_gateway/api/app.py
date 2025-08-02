from __future__ import annotations

from fastapi import FastAPI

from ai_gateway.api.routes import (
    cerebras_router,
    health_router,
    ollama_router,
    v1_router as api_router,
)
from ai_gateway.exceptions.handlers import register_exception_handlers
from ai_gateway.middleware.correlation import CorrelationIdMiddleware

# Import locally inside get_app() to avoid any potential circular import analysis issues in editors
# from ai_gateway.middleware.logging_middleware import StructuredLoggingMiddleware
from ai_gateway.middleware.security_headers import SecurityHeadersMiddleware


def get_app() -> FastAPI:
    """
    Application factory returning a configured FastAPI instance.

    Registers:
      - Global exception handlers (standardized error payloads).
      - Correlation ID middleware (X-Request-ID propagation).
      - Security headers middleware (conditional via settings).
      - Routers for /healthz, /v1, /cerebras/v1, /ollama/v1.
    """
    app = FastAPI()

    # Global exception handlers
    register_exception_handlers(app)

    # Middleware — order matters (Starlette executes in reverse install order):
    # To ensure Correlation executes BEFORE SecurityHeaders at runtime, Correlation must be INSTALLED AFTER it.
    # Therefore, install Correlation first in the user_middleware list (lower index), then SecurityHeaders.
    # This yields SecurityHeaders later in the list, so Correlation runs first.
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, enabled=True)
    # Install structured logging middleware last so it runs first at runtime, capturing full duration.
    # Local import prevents editor false-positive on circular imports.
    from ai_gateway.middleware.logging_middleware import StructuredLoggingMiddleware

    app.add_middleware(StructuredLoggingMiddleware, enabled=True)

    # Do NOT access settings at app creation time. CORS is disabled by default and tests that
    # require CORS will enable it by constructing a custom app or monkeypatching settings in their own client.
    # This avoids any eager construction of settings in get_app().

    # Routers (keep compatibility with tests expecting /v1, /cerebras/v1, /ollama/v1)
    app.include_router(health_router)
    app.include_router(api_router)
    app.include_router(cerebras_router)
    app.include_router(ollama_router)

    return app
