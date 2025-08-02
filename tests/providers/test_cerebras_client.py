from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_gateway.config.config import Settings
from ai_gateway.exceptions.errors import ProviderError
from ai_gateway.providers.cerebras_client import CerebrasClient


@pytest.mark.asyncio
async def test_cerebras_client_mock_mode_success() -> None:
    """Test that mock mode returns deterministic response."""
    client = CerebrasClient(mock_mode=True)

    response = await client.chat(
        model="test-model", messages=[{"role": "user", "content": "Hello"}]
    )

    assert response["id"] == "cb-mock-123"
    assert response["object"] == "chat.completion"
    assert response["model"] == "test-model"
    assert "choices" in response
    assert response["choices"][0]["message"]["content"] == "[cerebras-mock:test-model] echo: Hello"


@pytest.mark.asyncio
async def test_cerebras_client_mock_mode_no_user_content() -> None:
    """Test mock mode with no user messages."""
    client = CerebrasClient(mock_mode=True)

    response = await client.chat(
        model="test-model", messages=[{"role": "system", "content": "You are a helpful assistant"}]
    )

    assert response["choices"][0]["message"]["content"] == "[cerebras-mock:test-model] echo: "


@pytest.mark.asyncio
async def test_cerebras_client_real_mode_no_api_key() -> None:
    """Test that real mode raises ProviderError when no API key is provided."""
    with patch("ai_gateway.providers.cerebras_client.get_settings") as mock_get_settings:
        mock_get_settings.return_value = Settings(
            DEVELOPMENT_MODE=True, REQUIRE_AUTH=True, CEREBRAS_API_KEY=None, ALLOWED_API_KEYS=[]
        )

        with pytest.raises(ProviderError, match="Cerebras API key is required"):
            CerebrasClient(mock_mode=False)


@pytest.mark.asyncio
async def test_cerebras_client_real_mode_not_implemented() -> None:
    """Test that real mode raises ProviderError when SDK is not implemented."""
    client = CerebrasClient(api_key="test-key", mock_mode=False)

    with pytest.raises(ProviderError, match="Upstream provider error"):
        await client.chat(model="test-model", messages=[{"role": "user", "content": "Hello"}])


@pytest.mark.asyncio
async def test_cerebras_client_timeout_configuration() -> None:
    """Test that timeout is properly configured."""
    timeout = 15.0
    client = CerebrasClient(api_key="test-key", timeout_s=timeout, mock_mode=True)

    assert client.timeout_s == timeout


@pytest.mark.asyncio
async def test_cerebras_client_base_url_configuration() -> None:
    """Test that base URL is properly configured."""
    base_url = "https://api.example.com"
    client = CerebrasClient(api_key="test-key", base_url=base_url, mock_mode=True)

    assert client.base_url == base_url


@pytest.mark.asyncio
async def test_cerebras_client_mock_mode_detection() -> None:
    """Test mock mode detection logic."""
    # Test with explicit mock_mode=True
    client1 = CerebrasClient(mock_mode=True)
    assert client1.mock_mode is True

    # Test with PYTEST_CURRENT_TEST (should auto-enable mock mode)
    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "test_example"}):
        client2 = CerebrasClient(api_key="test-key")
        assert client2.mock_mode is True

    # Test with CI environment
    with patch.dict("os.environ", {"CI": "true"}, clear=False):
        with patch("ai_gateway.providers.cerebras_client.get_settings") as mock_get_settings:
            mock_get_settings.return_value = Settings(
                DEVELOPMENT_MODE=False,
                REQUIRE_AUTH=True,
                CEREBRAS_API_KEY="test-key",
                ALLOWED_API_KEYS=["test-key"],
            )
            client3 = CerebrasClient()
            assert client3.mock_mode is True


@pytest.mark.asyncio
async def test_cerebras_client_configuration_precedence() -> None:
    """Test that explicit arguments take precedence over settings."""
    settings = Settings(
        CEREBRAS_API_KEY="settings-key",
        CEREBRAS_BASE_URL="https://settings.example.com",
        REQUEST_TIMEOUT_S=10,
        ALLOWED_API_KEYS=["settings-key"],
    )

    client = CerebrasClient(
        api_key="explicit-key",
        base_url="https://explicit.example.com",
        timeout_s=20,
        settings=settings,
        mock_mode=True,
    )

    assert client.api_key == "explicit-key"
    assert client.base_url == "https://explicit.example.com"
    assert client.timeout_s == 20.0


@pytest.mark.asyncio
async def test_cerebras_client_fallback_settings() -> None:
    """Test that client falls back to settings when no explicit args provided."""
    settings = Settings(
        CEREBRAS_API_KEY="settings-key",
        CEREBRAS_BASE_URL="https://settings.example.com",
        REQUEST_TIMEOUT_S=10,
        ALLOWED_API_KEYS=["settings-key"],
    )

    with patch("ai_gateway.providers.cerebras_client.get_settings", return_value=settings):
        client = CerebrasClient(mock_mode=True)

        assert client.api_key == "settings-key"
        assert client.base_url == "https://settings.example.com"
        assert client.timeout_s == 10.0
