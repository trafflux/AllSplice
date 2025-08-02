import re

import pytest

from ai_gateway.providers.custom import CustomProcessingProvider
from ai_gateway.schemas.openai_chat import ChatCompletionRequest, ChatMessage


@pytest.mark.asyncio
async def test_custom_provider_response_shape_and_values() -> None:
    provider = CustomProcessingProvider()
    req = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[ChatMessage(role="user", content="Hello")],
    )

    resp = await provider.chat_completions(req)

    # id format
    assert resp.id.startswith("chatcmpl-")
    assert re.fullmatch(r"chatcmpl-[0-9a-f]{32}", resp.id), resp.id

    # object literal and created
    assert resp.object == "chat.completion"
    assert isinstance(resp.created, int)

    # model echo
    assert resp.model == req.model

    # choices
    assert len(resp.choices) == 1
    choice = resp.choices[0]
    assert choice.index == 0
    assert choice.finish_reason == "stop"
    assert choice.message.role == "assistant"
    assert "CustomProcessingProvider" in choice.message.content
    assert req.model in choice.message.content

    # usage
    assert resp.usage.prompt_tokens == 0
    assert resp.usage.completion_tokens == 0
    assert resp.usage.total_tokens == 0


@pytest.mark.asyncio
async def test_custom_provider_is_deterministic_shape_not_message_content() -> None:
    """We only require deterministic shape and fields; message content includes UUID-based id,
    so responses differ but remain schema consistent across calls."""
    provider = CustomProcessingProvider()
    req = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role="user", content="Ping")],
    )

    r1 = await provider.chat_completions(req)
    r2 = await provider.chat_completions(req)

    # Different ids per call but correct prefix
    assert r1.id != r2.id
    assert r1.id.startswith("chatcmpl-") and r2.id.startswith("chatcmpl-")

    # Shape and literals remain stable
    for r in (r1, r2):
        assert r.object == "chat.completion"
        assert isinstance(r.created, int)
        assert r.model == req.model
        assert len(r.choices) == 1
        assert r.choices[0].finish_reason == "stop"
        assert r.usage.total_tokens == 0
