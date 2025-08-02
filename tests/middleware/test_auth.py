from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient

from ai_gateway.exceptions.handlers import register_exception_handlers
from ai_gateway.middleware.auth import _parse_allowed_keys, _parse_bearer_token, auth_bearer


def build_app_with_auth_endpoint() -> FastAPI:
    app = FastAPI()
    # Register global handlers so AuthError becomes 401 with WWW-Authenticate
    register_exception_handlers(app)

    @app.get("/protected")
    async def protected(token: str = Depends(auth_bearer)) -> dict[str, str]:
        # Echo that auth passed without returning the token (avoid secret leakage)
        return {"status": "ok"}

    return app


class DummySettings:
    def __init__(self, allowed: str | list[str] | None) -> None:
        self.ALLOWED_API_KEYS = allowed


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    # Default: single key "validkey"
    from ai_gateway.config import config as config_module

    def _get_settings() -> DummySettings:
        return DummySettings("validkey")

    # Patch get_settings used by dependency
    monkeypatch.setattr(config_module, "get_settings", _get_settings)
    # Ensure environment does not force validation errors in Settings and allows auth checks
    monkeypatch.setenv("ALLOWED_API_KEYS", "validkey")
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    # Enable DEVELOPMENT_MODE to avoid strict Settings validation paths during tests
    monkeypatch.setenv("DEVELOPMENT_MODE", "true")
    yield


def test_missing_header_returns_401() -> None:
    app = build_app_with_auth_endpoint()
    client = TestClient(app)

    resp = client.get("/protected")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.headers.get("WWW-Authenticate") == "Bearer"
    data = resp.json()
    assert isinstance(data, dict) and "error" in data
    assert data["error"]["type"] == "auth_error"
    assert "Missing Authorization header" in data["error"]["message"]


def test_malformed_header_returns_401() -> None:
    app = build_app_with_auth_endpoint()
    client = TestClient(app)

    # No space after scheme, or missing token
    resp = client.get("/protected", headers={"Authorization": "Bearer"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.headers.get("WWW-Authenticate") == "Bearer"
    data = resp.json()
    assert data["error"]["type"] == "auth_error"
    assert "Malformed Authorization header" in data["error"]["message"]


def test_wrong_scheme_returns_401() -> None:
    app = build_app_with_auth_endpoint()
    client = TestClient(app)

    resp = client.get("/protected", headers={"Authorization": "Basic abc"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.headers.get("WWW-Authenticate") == "Bearer"
    data = resp.json()
    assert data["error"]["type"] == "auth_error"
    assert "Invalid auth scheme" in data["error"]["message"]


def test_empty_token_returns_401() -> None:
    app = build_app_with_auth_endpoint()
    client = TestClient(app)

    resp = client.get("/protected", headers={"Authorization": "Bearer   "})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.headers.get("WWW-Authenticate") == "Bearer"
    data = resp.json()
    assert data["error"]["type"] == "auth_error"
    assert "Empty bearer token" in data["error"]["message"]


def test_invalid_token_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    app = build_app_with_auth_endpoint()
    client = TestClient(app)

    # Patch allowed keys to something else
    from ai_gateway.config import config as config_module

    def _get_settings() -> DummySettings:
        return DummySettings("otherkey")

    monkeypatch.setattr(config_module, "get_settings", _get_settings)
    # Also override env to ensure config validation passes but allowed keys are different
    monkeypatch.setenv("ALLOWED_API_KEYS", "otherkey")

    resp = client.get("/protected", headers={"Authorization": "Bearer validkey"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.headers.get("WWW-Authenticate") == "Bearer"
    data = resp.json()
    assert data["error"]["type"] == "auth_error"
    assert "Invalid credentials" in data["error"]["message"]


def test_valid_single_token_succeeds() -> None:
    app = build_app_with_auth_endpoint()
    client = TestClient(app)

    # Ensure environment and settings align on valid key
    from ai_gateway.config import config as config_module

    def _get_settings() -> DummySettings:
        return DummySettings("validkey")

    # Force env to same valid key so runtime Settings sees it
    import os

    os.environ["ALLOWED_API_KEYS"] = "validkey"
    os.environ["DEVELOPMENT_MODE"] = "true"
    config_module.get_settings = _get_settings  # type: ignore[assignment]

    resp = client.get("/protected", headers={"Authorization": "Bearer validkey"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"status": "ok"}


def test_csv_with_whitespace_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    app = build_app_with_auth_endpoint()
    client = TestClient(app)

    # Allow keys with whitespace around commas
    from ai_gateway.config import config as config_module

    def _get_settings():
        return DummySettings(" key1 , validkey , key3 ")

    monkeypatch.setattr(config_module, "get_settings", _get_settings)
    # Also ensure env contains a superset including validkey
    monkeypatch.setenv("ALLOWED_API_KEYS", "key1, validkey , key3")
    monkeypatch.setenv("DEVELOPMENT_MODE", "true")

    resp = client.get("/protected", headers={"Authorization": "Bearer validkey"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"status": "ok"}


def test_parse_allowed_keys_helper() -> None:
    assert _parse_allowed_keys(None) == set()
    assert _parse_allowed_keys("") == set()
    assert _parse_allowed_keys("a,b , c ,,") == {"a", "b", "c"}


def test_parse_bearer_token_helper_errors() -> None:
    with pytest.raises(Exception):
        _parse_bearer_token(None)
    with pytest.raises(Exception):
        _parse_bearer_token("Bearer")
    with pytest.raises(Exception):
        _parse_bearer_token("Basic abc")
    with pytest.raises(Exception):
        _parse_bearer_token("Bearer   ")


def test_parse_bearer_token_helper_ok() -> None:
    assert _parse_bearer_token("Bearer tok") == "tok"
