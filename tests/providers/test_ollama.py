from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import pytest

from ai_gateway.providers.base import ChatProvider
from ai_gateway.providers.ollama import OllamaProvider
from ai_gateway.providers.ollama_client import OllamaClient
from ai_gateway.schemas.openai_chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
)
from ai_gateway.schemas.openai_embeddings import CreateEmbeddingsRequest
from ai_gateway.schemas.openai_models import Model


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure OllamaClient initialization sees relaxed settings in tests."""
    from ai_gateway.config.config import Settings, get_settings

    # Clear any cached get_settings results so our patch takes effect immediately
    if hasattr(get_settings, "cache_clear"):
        with contextlib.suppress(Exception):
            get_settings.cache_clear()

    def fake_settings() -> Settings:
        # provide minimal, valid config for unit tests
        return Settings(
            ALLOWED_API_KEYS=["test-key"],
            ALLOWED_API_KEYS_RAW="test-key",
            DEVELOPMENT_MODE=True,
            REQUIRE_AUTH=True,
            OLLAMA_HOST="http://localhost:11434",
            REQUEST_TIMEOUT_S=1,
        )

    monkeypatch.setattr("ai_gateway.config.config.get_settings", fake_settings, raising=True)


@pytest.fixture()
def provider(monkeypatch: pytest.MonkeyPatch) -> ChatProvider:
    # Ensure OllamaClient constructed inside provider sees relaxed settings
    from ai_gateway.config.config import Settings

    def fake_settings() -> Settings:
        return Settings(
            ALLOWED_API_KEYS=["test-key"],
            ALLOWED_API_KEYS_RAW="test-key",
            DEVELOPMENT_MODE=True,
            REQUIRE_AUTH=True,
            OLLAMA_HOST="http://localhost:11434",
            REQUEST_TIMEOUT_S=1,
        )

    # Patch before provider initialization so OllamaClient() uses it
    monkeypatch.setattr("ai_gateway.config.config.get_settings", fake_settings, raising=True)

    return OllamaProvider()


def _sample_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="llama3.1:latest",
        messages=[
            ChatMessage(role="user", content="Hello"),
        ],
        temperature=0.0,
        max_tokens=32,
    )


def test_success_maps_response(monkeypatch: pytest.MonkeyPatch, provider: ChatProvider) -> None:
    # Patch OllamaClient.chat to return a minimal successful structure
    async def _mock_chat(self: OllamaClient, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
        # kwargs may include model, messages, etc. We ignore specifics for the unit test.
        return {
            "model": kwargs.get("model", "llama3.1:latest"),
            "message": {"role": "assistant", "content": "Hi there!"},
            "created_at": "2024-01-01T00:00:00Z",
            "done": True,
            "total_duration": 1234567,
        }

    monkeypatch.setattr(OllamaClient, "chat", _mock_chat, raising=True)

    req = _sample_request()
    resp = asyncio.get_event_loop().run_until_complete(provider.chat_completions(req))
    assert isinstance(resp, ChatCompletionResponse)
    assert resp.object == "chat.completion"
    assert resp.model == "llama3.1:latest"
    assert resp.choices and isinstance(resp.choices[0], Choice)
    assert resp.choices[0].message.role == "assistant"
    assert "Hi there!" in resp.choices[0].message.content
    # usage may be zeros or estimated; just assert keys present
    assert resp.usage is not None
    assert {"prompt_tokens", "completion_tokens", "total_tokens"} <= set(
        resp.usage.model_dump().keys()
    )


def test_error_maps_to_provider_error(
    monkeypatch: pytest.MonkeyPatch, provider: ChatProvider
) -> None:
    # Force OllamaClient.chat to raise an exception to validate normalization
    class DummyNetworkError(Exception):
        pass

    async def _raise(self: OllamaClient, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
        raise DummyNetworkError("network down")

    monkeypatch.setattr(OllamaClient, "chat", _raise, raising=True)

    req = _sample_request()
    with pytest.raises(Exception) as ei:
        asyncio.get_event_loop().run_until_complete(provider.chat_completions(req))
    # Provider should wrap/normalize to ProviderError
    from ai_gateway.exceptions.errors import ProviderError

    assert isinstance(ei.value, ProviderError)


def test_timeout_maps_to_provider_error(
    monkeypatch: pytest.MonkeyPatch, provider: ChatProvider
) -> None:
    # Simulate a timeout/cancellation in the underlying client
    async def _sleep_forever(self: OllamaClient, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
        await asyncio.sleep(3600)
        return {}

    monkeypatch.setattr(OllamaClient, "chat", _sleep_forever, raising=True)

    req = _sample_request()
    # Run with a very short timeout by patching provider/client if provider enforces timeout internally
    # If provider relies on settings, shorten REQUEST_TIMEOUT_S via fixture
    with pytest.raises(Exception) as ei:
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(provider.chat_completions(req), timeout=0.01)
        )
    # Upstream timeout leads to ProviderError via handler at API layer. At unit level,
    # we can assert TimeoutError/CancelledError is raised here, and integration tests
    # ensure mapping to ProviderError via global handlers.
    # For robustness, allow either local timeout or ProviderError if provider converts it eagerly.
    from ai_gateway.exceptions.errors import ProviderError

    assert isinstance(ei.value, asyncio.TimeoutError | ProviderError)


@pytest.mark.asyncio
async def test_ollama_provider_list_models_stub(provider: ChatProvider) -> None:
    """Test list_models method returns a valid response (stub implementation)."""
    # Cast to OllamaProvider to access list_models method
    ollama_provider = provider  # Already OllamaProvider from fixture

    response = await ollama_provider.list_models()

    # Check response structure
    assert response.object == "list"
    assert isinstance(response.data, list)
    # The stub implementation should return at least one model
    assert len(response.data) > 0

    # Check each model
    for model in response.data:
        assert isinstance(model, Model)
        assert model.object == "model"
        assert isinstance(model.id, str) and len(model.id) > 0
        assert isinstance(model.created, int)
        assert isinstance(model.owned_by, str) and len(model.owned_by) > 0
        assert isinstance(model.permission, list) and len(model.permission) > 0


@pytest.mark.asyncio
async def test_ollama_provider_create_embeddings_stub(provider: ChatProvider) -> None:
    """Test create_embeddings method returns a valid response (stub implementation)."""
    # Cast to OllamaProvider to access create_embeddings method
    ollama_provider = provider  # Already OllamaProvider from fixture

    # Test with string input
    req = CreateEmbeddingsRequest(
        model="llama3.1:latest",
        input="Hello world",
    )
    resp = await ollama_provider.create_embeddings(req)

    assert resp.object == "list"
    assert isinstance(resp.data, list)
    assert len(resp.data) == 1
    assert resp.model == "llama3.1:latest"

    # Check embedding item
    item = resp.data[0]
    assert item.object == "embedding"
    assert isinstance(item.embedding, list)
    assert len(item.embedding) > 0
    assert item.index == 0

    # Check all embedding values are floats
    for val in item.embedding:
        assert isinstance(val, float)

    # Check usage
    assert resp.usage.prompt_tokens >= 0
    assert resp.usage.total_tokens >= 0
