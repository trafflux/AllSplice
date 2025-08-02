from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_gateway.api.app import get_app


def _build_minimal_app() -> FastAPI:
    # Use the standard app factory to ensure middleware ordering and settings usage
    return get_app()


@pytest.fixture()
def client_disabled_cors(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Ensure CORS is disabled by default
    from ai_gateway.config import config as config_module

    class DummySettings:
        ENABLE_SECURITY_HEADERS = True
        ENABLE_CORS = False

    def _get_settings() -> DummySettings:
        return DummySettings()

    # patch get_settings used by the app factory
    # clear cache if present then set
    cache_clear = getattr(config_module.get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    monkeypatch.setattr(config_module, "get_settings", _get_settings)
    return TestClient(_build_minimal_app())


@pytest.fixture()
def client_enabled_cors(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Build an app instance and attach CORS middleware directly to avoid relying on settings.
    from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

    app = _build_minimal_app()
    app.add_middleware(
        StarletteCORSMiddleware,
        allow_origins=["https://example.com"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=False,
    )
    return TestClient(app)


def test_cors_disabled_no_headers(client_disabled_cors: TestClient) -> None:
    resp = client_disabled_cors.get("/healthz", headers={"Origin": "https://example.com"})
    # When disabled, CORS headers should not be present
    assert "access-control-allow-origin" not in {k.lower(): v for k, v in resp.headers.items()}


def test_cors_enabled_allows_matching_origin(client_enabled_cors: TestClient) -> None:
    resp = client_enabled_cors.get("/healthz", headers={"Origin": "https://example.com"})
    assert resp.status_code == 200
    # Starlette sets the exact origin value for allowed origin matches
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://example.com"


def test_cors_enabled_blocks_other_origin(client_enabled_cors: TestClient) -> None:
    resp = client_enabled_cors.get("/healthz", headers={"Origin": "https://other.com"})
    # For non-allowed origin, header should be absent
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") is None


def test_cors_preflight_options_allowed(client_enabled_cors: TestClient) -> None:
    resp = client_enabled_cors.options(
        "/healthz",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    # Starlette returns 200 for preflight by default
    assert resp.status_code in (200, 204)
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://example.com"
    allow_methods = resp.headers.get("Access-Control-Allow-Methods") or ""
    assert "GET" in allow_methods
