import pytest
from fastapi import FastAPI

from ai_gateway.api.app import get_app
from ai_gateway.middleware.correlation import CorrelationIdMiddleware
from ai_gateway.middleware.security_headers import SecurityHeadersMiddleware


@pytest.fixture()
def app() -> FastAPI:
    # Build a fresh app instance for each test; get_app should not eagerly
    # construct Settings and should be safe to call without env.
    return get_app()


def _route_prefixes(app: FastAPI) -> set[str]:
    prefixes: set[str] = set()
    for route in app.router.routes:
        # Only include actual API routes
        path = getattr(route, "path", None)
        if isinstance(path, str):
            # Normalize /healthz (no trailing slash normalization required)
            if path.startswith("/v1"):
                prefixes.add("/v1")
            elif path.startswith("/cerebras/v1"):
                prefixes.add("/cerebras/v1")
            elif path.startswith("/ollama/v1"):
                prefixes.add("/ollama/v1")
            elif path == "/healthz":
                prefixes.add("/healthz")
    return prefixes


def test_routers_registered(app: FastAPI) -> None:
    prefixes = _route_prefixes(app)
    # Expect all namespaces present
    assert "/v1" in prefixes, "Default /v1 routes should be registered"
    assert "/cerebras/v1" in prefixes, "Cerebras /cerebras/v1 routes should be registered"
    assert "/ollama/v1" in prefixes, "Ollama /ollama/v1 routes should be registered"
    assert "/healthz" in prefixes, "Health endpoint /healthz should be registered"


def test_middleware_order(app: FastAPI) -> None:
    # FastAPI/Starlette stores user middleware in app.user_middleware as a list in install order.
    # Each entry is a starlette.types._Middleware instance with attributes (cls, options).
    entries = list(app.user_middleware)

    # Collect indices for the middleware classes of interest
    corr_index: int | None = None
    sec_index: int | None = None
    for i, m in enumerate(entries):
        if getattr(m, "cls", None) is CorrelationIdMiddleware:
            corr_index = i
        if getattr(m, "cls", None) is SecurityHeadersMiddleware:
            sec_index = i

    assert corr_index is not None, "CorrelationIdMiddleware must be installed"
    assert sec_index is not None, "SecurityHeadersMiddleware must be installed"
    # Starlette applies middleware in reverse installation order (last installed executes first).
    # To have Correlation execute before SecurityHeaders, Correlation must be installed AFTER SecurityHeaders.
    # Therefore, corr_index must be greater than sec_index.
    assert corr_index > sec_index, (
        "Middleware install order must be SecurityHeadersMiddleware then CorrelationIdMiddleware"
    )


def test_app_factory_does_not_construct_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure get_app() creation does not require Settings construction.
    We simulate a failing Settings initialization and assert get_app() still succeeds.
    """
    import ai_gateway.config.config as cfg

    # Ensure any cached settings are cleared so our patch takes effect if indirectly invoked.
    cache_clear = getattr(cfg.get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()

    constructed = {"count": 0}

    def _bomb_settings() -> object:
        constructed["count"] += 1
        raise RuntimeError("Settings should not be constructed at app creation")

    # Patch get_settings to a function that would blow up if called during app creation.
    monkeypatch.setattr(cfg, "get_settings", _bomb_settings, raising=True)

    # Creating the app must NOT call get_settings. If it does, the test will fail by raising.
    app = get_app()
    assert isinstance(app, FastAPI)
    # Sanity: ensure our "bomb" was not triggered.
    assert constructed["count"] == 0
