from __future__ import annotations

import pytest

from ai_gateway.exceptions.errors import ProviderError
from ai_gateway.providers.cerebras import CerebrasProvider
from ai_gateway.providers.cerebras_client import CerebrasClient
from ai_gateway.schemas.openai_chat import ChatCompletionRequest, ChatMessage
from ai_gateway.schemas.openai_embeddings import CreateEmbeddingsRequest
from ai_gateway.schemas.openai_models import Model


class _MockClientOK(CerebrasClient):
    def __init__(self) -> None:
        # Avoid calling real Settings in tests; force mock params
        self.api_key: str | None = None
        self.base_url: str | None = None
        self.timeout_s: float = 1.0
        self.mock_mode: bool = True

    async def chat(
        self, model: str, messages: list[dict[str, str]], **kwargs: object
    ) -> dict[str, object]:
        last_user = ""
        for m in reversed(messages):
            role = m.get("role")
            if role == "user":
                last_user = str(m.get("content", ""))
                break
        return {
            "id": "cb-mock-xyz",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": f"echo:{last_user}"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        }


class _MockClientError(CerebrasClient):
    def __init__(self) -> None:
        self.api_key: str | None = None
        self.base_url: str | None = None
        self.timeout_s: float = 1.0
        self.mock_mode: bool = True

    async def chat(
        self, model: str, messages: list[dict[str, str]], **kwargs: object
    ) -> dict[str, object]:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_cerebras_provider_ok_mapping() -> None:
    provider = CerebrasProvider(client=_MockClientOK())
    req = ChatCompletionRequest(
        model="cerebras/small",
        messages=[
            ChatMessage(role="system", content="You are a test bot."),
            ChatMessage(role="user", content="Hello"),
        ],
        temperature=0.1,
        max_tokens=16,
    )
    resp = await provider.chat_completions(req)

    assert resp.object == "chat.completion"
    assert resp.model == "cerebras/small"
    assert isinstance(resp.created, int)
    assert resp.id.startswith("chatcmpl-")

    assert len(resp.choices) == 1
    choice = resp.choices[0]
    assert choice.index == 0
    assert choice.message.role == "assistant"
    assert choice.message.content == "echo:Hello"
    assert choice.finish_reason == "stop"

    assert resp.usage.prompt_tokens == 2
    assert resp.usage.completion_tokens == 3
    assert resp.usage.total_tokens == 5


@pytest.mark.asyncio
async def test_cerebras_provider_error_normalization() -> None:
    provider = CerebrasProvider(client=_MockClientError())
    req = ChatCompletionRequest(
        model="cerebras/small",
        messages=[ChatMessage(role="user", content="Hello")],
    )
    with pytest.raises(ProviderError):
        await provider.chat_completions(req)


@pytest.mark.asyncio
async def test_cerebras_provider_list_models_stub() -> None:
    """Test list_models method returns a valid response (stub implementation)."""
    provider = CerebrasProvider()
    response = await provider.list_models()

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
async def test_cerebras_provider_create_embeddings_stub() -> None:
    """Test create_embeddings method returns a valid response (stub implementation)."""
    provider = CerebrasProvider()

    # Test with string input
    req = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input="Hello world",
    )
    resp = await provider.create_embeddings(req)

    assert resp.object == "list"
    assert isinstance(resp.data, list)
    assert len(resp.data) == 1
    assert resp.model == "text-embedding-ada-002"

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
