import asyncio
import json as jsonlib
from collections.abc import AsyncIterator
from typing import Any, TypeVar

import pytest

from ai_gateway.providers.ollama_client import OllamaClient


class _FakeStreamResponse:
    """
    Minimal stand-in for httpx.Response returned by AsyncClient.stream(...),
    exposing aiter_lines() and aiter_bytes() used by our client.
    """

    def __init__(
        self, lines: list[bytes] | None = None, text_lines: list[str] | None = None
    ) -> None:
        self._byte_lines = lines or []
        self._text_lines = text_lines or []

    async def aiter_lines(self) -> AsyncIterator[str]:
        # Prefer text lines when provided to simulate httpx line decoding
        if self._text_lines:
            for line in self._text_lines:
                await asyncio.sleep(0)
                yield line
            return
        # Fallback: decode byte lines
        for b in self._byte_lines:
            await asyncio.sleep(0)
            yield b.decode("utf-8", errors="ignore")

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for b in self._byte_lines:
            await asyncio.sleep(0)
            yield b


T = TypeVar("T")


class _FakeAsyncClient:
    """
    Fakes httpx.AsyncClient.stream context manager. We only emulate the subset used by OllamaClient.
    """

    def __init__(self, response: _FakeStreamResponse) -> None:
        self._response = response

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any
    ) -> None:
        return None

    def stream(
        self,
        method: str,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> "_FakeStreamContext":
        # Validate expected method/url minimally
        assert method.upper() == "POST"
        assert url.endswith("/api/chat")
        # Return an async context manager yielding our fake response
        return _FakeStreamContext(self._response)


class _FakeStreamContext:
    def __init__(self, response: _FakeStreamResponse) -> None:
        self._response = response

    async def __aenter__(self) -> _FakeStreamResponse:
        return self._response

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any
    ) -> None:
        return None


@pytest.mark.asyncio
async def test_chat_stream_parses_jsonl_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure OllamaClient.chat_stream yields parsed dicts for plain JSONL streams and terminates on done=true.
    """
    # Given two normal content chunks and a terminal done chunk
    lines = [
        jsonlib.dumps({"message": {"content": "Hel"}}).encode(),
        jsonlib.dumps({"message": {"content": "lo"}}).encode(),
        jsonlib.dumps({"done": True, "done_reason": "stop"}).encode(),
    ]
    response = _FakeStreamResponse(lines=lines)

    # Patch OllamaClient._client to our fake
    client = OllamaClient(base_url="http://ollama.test", timeout_s=5)
    monkeypatch.setattr(client, "_client", _FakeAsyncClient(response), raising=True)

    chunks = []
    async for item in client.chat_stream(
        model="llama3",
        messages=[{"role": "user", "content": "Hi"}],
        options=None,
        response_format=None,
    ):
        chunks.append(item)

    assert {"message": {"content": "Hel"}} in chunks
    assert {"message": {"content": "lo"}} in chunks
    # last element should be the done marker yielded once
    assert chunks[-1] == {"done": True, "done_reason": "stop"}


@pytest.mark.asyncio
async def test_chat_stream_parses_sse_prefixed_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure parsing tolerates SSE 'data:' prefix and ignores [DONE] sentinel line.
    """
    text_lines = [
        "data: " + jsonlib.dumps({"message": {"content": "A"}}),
        "data: " + jsonlib.dumps({"message": {"content": "B"}}),
        "data: " + jsonlib.dumps({"done": True, "done_reason": "stop"}),
        "data: [DONE]",
    ]
    response = _FakeStreamResponse(text_lines=text_lines)

    client = OllamaClient(base_url="http://ollama.test", timeout_s=5)
    monkeypatch.setattr(client, "_client", _FakeAsyncClient(response), raising=True)

    chunks = []
    async for item in client.chat_stream(
        model="llama3",
        messages=[{"role": "user", "content": "Hi"}],
        options=None,
        response_format=None,
    ):
        chunks.append(item)

    assert {"message": {"content": "A"}} in chunks
    assert {"message": {"content": "B"}} in chunks
    assert chunks[-1] == {"done": True, "done_reason": "stop"}
    # Ensure items are dicts; no stray string "[DONE]" passed through
    assert all(isinstance(x, dict) for x in chunks)


@pytest.mark.asyncio
async def test_message_content_coercion_list_to_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensures list-based content is coerced to string to avoid 400 on Ollama 0.10.1.
    We verify the request payload sent to upstream includes the flattened content.
    """

    captured_payload: dict[str, Any] = {}

    class _CaptureClient(_FakeAsyncClient):
        def stream(
            self,
            method: str,
            url: str,
            json: dict[str, Any],
            headers: dict[str, str],
            timeout: float,
        ) -> "_FakeStreamContext":
            nonlocal captured_payload
            captured_payload = json
            # Minimal single done event stream so generator terminates.
            # Build line using standard json module; ensure no shadowing of module name.
            payload_dict: dict[str, Any] = {"done": True, "done_reason": "stop"}
            done_line: str = "data: " + jsonlib.dumps(payload_dict)
            resp = _FakeStreamResponse(text_lines=[done_line])
            return _FakeStreamContext(resp)

    response = _FakeStreamResponse(text_lines=[])
    cap_client = _CaptureClient(response)

    client = OllamaClient(base_url="http://ollama.test", timeout_s=5)
    monkeypatch.setattr(client, "_client", cap_client, raising=True)

    # Use Any typing for messages to satisfy chat_stream signature expectation.
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Part1"},
                {"type": "text", "text": " Part2"},
            ],
        }
    ]

    # Drain the stream
    async for _ in client.chat_stream(
        model="llama3", messages=messages, options=None, response_format=None
    ):
        pass

    # Assert flattening occurred in outbound payload
    sent_messages = captured_payload.get("messages") or []
    assert sent_messages and isinstance(sent_messages[0]["content"], str)
    assert sent_messages[0]["content"] == "Part1 Part2"
