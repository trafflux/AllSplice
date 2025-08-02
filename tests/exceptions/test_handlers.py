from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_gateway.exceptions.errors import (
    AuthError,
    InternalError,
    ProviderError,
    ValidationAppError,
)
from ai_gateway.exceptions.handlers import register_exception_handlers


def build_app_with_handlers() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/auth")
    async def raise_auth() -> dict[str, Any]:
        raise AuthError("Auth failed", {"reason": "bad_token"})

    @app.get("/raise/validation")
    async def raise_validation() -> dict[str, Any]:
        raise ValidationAppError("Invalid input", {"field": "x"})

    @app.get("/raise/provider")
    async def raise_provider() -> dict[str, Any]:
        raise ProviderError("Upstream failed", {"provider": "dummy"})

    @app.get("/raise/internal")
    async def raise_internal() -> dict[str, Any]:
        raise InternalError("Something broke")

    @app.get("/raise/unexpected")
    async def raise_unexpected() -> dict[str, Any]:
        # This should be normalized to InternalError by the generic handler
        # Use Starlette HTTPException to ensure the route hits our global exception handler path.
        from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: WPS433

        raise StarletteHTTPException(status_code=500, detail="boom")

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.fixture()
def client() -> TestClient:
    app = build_app_with_handlers()
    return TestClient(app)


def assert_standard_error_shape(payload: dict[str, Any]) -> None:
    assert isinstance(payload, dict)
    assert "error" in payload
    err = payload["error"]
    assert isinstance(err, dict)
    assert "type" in err and isinstance(err["type"], str)
    assert "message" in err and isinstance(err["message"], str)
    # details is optional
    if "details" in err:
        assert isinstance(err["details"], dict)


def test_auth_error_is_normalized_and_sets_www_authenticate(client: TestClient) -> None:
    resp = client.get("/raise/auth")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"
    payload = resp.json()
    assert_standard_error_shape(payload)
    assert payload["error"]["type"] == "auth_error"
    assert "Auth failed" in payload["error"]["message"]
    assert payload["error"]["details"] == {"reason": "bad_token"}


def test_validation_error_is_normalized(client: TestClient) -> None:
    resp = client.get("/raise/validation")
    assert resp.status_code == 422
    payload = resp.json()
    assert_standard_error_shape(payload)
    assert payload["error"]["type"] == "validation_error"
    assert "Invalid input" in payload["error"]["message"]
    assert payload["error"]["details"] == {"field": "x"}


def test_provider_error_is_normalized(client: TestClient) -> None:
    resp = client.get("/raise/provider")
    assert resp.status_code == 502
    payload = resp.json()
    assert_standard_error_shape(payload)
    assert payload["error"]["type"] == "provider_error"
    assert "Upstream failed" in payload["error"]["message"]
    assert payload["error"]["details"] == {"provider": "dummy"}


def test_internal_error_is_normalized(client: TestClient) -> None:
    resp = client.get("/raise/internal")
    assert resp.status_code == 500
    payload = resp.json()
    assert_standard_error_shape(payload)
    assert payload["error"]["type"] == "internal_error"
    assert "Something broke" in payload["error"]["message"]


def test_unexpected_exception_maps_to_internal_error_without_leaking_details(
    client: TestClient,
) -> None:
    resp = client.get("/raise/unexpected")
    assert resp.status_code == 500
    payload = resp.json()
    assert_standard_error_shape(payload)
    assert payload["error"]["type"] == "internal_error"
    # Message should be the standardized one from handlers, not the original "boom"
    assert payload["error"]["message"] == "An internal error occurred."
    # Ensure no raw exception text leaked
    text = json.dumps(payload)
    assert "boom" not in text


def test_ok_pass_through(client: TestClient) -> None:
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
