from __future__ import annotations

import pytest

from ai_gateway.exceptions.errors import ProviderError
from ai_gateway.providers.cerebras import CerebrasProvider
from ai_gateway.providers.cerebras_client import CerebrasClient
from ai_gateway.schemas.openai_chat import ChatCompletionRequest, ChatMessage


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
