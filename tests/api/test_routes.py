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
        return Settings(ALLOWED_API_KEYS=["k1"], DEVELOPMENT_MODE=True, REQUIRE_AUTH=True)

    monkeypatch.setattr("ai_gateway.config.config.get_settings", fake_settings)

    app: FastAPI = get_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Provide a minimal valid message to satisfy request validation so we exercise auth
        r = await client.post(
            "/v1/chat/completions",
            json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]},
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


@pytest.mark.asyncio
async def test_v1_list_models_authorized(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GET /v1/models endpoint."""

    def fake_settings() -> Settings:
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
        r = await client.get(
            "/v1/models",
            headers={"Authorization": "Bearer test-key"},
        )
        assert r.status_code == 200
        body = r.json()

    # Basic schema assertions
    assert body["object"] == "list"
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0

    # Check each model
    for model in body["data"]:
        assert model["object"] == "model"
        assert isinstance(model["id"], str) and len(model["id"]) > 0
        assert isinstance(model["created"], int)
        assert isinstance(model["owned_by"], str) and len(model["owned_by"]) > 0
        assert isinstance(model["permission"], list) and len(model["permission"]) > 0


@pytest.mark.asyncio
async def test_v1_create_embeddings_authorized(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test POST /v1/embeddings endpoint."""

    def fake_settings() -> Settings:
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
            "model": "text-embedding-ada-002",
            "input": "Hello world",
        }
        r = await client.post(
            "/v1/embeddings",
            headers={"Authorization": "Bearer test-key"},
            json=req,
        )
        assert r.status_code == 200
        body = r.json()

    # Basic schema assertions
    assert body["object"] == "list"
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    assert body["model"] == "text-embedding-ada-002"

    # Check embedding item
    item = body["data"][0]
    assert item["object"] == "embedding"
    assert isinstance(item["embedding"], list)
    assert len(item["embedding"]) > 0
    assert item["index"] == 0

    # Check all embedding values are floats
    for val in item["embedding"]:
        assert isinstance(val, int | float)

    # Check usage
    assert "usage" in body
    assert isinstance(body["usage"]["prompt_tokens"], int)
    assert isinstance(body["usage"]["total_tokens"], int)


@pytest.mark.asyncio
async def test_provider_list_models_and_embeddings_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test list_models and create_embeddings endpoints for all providers."""

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

        # Test Cerebras endpoints
        # list_models
        r1 = await client.get("/cerebras/v1/models", headers=h)
        assert r1.status_code == 200
        body1 = r1.json()
        assert body1["object"] == "list"
        assert isinstance(body1["data"], list)

        # create_embeddings
        r2 = await client.post(
            "/cerebras/v1/embeddings",
            headers=h,
            json={
                "model": "text-embedding-ada-002",
                "input": "Hello world",
            },
        )
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2["object"] == "list"
        assert isinstance(body2["data"], list)
        assert len(body2["data"]) == 1

        # Test Ollama endpoints
        # list_models
        r3 = await client.get("/ollama/v1/models", headers=h)
        assert r3.status_code == 200
        body3 = r3.json()
        assert body3["object"] == "list"
        assert isinstance(body3["data"], list)

        # create_embeddings
        r4 = await client.post(
            "/ollama/v1/embeddings",
            headers=h,
            json={
                "model": "llama3.1:latest",
                "input": "Hello world",
            },
        )
        assert r4.status_code == 200
        body4 = r4.json()
        assert body4["object"] == "list"
        assert isinstance(body4["data"], list)
        assert len(body4["data"]) == 1
