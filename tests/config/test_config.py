from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from ai_gateway.config import constants
from ai_gateway.config.config import Settings, get_settings


@contextmanager
def env_vars(env: dict[str, str | None]) -> Iterator[None]:
    """Temporarily set environment variables for the scope of a test."""
    old = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        # Clear cached settings so each test sees fresh env
        get_settings.cache_clear()
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        get_settings.cache_clear()


def test_defaults_require_auth_with_empty_keys_raises():
    with env_vars(
        {
            "REQUIRE_AUTH": "true",
            "DEVELOPMENT_MODE": "false",
            "ALLOWED_API_KEYS": "",
        }
    ):
        with pytest.raises(Exception):
            Settings()


def test_defaults_allow_empty_keys_in_dev_mode():
    with env_vars(
        {
            "REQUIRE_AUTH": "true",
            "DEVELOPMENT_MODE": "true",
            "ALLOWED_API_KEYS": "",
        }
    ):
        # In dev mode, allow empty keys
        s = Settings()
        assert s.ALLOWED_API_KEYS == []


def test_allowed_api_keys_csv_parsing_and_trimming():
    with env_vars(
        {
            "REQUIRE_AUTH": "false",  # disable strictness for this test
            "ALLOWED_API_KEYS": " key1 ,key2,  key3 , ,",
        }
    ):
        # pydantic-settings expects JSON for list-typed envs unless using a custom source;
        # mimic CSV by setting via code override: pass through env and rely on our CSV parser.
        s = Settings()
        assert s.ALLOWED_API_KEYS == ["key1", "key2", "key3"]


def test_core_defaults_and_types():
    with env_vars(
        {
            "REQUIRE_AUTH": "false",
            "ALLOWED_API_KEYS": "",
        }
    ):
        # When auth not required (tests), empty list is acceptable
        s = Settings()
        assert s.SERVICE_HOST == "0.0.0.0"
        assert s.SERVICE_PORT == 8000
        assert s.LOG_LEVEL == "INFO"
        assert s.ENABLE_SECURITY_HEADERS is True
        assert s.REQUEST_TIMEOUT_S == constants.DEFAULT_REQUEST_TIMEOUT_S


@pytest.mark.parametrize("level", ["debug", "INFO", "Warning", "ERROR"])
def test_log_level_normalization(level: str) -> None:
    with env_vars(
        {
            "REQUIRE_AUTH": "false",
            "ALLOWED_API_KEYS": "",
            "LOG_LEVEL": level,
        }
    ):
        s = Settings()
        assert level.upper() == s.LOG_LEVEL


def test_invalid_log_level_raises():
    with env_vars(
        {
            "REQUIRE_AUTH": "false",
            "LOG_LEVEL": "VERBOSE",
        }
    ):
        with pytest.raises(Exception):
            Settings()


def test_timeout_must_be_positive():
    with env_vars(
        {
            "REQUIRE_AUTH": "false",
            "REQUEST_TIMEOUT_S": "0",
        }
    ):
        with pytest.raises(Exception):
            Settings()


def test_url_fields_accept_valid_when_provided():
    with env_vars(
        {
            "REQUIRE_AUTH": "false",
            "ALLOWED_API_KEYS": "",
            "CEREBRAS_BASE_URL": "https://api.cerebras.ai",
            "OLLAMA_HOST": "http://localhost:11434",
        }
    ):
        s = Settings()
        assert str(s.CEREBRAS_BASE_URL) == "https://api.cerebras.ai"
        assert str(s.OLLAMA_HOST) == "http://localhost:11434"


def test_cached_get_settings_returns_same_instance_until_cleared():
    with env_vars(
        {
            "REQUIRE_AUTH": "false",
            "ALLOWED_API_KEYS": "",
        }
    ):
        a = get_settings()
        b = get_settings()
        assert a is b
        # After changing env and clearing cache, instance should differ
        os.environ["SERVICE_PORT"] = "9000"
        get_settings.cache_clear()
        c = get_settings()
        assert c is not a
        assert c.SERVICE_PORT == 9000
