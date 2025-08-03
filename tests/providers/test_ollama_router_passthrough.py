from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_gateway.providers.ollama import OllamaProvider
from ai_gateway.schemas.openai_chat import ChatCompletionRequest, ChatMessage
from ai_gateway.schemas.openai_embeddings import CreateEmbeddingsRequest


@pytest.mark.asyncio
async def test_chat_completions_pass_through_all_fields_to_client() -> None:
    # Arrange provider with a mocked client
    mock_client = MagicMock()
    mock_client.chat = AsyncMock(
        return_value={
            "message": {"role": "assistant", "content": "ok"},
            "prompt_eval_count": 1,
            "eval_count": 2,
        }
    )
    provider = OllamaProvider(client=mock_client)

    # Build request covering core model fields, and attach additional pass-through attributes dynamically.
    req = ChatCompletionRequest(
        model="ollama-test",
        messages=[
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="Hello"),
        ],
        temperature=0.7,
        top_p=0.9,
        max_tokens=128,
        stop=["END"],
        n=2,
    )
    # Attach router-first extras dynamically to avoid mypy constructor errors
    req.__dict__["seed"] = 42
    req.__dict__["top_k"] = 50
    req.__dict__["presence_penalty"] = 0.1
    req.__dict__["frequency_penalty"] = 0.2
    req.__dict__["logprobs"] = None
    req.__dict__["logit_bias"] = {"123": 1.5}
    req.__dict__["user"] = "router-user"
    req.__dict__["response_format"] = {"type": "json_object"}
    req.__dict__["tools"] = [{"type": "function", "function": {"name": "toolA", "parameters": {}}}]
    req.__dict__["tool_choice"] = "auto"

    # Act
    _ = await provider.chat_completions(req)

    # Assert: was client.chat called with expected shape?
    assert mock_client.chat.await_count == 1
    args, kwargs = mock_client.chat.await_args
    assert kwargs.get("model") == "ollama-test"
    # messages mapping
    assert kwargs.get("messages") == [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
    ]
    # format hint due to response_format json_object
    assert kwargs.get("format_hint") == "json"
    # stream explicitly disabled
    assert kwargs.get("stream") is False

    # options mapping
    options = kwargs.get("options") or {}
    # direct
    assert options.get("num_predict") == 128
    assert options.get("stop") == ["END"]
    assert options.get("temperature") == 0.7
    assert options.get("top_p") == 0.9
    assert options.get("seed") == 42
    # captured extras
    assert options.get("top_k") == 50
    assert options.get("presence_penalty") == 0.1
    assert options.get("frequency_penalty") == 0.2
    assert options.get("logit_bias") == {"123": 1.5}
    assert options.get("n") == 2
    assert options.get("user") == "router-user"
    # tools captured
    assert isinstance(options.get("tools"), list)
    assert options.get("tool_choice") == "auto"
    # structured hint when response_format is json_object
    assert options.get("structured") is True


@pytest.mark.asyncio
async def test_list_models_maps_from_client_get_tags() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.get_tags = AsyncMock(
        return_value={
            "models": [
                {"name": "llama3", "modified_at": "2024-01-01T00:00:00Z"},
                {"name": "tinyllama"},
            ]
        }
    )
    provider = OllamaProvider(client=mock_client)

    # Act
    res = await provider.list_models()

    # Assert
    assert res.data, "expected at least one model"
    ids = [m.id for m in res.data]
    assert "llama3" in ids and "tinyllama" in ids
    # created should be an int epoch
    for m in res.data:
        assert isinstance(m.created, int)
        # permissions populated
        assert m.permission and len(m.permission) == 1
        perm = m.permission[0]
        assert perm.allow_view is True
        assert perm.allow_sampling is True


@pytest.mark.asyncio
async def test_embeddings_multiple_inputs_sequential_calls_and_normalization() -> None:
    # Arrange
    mock_client = MagicMock()
    # Return a vector-shaped payload for first, and a malformed payload for the second
    mock_client.create_embeddings = AsyncMock(
        side_effect=[
            {"data": [{"embedding": [0.1, 0.2, 0.3], "index": 0}], "model": "m", "object": "list"},
            {"unexpected": "shape"},
        ]
    )
    provider = OllamaProvider(client=mock_client)

    # Act
    emb_req = CreateEmbeddingsRequest(model="m", input=["one", "two"])
    res = await provider.create_embeddings(req=emb_req)

    # Assert
    assert res.object == "list"
    assert len(res.data) == 2
    # first item uses upstream vector
    assert res.data[0].embedding == [0.1, 0.2, 0.3]
    # second item falls back to deterministic vector list[float]
    assert isinstance(res.data[1].embedding, list)
    assert all(isinstance(x, float | int) for x in res.data[1].embedding)
    # usage currently zeroed
    assert res.usage.prompt_tokens == 0
    assert res.usage.total_tokens == 0


@pytest.mark.asyncio
async def test_client_headers_propagate_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # This test exercises that _headers includes X-Request-ID when available
    from ai_gateway.providers.ollama_client import OllamaClient

    # Fake correlation id getter
    captured_headers: dict[str, str] = {}

    async def fake_post(url: str, json: dict[str, Any], headers: dict[str, str]) -> Any:
        nonlocal captured_headers
        captured_headers = headers

        # create a tiny dummy response-like object
        class R:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, Any]:
                return {"message": {"role": "assistant", "content": "ok"}}

            @property
            def request(self) -> Any:
                return None

        return R()

    # Patch client internals
    client = OllamaClient()
    # Patch get_request_id to supply a deterministic value
    monkeypatch.setattr(
        "ai_gateway.providers.ollama_client.get_request_id", lambda: "req-123", raising=True
    )

    async def post_wrapper(*_args: Any, **_kwargs: Any) -> Any:
        return await fake_post(
            url="/api/chat",
            json=_kwargs.get("json", {}),
            headers=_kwargs.get("headers", {}),
        )

    # Replace the internal httpx client object with a simple stub exposing an async post
    class StubClient:
        async def post(self, *args: Any, **kwargs: Any) -> Any:
            return await post_wrapper(*args, **kwargs)

    monkeypatch.setattr(client, "_client", StubClient(), raising=True)

    # Act
    await client.chat(model="m", messages=[{"role": "user", "content": "hi"}])

    # Assert header forwarded
    assert captured_headers.get("X-Request-ID") == "req-123"
