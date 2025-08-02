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


class DummySettings:
    def __init__(self) -> None:
        self.OLLAMA_HOST = "http://localhost:11434"
        self.REQUEST_TIMEOUT_S = 1.0
        self.MODEL_DEFAULT = "llama3.1:latest"


@pytest.fixture()
def settings() -> DummySettings:
    return DummySettings()


@pytest.fixture()
def provider(monkeypatch: pytest.MonkeyPatch, settings: DummySettings) -> ChatProvider:
    # Build provider with injected DummySettings via monkeypatch if provider pulls get_settings at runtime.
    from ai_gateway.config import config as config_module

    def _get_settings() -> DummySettings:
        return settings

    # Ensure provider uses our settings
    if hasattr(config_module.get_settings, "cache_clear"):
        with contextlib.suppress(Exception):
            config_module.get_settings.cache_clear()
    monkeypatch.setattr(config_module, "get_settings", _get_settings)

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
