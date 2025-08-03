from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "src")))

from ai_gateway.schemas.openai_embeddings import (
    CreateEmbeddingsRequest,
    CreateEmbeddingsResponse,
    EmbeddingItem,
    EmbeddingUsage,
    deterministic_vector,
    normalize_input_to_strings,
)


def test_create_embeddings_request_valid() -> None:
    """Test valid CreateEmbeddingsRequest creation."""
    # String input
    req1 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input="Hello world",
    )
    assert req1.model == "text-embedding-ada-002"
    assert req1.input == "Hello world"
    assert req1.encoding_format == "float"

    # List of strings input
    req2 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input=["Hello", "world"],
    )
    assert req2.input == ["Hello", "world"]

    # List of integers input
    req3 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input=[1, 2, 3],
    )
    assert req3.input == [1, 2, 3]

    # List of list of integers input
    req4 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input=[[1, 2], [3, 4]],
    )
    assert req4.input == [[1, 2], [3, 4]]

    # With user and encoding_format
    req5 = CreateEmbeddingsRequest(
        model="text-embedding-ada-002",
        input="Hello",
        user="user123",
        encoding_format="base64",
    )
    assert req5.user == "user123"
    assert req5.encoding_format == "base64"


def test_create_embeddings_request_rejects_empty_model() -> None:
    """Test CreateEmbeddingsRequest rejects empty model."""
    with pytest.raises(Exception):
        CreateEmbeddingsRequest(
            model="  ",
            input="Hello",
        )


def test_create_embeddings_request_input_validation() -> None:
    """Test CreateEmbeddingsRequest input validation."""
    # Valid cases are tested in test_create_embeddings_request_valid

    # None input should fail
    with pytest.raises(Exception):
        CreateEmbeddingsRequest(
            model="text-embedding-ada-002",
            input=None,  # type: ignore[arg-type]
        )

    # Mixed list types should fail
    with pytest.raises(Exception):
        CreateEmbeddingsRequest(
            model="text-embedding-ada-002",
            input=["hello", 1],  # type: ignore[arg-type]
        )

    # Invalid nested list types should fail
    with pytest.raises(Exception):
        CreateEmbeddingsRequest(
            model="text-embedding-ada-002",
            input=[[1, 2], ["a", "b"]],  # type: ignore[arg-type]
        )


def test_embedding_item_valid() -> None:
    """Test valid EmbeddingItem creation."""
    item = EmbeddingItem(
        embedding=[0.1, 0.2, 0.3],
        index=0,
    )
    assert item.object == "embedding"
    assert item.embedding == [0.1, 0.2, 0.3]
    assert item.index == 0


def test_embedding_item_rejects_empty_embedding() -> None:
    """Test EmbeddingItem rejects empty embedding."""
    with pytest.raises(Exception):
        EmbeddingItem(
            embedding=[],
            index=0,
        )


def test_embedding_item_index_validation() -> None:
    """Test EmbeddingItem index validation."""
    # Valid case
    item = EmbeddingItem(
        embedding=[0.1, 0.2],
        index=5,
    )
    assert item.index == 5

    # Invalid case - negative index
    with pytest.raises(Exception):
        EmbeddingItem(
            embedding=[0.1, 0.2],
            index=-1,
        )


def test_embedding_usage_valid() -> None:
    """Test valid EmbeddingUsage creation."""
    usage = EmbeddingUsage(
        prompt_tokens=10,
        total_tokens=10,
    )
    assert usage.prompt_tokens == 10
    assert usage.total_tokens == 10


def test_embedding_usage_validation() -> None:
    """Test EmbeddingUsage field validation."""
    # Valid case
    usage = EmbeddingUsage(
        prompt_tokens=5,
        total_tokens=5,
    )
    assert usage.prompt_tokens == 5
    assert usage.total_tokens == 5

    # Invalid cases - negative values
    with pytest.raises(Exception):
        EmbeddingUsage(
            prompt_tokens=-1,
            total_tokens=5,
        )

    with pytest.raises(Exception):
        EmbeddingUsage(
            prompt_tokens=5,
            total_tokens=-1,
        )


def test_create_embeddings_response_valid() -> None:
    """Test valid CreateEmbeddingsResponse creation."""
    item = EmbeddingItem(
        embedding=[0.1, 0.2, 0.3],
        index=0,
    )

    usage = EmbeddingUsage(
        prompt_tokens=10,
        total_tokens=10,
    )

    response = CreateEmbeddingsResponse(
        data=[item],
        model="text-embedding-ada-002",
        usage=usage,
    )
    assert response.object == "list"
    assert len(response.data) == 1
    assert response.data[0] == item
    assert response.model == "text-embedding-ada-002"
    assert response.usage == usage


def test_create_embeddings_response_rejects_empty_data() -> None:
    """Test CreateEmbeddingsResponse rejects empty data."""
    usage = EmbeddingUsage(
        prompt_tokens=10,
        total_tokens=10,
    )

    with pytest.raises(Exception):
        CreateEmbeddingsResponse(
            data=[],
            model="text-embedding-ada-002",
            usage=usage,
        )


def test_deterministic_vector() -> None:
    """Test deterministic_vector function."""
    # Same input should produce same output
    vec1 = deterministic_vector("hello", dim=4)
    vec2 = deterministic_vector("hello", dim=4)
    assert vec1 == vec2
    assert len(vec1) == 4

    # Different inputs should produce different outputs
    vec3 = deterministic_vector("world", dim=4)
    assert vec1 != vec3

    # Check all values are in [-1, 1) range
    for val in vec1:
        assert -1.0 <= val < 1.0


def test_normalize_input_to_strings() -> None:
    """Test normalize_input_to_strings function."""
    # String input
    result1 = normalize_input_to_strings("hello")
    assert result1 == ["hello"]

    # List of strings
    result2 = normalize_input_to_strings(["hello", "world"])
    assert result2 == ["hello", "world"]

    # List of integers
    result3 = normalize_input_to_strings([1, 2, 3])
    assert result3 == ["1 2 3"]

    # List of list of integers
    result4 = normalize_input_to_strings([[1, 2], [3, 4]])
    assert result4 == ["1 2", "3 4"]

    # Empty list
    result5 = normalize_input_to_strings([])
    assert result5 == []


def test_normalize_input_to_strings_validation() -> None:
    """Test normalize_input_to_strings validation."""
    # Mixed list should fail
    with pytest.raises(Exception):
        normalize_input_to_strings(["hello", 1])  # type: ignore[arg-type]

    # Invalid nested list should fail
    with pytest.raises(Exception):
        normalize_input_to_strings([[1, 2], ["a", "b"]])  # type: ignore[arg-type]
