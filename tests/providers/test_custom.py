import re

import pytest

from ai_gateway.providers.custom import CustomProcessingProvider
from ai_gateway.schemas.openai_chat import ChatCompletionRequest, ChatMessage
from ai_gateway.schemas.openai_embeddings import CreateEmbeddingsRequest
from ai_gateway.schemas.openai_models import Model, ModelPermission


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


@pytest.mark.asyncio
async def test_custom_provider_list_models() -> None:
    """Test list_models method returns valid Model list."""
    provider = CustomProcessingProvider()
    response = await provider.list_models()

    # Check response structure
    assert response.object == "list"
    assert isinstance(response.data, list)
    assert len(response.data) > 0

    # Check each model
    for model in response.data:
        assert isinstance(model, Model)
        assert model.object == "model"
        assert isinstance(model.id, str) and len(model.id) > 0
        assert isinstance(model.created, int)
        assert isinstance(model.owned_by, str) and len(model.owned_by) > 0
        assert isinstance(model.permission, list) and len(model.permission) > 0

        # Check permissions
        for perm in model.permission:
            assert isinstance(perm, ModelPermission)
            assert perm.object == "model_permission"
            assert isinstance(perm.id, str) and len(perm.id) > 0
            assert isinstance(perm.created, int)
            assert isinstance(perm.allow_create_engine, bool)
            assert isinstance(perm.allow_sampling, bool)
            assert isinstance(perm.allow_logprobs, bool)
            assert isinstance(perm.allow_search_indices, bool)
            assert isinstance(perm.allow_view, bool)
            assert isinstance(perm.allow_fine_tuning, bool)
            assert isinstance(perm.is_blocking, bool)


@pytest.mark.asyncio
async def test_custom_provider_create_embeddings() -> None:
    """Test create_embeddings method returns valid embeddings."""
    provider = CustomProcessingProvider()

    # Test with string input
    req1 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input="Hello world",
    )
    resp1 = await provider.create_embeddings(req1)

    assert resp1.object == "list"
    assert isinstance(resp1.data, list)
    assert len(resp1.data) == 1
    assert resp1.model == "text-embedding-ada-002"

    # Check embedding item
    item1 = resp1.data[0]
    assert item1.object == "embedding"
    assert isinstance(item1.embedding, list)
    assert len(item1.embedding) > 0
    assert item1.index == 0

    # Check all embedding values are floats in [-1, 1) range
    for val in item1.embedding:
        assert isinstance(val, float)
        assert -1.0 <= val < 1.0

    # Check usage
    assert resp1.usage.prompt_tokens >= 0
    assert resp1.usage.total_tokens >= 0

    # Test with list of strings input
    req2 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input=["Hello", "world"],
    )
    resp2 = await provider.create_embeddings(req2)

    assert len(resp2.data) == 2
    assert resp2.data[0].index == 0
    assert resp2.data[1].index == 1

    # Embeddings should be different for different inputs
    assert resp2.data[0].embedding != resp2.data[1].embedding

    # Test with list of integers input
    req3 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input=[1, 2, 3],
    )
    resp3 = await provider.create_embeddings(req3)

    assert len(resp3.data) == 1
    assert resp3.data[0].index == 0

    # Test with list of list of integers input
    req4 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input=[[1, 2], [3, 4]],
    )
    resp4 = await provider.create_embeddings(req4)

    assert len(resp4.data) == 2
    assert resp4.data[0].index == 0
    assert resp4.data[1].index == 1
