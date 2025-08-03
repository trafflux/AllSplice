import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest

from ai_gateway.providers.ollama import OllamaProvider
from ai_gateway.providers.ollama_client import OllamaClient
from ai_gateway.schemas.openai_chat import ChatCompletionRequest, ChatMessage


class _FakeOllamaClient(OllamaClient):
    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        # Bypass base init; we don't need httpx client for mapping tests
        self._chunks: list[dict[str, Any]] = chunks

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        options: dict[str, Any] | None = None,
        format_hint: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        for ch in self._chunks:
            await asyncio.sleep(0)
            yield ch


@pytest.mark.asyncio
async def test_stream_mapping_to_openai_chunks() -> None:
    """
    Given upstream Ollama-like stream objects, verify provider maps to OpenAI-compatible
    chat.completion.chunk events, including final finish_reason mapping.
    """
    upstream: list[dict[str, Any]] = [
        {"message": {"content": "Hel"}},
        {"message": {"content": "lo"}},
        {"done": True, "done_reason": "stop"},
    ]
    fake_client = _FakeOllamaClient(upstream)
    provider = OllamaProvider(client=fake_client)

    req = ChatCompletionRequest(
        model="llama3",
        messages=[ChatMessage(role="user", content="Hi")],
        stream=True,
    )

    observed: list[dict[str, Any]] = []
    async for chunk in provider.stream_chat_completions(req):
        observed.append(chunk)

    # Expect at least three chunks: two deltas + a final with finish_reason
    assert len(observed) >= 3
    # First two contain delta.content text
    assert observed[0]["object"] == "chat.completion.chunk"
    assert observed[0]["choices"][0]["delta"]["content"] == "Hel"
    assert observed[1]["choices"][0]["delta"]["content"] == "lo"
    # Final one should carry finish_reason and no delta content
    final = observed[-1]
    assert final["object"] == "chat.completion.chunk"
    assert final["choices"][0]["finish_reason"] == "stop"
    assert "content" not in final["choices"][0].get("delta", {})


@pytest.mark.asyncio
async def test_stream_mapping_handles_empty_and_non_text_chunks() -> None:
    """
    Provider should ignore non-dict or empty lines and still produce well-formed OpenAI chunks.
    """
    upstream: list[dict[str, Any]] = [
        {},  # ignored content
        {"irrelevant": True},
        {"message": {"content": ""}},  # empty delta -> may be mapped to empty or skipped
        {"done": True, "done_reason": "stop"},
    ]
    fake_client = _FakeOllamaClient(upstream)
    provider = OllamaProvider(client=fake_client)

    req = ChatCompletionRequest(
        model="llama3",
        messages=[ChatMessage(role="user", content="Hi")],
        stream=True,
    )

    observed: list[dict[str, Any]] = []
    async for chunk in provider.stream_chat_completions(req):
        observed.append(chunk)

    assert observed, "Expected at least a final chunk"
    assert observed[-1]["choices"][0]["finish_reason"] == "stop"
