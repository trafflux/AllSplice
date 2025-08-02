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
# The current routes instantiate providers directly inside route handlers and do not expose
# dependency callables for providers. We can still validate DI override ability by monkeypatching
# the provider classes that the routes import (ai_gateway.providers.custom.CustomProcessingProvider,
# ai_gateway.providers.cerebras.CerebrasProvider, ai_gateway.providers.ollama.OllamaProvider).
#
# This preserves the app's composition while allowing us to inject fakes in tests, which is
# effectively testing the "DI seam" via import-time binding used by the routes module.


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
    # Enable dev-mode bypass to avoid needing Authorization headers.
    # tests/conftest.py already sets defaults; enforce here for clarity.
    import os

    os.environ["DEVELOPMENT_MODE"] = "true"
    os.environ["REQUIRE_AUTH"] = "false"
    return get_app()


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    # httpx>=0.24 requires ASGITransport to pass an ASGI app directly
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_v1_provider_override_success(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    # Patch the provider class used by the /v1 route to our fake success provider

    # Patch at the symbol actually used by the route module so our fake is constructed
    import ai_gateway.api.routes as routes_mod

    monkeypatch.setattr(
        routes_mod, "CustomProcessingProvider", lambda: FakeSuccessProvider("fake-v1")
    )
    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(f"{V1_BASE}/chat/completions", json=payload.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "fake-v1"
    assert data["choices"][0]["message"]["content"] == "fake-ok"
    assert data["object"] == "chat.completion"
    assert data["id"].startswith("chatcmpl-"[:10]) or data["id"] == "chatcmpl-fake"


@pytest.mark.asyncio
async def test_cerebras_provider_override_success(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    import ai_gateway.api.routes as routes_mod

    monkeypatch.setattr(
        routes_mod, "CerebrasProvider", lambda: FakeSuccessProvider("fake-cerebras")
    )
    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(f"{CEREBRAS_BASE}/chat/completions", json=payload.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "fake-cerebras"
    assert data["choices"][0]["message"]["content"] == "fake-ok"
    assert data["object"] == "chat.completion"


@pytest.mark.asyncio
async def test_ollama_provider_override_success(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    import ai_gateway.api.routes as routes_mod

    monkeypatch.setattr(routes_mod, "OllamaProvider", lambda: FakeSuccessProvider("fake-ollama"))
    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(f"{OLLAMA_BASE}/chat/completions", json=payload.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "fake-ollama"
    assert data["choices"][0]["message"]["content"] == "fake-ok"
    assert data["object"] == "chat.completion"


@pytest.mark.asyncio
async def test_cerebras_provider_error_normalization(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    import ai_gateway.api.routes as routes_mod

    monkeypatch.setattr(routes_mod, "CerebrasProvider", lambda: FakeErrorProvider("boom"))
    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(f"{CEREBRAS_BASE}/chat/completions", json=payload.model_dump())
    # Expect the global exception handler to convert ProviderError into a 502 with standardized payload
    assert resp.status_code == 502
    data = resp.json()
    assert "error" in data
    assert data["error"]["type"] in ("ProviderError", "provider_error")
    assert "boom" in data["error"]["message"]


@pytest.mark.asyncio
async def test_ollama_provider_error_normalization(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    import ai_gateway.api.routes as routes_mod

    monkeypatch.setattr(
        routes_mod, "OllamaProvider", lambda: FakeErrorProvider("downstream failed")
    )
    payload = ChatCompletionRequest(
        model="ignored", messages=[ChatMessage(role="user", content="hi")]
    )

    resp = await client.post(f"{OLLAMA_BASE}/chat/completions", json=payload.model_dump())
    assert resp.status_code == 502
    data = resp.json()
    assert "error" in data
    assert data["error"]["type"] in ("ProviderError", "provider_error")
    assert "downstream failed" in data["error"]["message"]
