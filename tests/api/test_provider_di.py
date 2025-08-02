from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ai_gateway.api.app import get_app
from ai_gateway.config.constants import CEREBRAS_BASE, OLLAMA_BASE, V1_BASE
from ai_gateway.exceptions.errors import ProviderError
from ai_gateway.schemas.openai_chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    Usage,
)

# Notes:
# The routes now use dependency injection with provider factory functions. We test DI override
# ability using FastAPI's dependency_overrides mechanism to replace the provider factories
# with our fake providers (FakeSuccessProvider and FakeErrorProvider).
#
# This approach is more idiomatic FastAPI and allows us to test the dependency injection
# system directly while maintaining the app's composition.


class ChatProvider(Protocol):
    async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse:  # noqa: D401
        ...


class FakeSuccessProvider:
    """Deterministic fake provider returning OpenAI-compatible response."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse:
        # Produce a minimal, deterministic response with sentinel model to assert routing.
        return ChatCompletionResponse(
            id="chatcmpl-fake",
            object="chat.completion",
            created=1,
            model=self.model_name,
            choices=[
                Choice(
                    index=0,
                    message=ChatMessage(role="assistant", content="fake-ok"),
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )


class FakeErrorProvider:
    """Fake provider that raises ProviderError for error normalization tests."""

    def __init__(self, message: str = "provider failed") -> None:
        self._message = message

    async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse:
        raise ProviderError(self._message)


@pytest.fixture()
def app() -> FastAPI:
    # Enable dev-mode but require auth to test dependency injection
    import os

    os.environ["DEVELOPMENT_MODE"] = "true"
    os.environ["REQUIRE_AUTH"] = "true"
    return get_app()


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    # httpx>=0.24 requires ASGITransport to pass an ASGI app directly
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_v1_provider_override_success(client: AsyncClient, app: FastAPI) -> None:
    # Override the provider factory to return our fake success provider
    from ai_gateway.api.routes import get_custom_provider

    def fake_provider_factory() -> FakeSuccessProvider:
        return FakeSuccessProvider("fake-v1")

    app.dependency_overrides[get_custom_provider] = fake_provider_factory

    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(
        f"{V1_BASE}/chat/completions",
        headers={"Authorization": "Bearer test-key"},
        json=payload.model_dump(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "fake-v1"
    assert data["choices"][0]["message"]["content"] == "fake-ok"
    assert data["object"] == "chat.completion"
    assert data["id"].startswith("chatcmpl-"[:10]) or data["id"] == "chatcmpl-fake"


@pytest.mark.asyncio
async def test_cerebras_provider_override_success(client: AsyncClient, app: FastAPI) -> None:
    # Override the provider factory to return our fake success provider
    from ai_gateway.api.routes import get_cerebras_provider

    def fake_provider_factory() -> FakeSuccessProvider:
        return FakeSuccessProvider("fake-cerebras")

    app.dependency_overrides[get_cerebras_provider] = fake_provider_factory

    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(
        f"{CEREBRAS_BASE}/chat/completions",
        headers={"Authorization": "Bearer test-key"},
        json=payload.model_dump(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "fake-cerebras"
    assert data["choices"][0]["message"]["content"] == "fake-ok"
    assert data["object"] == "chat.completion"


@pytest.mark.asyncio
async def test_ollama_provider_override_success(client: AsyncClient, app: FastAPI) -> None:
    # Override the provider factory to return our fake success provider
    from ai_gateway.api.routes import get_ollama_provider

    def fake_provider_factory() -> FakeSuccessProvider:
        return FakeSuccessProvider("fake-ollama")

    app.dependency_overrides[get_ollama_provider] = fake_provider_factory

    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(
        f"{OLLAMA_BASE}/chat/completions",
        headers={"Authorization": "Bearer test-key"},
        json=payload.model_dump(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "fake-ollama"
    assert data["choices"][0]["message"]["content"] == "fake-ok"
    assert data["object"] == "chat.completion"


@pytest.mark.asyncio
async def test_cerebras_provider_error_normalization(client: AsyncClient, app: FastAPI) -> None:
    # Override the provider factory to return our fake error provider
    from ai_gateway.api.routes import get_cerebras_provider

    def fake_provider_factory() -> FakeErrorProvider:
        return FakeErrorProvider("boom")

    app.dependency_overrides[get_cerebras_provider] = fake_provider_factory

    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(
        f"{CEREBRAS_BASE}/chat/completions",
        headers={"Authorization": "Bearer test-key"},
        json=payload.model_dump(),
    )
    # Expect the global exception handler to convert ProviderError into a 502 with standardized payload
    assert resp.status_code == 502
    data = resp.json()
    assert "error" in data
    assert data["error"]["type"] in ("ProviderError", "provider_error")
    assert "boom" in data["error"]["message"]


@pytest.mark.asyncio
async def test_ollama_provider_error_normalization(client: AsyncClient, app: FastAPI) -> None:
    # Override the provider factory to return our fake error provider
    from ai_gateway.api.routes import get_ollama_provider

    def fake_provider_factory() -> FakeErrorProvider:
        return FakeErrorProvider("downstream failed")

    app.dependency_overrides[get_ollama_provider] = fake_provider_factory

    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(
        f"{OLLAMA_BASE}/chat/completions",
        headers={"Authorization": "Bearer test-key"},
        json=payload.model_dump(),
    )
    assert resp.status_code == 502
    data = resp.json()
    assert "error" in data
    assert data["error"]["type"] in ("ProviderError", "provider_error")
    assert "downstream failed" in data["error"]["message"]
