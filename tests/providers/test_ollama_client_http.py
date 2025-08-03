from __future__ import annotations

from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from ai_gateway.exceptions.errors import ProviderError
from ai_gateway.providers.ollama import OllamaProvider
from ai_gateway.providers.ollama_client import OllamaClient
from ai_gateway.schemas.openai_chat import ChatCompletionRequest, ChatMessage
from ai_gateway.schemas.openai_embeddings import CreateEmbeddingsRequest


@pytest.mark.asyncio
async def test_client_chat_success_and_provider_mapping(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange HTTP mock for /api/chat
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={
            "model": "llama3",
            "created_at": "2024-01-02T10:20:30Z",
            "message": {"role": "assistant", "content": "hello"},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 3,
            "eval_count": 7,
        },
        status_code=200,
    )

    # Provider with real client (uses httpx_mock transport automatically)
    client = OllamaClient()
    provider = OllamaProvider(client=client)

    req = ChatCompletionRequest(
        model="llama3",
        messages=[ChatMessage(role="user", content="hi")],
        max_tokens=16,
    )
    # Act
    res = await provider.chat_completions(req)

    # Assert OpenAI response shape
    assert res.object == "chat.completion"
    assert res.model == "llama3"
    assert res.choices and res.choices[0].message.content == "hello"
    assert res.usage.prompt_tokens == 3
    assert res.usage.completion_tokens == 7
    assert res.usage.total_tokens == 10


@pytest.mark.asyncio
async def test_client_chat_http_error_normalized_to_provider_error(httpx_mock: HTTPXMock) -> None:
    # 500 from upstream
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"error": "boom"},
        status_code=500,
    )
    provider = OllamaProvider(client=OllamaClient())
    req = ChatCompletionRequest(model="m", messages=[ChatMessage(role="user", content="x")])

    with pytest.raises(ProviderError):
        await provider.chat_completions(req)


@pytest.mark.asyncio
async def test_client_chat_timeout_normalized_to_provider_error(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate timeout by raising from transport
    async def raise_timeout(*_args: Any, **_kwargs: Any) -> Any:
        raise httpx.ReadTimeout("timeout")

    # Instead of monkeypatching internals (which may bypass httpx error handling),
    # register a transport that raises a timeout for the expected endpoint.
    httpx_mock.add_callback(
        lambda request: (_ for _ in ()).throw(
            httpx.ReadTimeout("timeout")
        ),  # raise inside coroutine
        method="POST",
        url="http://localhost:11434/api/chat",
    )

    provider = OllamaProvider(client=OllamaClient())
    req = ChatCompletionRequest(model="m", messages=[ChatMessage(role="user", content="x")])

    with pytest.raises(ProviderError):
        await provider.chat_completions(req)


@pytest.mark.asyncio
async def test_client_tags_success(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="http://localhost:11434/api/tags",
        json={
            "models": [
                {"name": "llama3", "modified_at": "2024-01-01T00:00:00Z"},
                {"name": "tinyllama"},
            ]
        },
        status_code=200,
    )
    provider = OllamaProvider(client=OllamaClient())
    res = await provider.list_models()
    assert any(m.id == "llama3" for m in res.data)
    assert any(m.id == "tinyllama" for m in res.data)
    for m in res.data:
        assert isinstance(m.created, int)


@pytest.mark.asyncio
async def test_client_embeddings_success(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/embeddings",
        json={"data": [{"embedding": [0.1, 0.2, 0.3], "index": 0}], "model": "m", "object": "list"},
        status_code=200,
    )
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/embeddings",
        json={"data": [{"embedding": [0.4, 0.5, 0.6], "index": 0}], "model": "m", "object": "list"},
        status_code=200,
    )
    provider = OllamaProvider(client=OllamaClient())

    req = CreateEmbeddingsRequest(model="m", input=["one", "two"])
    res = await provider.create_embeddings(req)
    assert res.object == "list"
    assert len(res.data) == 2
    assert res.data[0].embedding == [0.1, 0.2, 0.3]
    assert res.data[1].embedding == [0.4, 0.5, 0.6]
    assert res.usage.prompt_tokens == 0
    assert res.usage.total_tokens == 0


@pytest.mark.asyncio
async def test_client_embeddings_json_error_path_to_fallback(httpx_mock: HTTPXMock) -> None:
    # Non-conforming JSON shape; provider should fallback to deterministic vector
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/embeddings",
        json={"unexpected": "shape"},
        status_code=200,
    )
    provider = OllamaProvider(client=OllamaClient())

    req = CreateEmbeddingsRequest(model="m", input="only-one")
    res = await provider.create_embeddings(req)
    assert res.object == "list"
    assert len(res.data) == 1
    assert isinstance(res.data[0].embedding, list)
    assert all(isinstance(x, float | int) for x in res.data[0].embedding)
