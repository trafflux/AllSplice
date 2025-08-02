import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ai_gateway.api.app import get_app
from ai_gateway.config.config import Settings


@pytest.mark.asyncio
async def test_v1_chat_completions_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure there are allowed keys but we don't send any header
    def fake_settings() -> Settings:
        # Enable DEVELOPMENT_MODE to relax config validation in tests
        return Settings(ALLOWED_API_KEYS=["k1"], DEVELOPMENT_MODE=True)

    monkeypatch.setattr("ai_gateway.config.config.get_settings", fake_settings)

    app: FastAPI = get_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/v1/chat/completions", json={"model": "gpt-3.5-turbo", "messages": []}
        )
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_v1_chat_completions_authorized(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_settings() -> Settings:
        # Set both list and raw CSV so config normalization and env access both succeed
        return Settings(
            ALLOWED_API_KEYS=["test-key"],
            ALLOWED_API_KEYS_RAW="test-key",
            DEVELOPMENT_MODE=True,
            REQUIRE_AUTH=True,
        )

    monkeypatch.setattr("ai_gateway.config.config.get_settings", fake_settings)

    app: FastAPI = get_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        req = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "hi"}],
        }
        r = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer test-key"},
            json=req,
        )
        assert r.status_code == 200
        body = r.json()
    # Basic schema assertions
    assert body["id"].startswith("chatcmpl-")
    assert body["object"] == "chat.completion"
    assert isinstance(body["created"], int)
    assert body["model"] == "gpt-3.5-turbo"
    assert isinstance(body["choices"], list) and len(body["choices"]) == 1
    choice = body["choices"][0]
    assert choice["index"] == 0
    assert choice["finish_reason"] == "stop"
    assert choice["message"]["role"] == "assistant"
    assert "usage" in body
    assert {"prompt_tokens", "completion_tokens", "total_tokens"} <= set(body["usage"].keys())


@pytest.mark.asyncio
async def test_cerebras_and_ollama_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_settings() -> Settings:
        return Settings(
            ALLOWED_API_KEYS=["k1"],
            ALLOWED_API_KEYS_RAW="k1",
            DEVELOPMENT_MODE=True,
            REQUIRE_AUTH=True,
        )

    monkeypatch.setattr("ai_gateway.config.config.get_settings", fake_settings)

    app: FastAPI = get_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = {"Authorization": "Bearer k1"}
        req = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "hi"}],
        }

        # Cerebras is functional; assert standard OpenAI-like schema on success
        r1 = await client.post("/cerebras/v1/chat/completions", headers=h, json=req)
        assert r1.status_code in (200, 502)
        if r1.status_code == 200:
            body1 = r1.json()
            assert body1["id"].startswith("chatcmpl-")
            assert body1["object"] == "chat.completion"
            assert isinstance(body1["created"], int)
            assert isinstance(body1["choices"], list) and len(body1["choices"]) == 1
            assert "usage" in body1
        else:
            # Standardized error payload via global handlers
            body1 = r1.json()
            assert "error" in body1 and "type" in body1["error"] and "message" in body1["error"]

        # Ollama path is wired as well; assert 200 or standardized error
        r2 = await client.post("/ollama/v1/chat/completions", headers=h, json=req)
        assert r2.status_code in (200, 502)
        if r2.status_code == 200:
            body2 = r2.json()
            assert body2["id"].startswith("chatcmpl-")
            assert body2["object"] == "chat.completion"
            assert isinstance(body2["created"], int)
            assert isinstance(body2["choices"], list) and len(body2["choices"]) == 1
            assert "usage" in body2
        else:
            body2 = r2.json()
            assert "error" in body2 and "type" in body2["error"] and "message" in body2["error"]
