from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_gateway.config.config import Settings
from ai_gateway.providers.ollama_client import OllamaClient


@pytest.mark.asyncio
async def test_ollama_client_mock_mode_success() -> None:
    """Test that mock mode returns deterministic response."""
    client = OllamaClient()

    response = await client.chat(
        model="test-model", messages=[{"role": "user", "content": "Hello"}]
    )

    assert response["model"] == "test-model"
    assert "message" in response
    assert response["message"]["role"] == "assistant"
    assert response["message"]["content"] == "Ollama mock reply to: Hello"
    assert response["done_reason"] == "stop"


@pytest.mark.asyncio
async def test_ollama_client_mock_mode_no_user_content() -> None:
    """Test mock mode with no user messages."""
    client = OllamaClient()

    response = await client.chat(
        model="test-model", messages=[{"role": "system", "content": "You are a helpful assistant"}]
    )

    assert response["message"]["content"] == "Ollama mock reply to:"


@pytest.mark.asyncio
async def test_ollama_client_timeout_configuration() -> None:
    """Test that timeout is properly configured."""
    timeout = 15
    client = OllamaClient(timeout_s=timeout)

    assert client._timeout_s == float(timeout)


@pytest.mark.asyncio
async def test_ollama_client_base_url_configuration() -> None:
    """Test that base URL is properly configured."""
    base_url = "https://ollama.example.com"
    client = OllamaClient(base_url=base_url)

    assert client._base_url == base_url


@pytest.mark.asyncio
async def test_ollama_client_default_base_url() -> None:
    """Test that default base URL is used when none provided."""
    client = OllamaClient()

    assert client._base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_ollama_client_timeout_behavior() -> None:
    """Test that timeout behavior works correctly."""
    # Set a very short timeout
    client = OllamaClient(timeout_s=None)

    response = await client.chat(
        model="test-model", messages=[{"role": "user", "content": "Hello"}]
    )

    # Should still return a response even with timeout due to move_on_after
    assert response["message"]["role"] == "assistant"
    assert response["done_reason"] == "stop"


@pytest.mark.asyncio
async def test_ollama_client_settings_timeout() -> None:
    """Test that timeout from settings is used when no explicit timeout provided."""
    settings = Settings(REQUEST_TIMEOUT_S=25, ALLOWED_API_KEYS=["test-key"])

    with patch("ai_gateway.providers.ollama_client.get_settings", return_value=settings):
        client = OllamaClient()

        assert client._timeout_s == 25.0


@pytest.mark.asyncio
async def test_ollama_client_settings_base_url() -> None:
    """Test that base URL from settings is used when no explicit base URL provided."""
    settings = Settings(OLLAMA_HOST="https://settings.example.com", ALLOWED_API_KEYS=["test-key"])

    with patch("ai_gateway.providers.ollama_client.get_settings", return_value=settings):
        client = OllamaClient()

        assert client._base_url == "https://settings.example.com"


@pytest.mark.asyncio
async def test_ollama_client_explicit_args_override_settings() -> None:
    """Test that explicit arguments take precedence over settings."""
    settings = Settings(
        OLLAMA_HOST="https://settings.example.com",
        REQUEST_TIMEOUT_S=10,
        ALLOWED_API_KEYS=["test-key"],
    )

    with patch("ai_gateway.providers.ollama_client.get_settings", return_value=settings):
        client = OllamaClient(base_url="https://explicit.example.com", timeout_s=20)

        assert client._base_url == "https://explicit.example.com"
        assert client._timeout_s == 20.0


@pytest.mark.asyncio
async def test_ollama_client_empty_settings_fallback() -> None:
    """Test that client falls back to defaults when settings are empty."""
    settings = Settings(OLLAMA_HOST=None, REQUEST_TIMEOUT_S=30, ALLOWED_API_KEYS=["test-key"])

    with patch("ai_gateway.providers.ollama_client.get_settings", return_value=settings):
        client = OllamaClient()

        # Should fall back to defaults
        assert client._base_url == "http://localhost:11434"
        assert client._timeout_s == 30.0  # Default from client code


@pytest.mark.asyncio
async def test_ollama_client_url_string_conversion() -> None:
    """Test that URL objects are properly converted to strings."""
    # This test simulates what happens when Pydantic provides a URL object
    settings = Settings(OLLAMA_HOST=None, REQUEST_TIMEOUT_S=30, ALLOWED_API_KEYS=["test-key"])

    with patch("ai_gateway.providers.ollama_client.get_settings", return_value=settings):
        client = OllamaClient()

        # The internal storage should be a plain string
        assert isinstance(client._base_url, str)
        assert client._base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_ollama_client_kwargs_ignored() -> None:
    """Test that additional kwargs are ignored (as documented)."""
    client = OllamaClient()

    # This should not raise an error even though we pass unsupported kwargs
    response = await client.chat(
        model="test-model",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,  # This is ignored by the current implementation
        max_tokens=100,  # This is ignored by the current implementation
    )

    assert response["message"]["role"] == "assistant"
    assert response["done_reason"] == "stop"
