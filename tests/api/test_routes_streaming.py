import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status

from ai_gateway.api.app import get_app
from ai_gateway.config.config import Settings, get_settings
from ai_gateway.middleware.auth import auth_bearer


@pytest.mark.asyncio
async def test_ollama_streaming_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verifies:
      - POST /ollama/v1/chat/completions with stream=true returns SSE event-stream
      - Includes correlation headers (X-Request-ID and x-request-id)
      - Frames events as 'data: {...}\\n\\n' and ends with 'data: [DONE]\\n\\n'
    """
    # Arrange a fake provider with stream_chat_completions implemented
    chunks: list[dict[str, Any]] = [
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1_700_000_000,
            "model": "llama3",
            "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1_700_000_000,
            "model": "llama3",
            "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": None}],
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1_700_000_000,
            "model": "llama3",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        },
    ]

    async def fake_stream_chat_completions(self: Any, _req: Any) -> AsyncIterator[dict[str, Any]]:
        # Method signature must accept 'self' when monkeypatched on the class
        for ch in chunks:
            await asyncio.sleep(0)  # yield control
            yield ch

    # Patch the provider in the app composition root
    # Ensure auth passes by overriding settings dependency to include our test key.
    def _test_settings() -> Settings:
        s = get_settings()
        data = s.model_dump()
        # Accept "test" token and ensure dev bypass is enabled to avoid strict auth in tests
        data["ALLOWED_API_KEYS"] = "test"
        data["LOG_LEVEL"] = "DEBUG"
        data["DEVELOPMENT_MODE"] = True
        data["REQUIRE_AUTH"] = False
        return Settings(**data)

    def _allow_auth() -> Any:
        # Bypass auth validation explicitly for tests using our known token
        return None

    app = get_app()
    # Override dependencies so routes read test settings (including allowed API key)
    app.dependency_overrides[get_settings] = _test_settings
    # Explicitly bypass auth dependency for these tests to avoid 401
    app.dependency_overrides[auth_bearer] = lambda: None

    # Also ensure environment variables reflect permissive auth for any codepaths reading os.environ early
    import os

    os.environ["ALLOWED_API_KEYS"] = "test"
    os.environ["DEVELOPMENT_MODE"] = "true"
    os.environ["REQUIRE_AUTH"] = "false"

    # Find the provider instance created in app state via dependency injection. We patch at attribute level
    # by monkeypatching the OllamaProvider.stream_chat_completions method.
    from ai_gateway.providers.ollama import OllamaProvider

    monkeypatch.setattr(
        OllamaProvider, "stream_chat_completions", fake_stream_chat_completions, raising=True
    )

    # Use a token accepted by auth in tests; some apps may expect a specific default like "test"
    headers = {"Authorization": "Bearer test", "X-Request-ID": "req-123"}

    # Use ASGITransport to mount the FastAPI app in httpx AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/ollama/v1/chat/completions",
            json={
                "model": "llama3",
                "stream": True,
                "messages": [{"role": "user", "content": "Hi"}],
            },
            headers=headers,
        )

        # Should be an event-stream response
        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers.get("content-type", "").startswith("text/event-stream")
        # correlation headers
        assert "x-request-id" in resp.headers
        assert "X-Request-ID" in resp.headers or "x-request-id" in resp.headers

        # Collect streamed body (httpx buffers test app responses)
        body = resp.text
        # Ensure data events for each chunk
        assert f"data: {json.dumps(chunks[0], separators=(',', ':'))}\n\n" in body
        assert f"data: {json.dumps(chunks[1], separators=(',', ':'))}\n\n" in body
        assert f"data: {json.dumps(chunks[2], separators=(',', ':'))}\n\n" in body
        # Terminal sentinel
        assert "data: [DONE]\n\n" in body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/v1/chat/completions",
        "/cerebras/v1/chat/completions",
    ],
)
async def test_streaming_unsupported_providers_return_501(path: str) -> None:
    """
    Verifies non-Ollama namespaces return 501 when stream=true per S1/S3 rules.
    """
    # Ensure auth passes by overriding settings dependency to include our test key.
    app = get_app()
    # Ensure env for this test function as well
    import os

    os.environ["ALLOWED_API_KEYS"] = "test"
    os.environ["DEVELOPMENT_MODE"] = "true"
    os.environ["REQUIRE_AUTH"] = "false"

    def _test_settings() -> Settings:
        s = get_settings()
        data = s.model_dump()
        data["ALLOWED_API_KEYS"] = "test"
        data["LOG_LEVEL"] = "DEBUG"
        data["DEVELOPMENT_MODE"] = True
        data["REQUIRE_AUTH"] = False
        return Settings(**data)

    def _allow_auth() -> Any:
        return None

    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[auth_bearer] = lambda: None

    import os

    os.environ["ALLOWED_API_KEYS"] = "test"
    os.environ["DEVELOPMENT_MODE"] = "true"
    os.environ["REQUIRE_AUTH"] = "false"

    headers = {"Authorization": "Bearer test"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            path,
            json={
                "model": "gpt-3.5-mock",
                "stream": True,
                "messages": [{"role": "user", "content": "Hi"}],
            },
            headers=headers,
        )
        assert resp.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert resp.headers.get("content-type", "").startswith("application/json")
        # correlation headers present on error responses too
        assert "x-request-id" in resp.headers
        payload = resp.json()
        assert "error" in payload
        assert payload["error"]["type"]
        assert payload["error"]["message"]
