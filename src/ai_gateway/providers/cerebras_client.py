from __future__ import annotations

import os
from typing import Any

from ai_gateway.config.config import Settings, get_settings
from ai_gateway.exceptions.errors import ProviderError


class CerebrasClient:
    """Thin async wrapper for the Cerebras Chat Completions SDK/client.

    This class encapsulates configuration (API key, base URL, timeout) and exposes a
    simple async `chat` method that returns a dict-compatible payload. In CI and test
    environments, this client supports a deterministic mock mode to avoid any network IO.

    The actual Cerebras SDK is not imported here to keep this package lightweight and
    fully mockable in tests. A future phase may adapt this wrapper to the official SDK.

    Attributes:
        api_key: API key used to authenticate with Cerebras Cloud.
        base_url: Optional base URL for the Cerebras API endpoint.
        timeout_s: Request timeout in seconds.
        mock_mode: If True, return deterministic mock responses (no network).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_s: float | None = None,
        *,
        settings: Settings | None = None,
        mock_mode: bool | None = None,
    ) -> None:
        # Prefer injected settings (used by tests via monkeypatch). Fall back to get_settings().
        try:
            cfg = settings or get_settings()
        except Exception:
            # Avoid validation explosions in editor/CI analyzers; default to permissive dev-like settings.
            cfg = Settings(
                ALLOWED_API_KEYS=[],
                ALLOWED_API_KEYS_RAW="",
                DEVELOPMENT_MODE=True,
                REQUIRE_AUTH=True,
            )
        # Resolve configuration with explicit args taking precedence over Settings.
        self.api_key: str | None = api_key if api_key is not None else cfg.CEREBRAS_API_KEY
        # Coerce possible pydantic AnyHttpUrl/HttpUrl to str for internal storage.
        self.base_url: str | None
        if base_url is not None:
            self.base_url = base_url
        elif cfg.CEREBRAS_BASE_URL is not None:
            self.base_url = str(cfg.CEREBRAS_BASE_URL)
        else:
            self.base_url = None
        self.timeout_s: float = float(timeout_s if timeout_s is not None else cfg.REQUEST_TIMEOUT_S)

        # Determine mock mode:
        # - Explicit mock_mode arg overrides all.
        # - Else enabled when RUNNING_IN_CI=true or DEVELOPMENT_MODE=true and no api key provided.
        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            running_in_ci = os.getenv("CI", "").lower() in {"1", "true", "yes"}
            dev_mode = bool(getattr(cfg, "DEVELOPMENT_MODE", False))
            # In tests, get_settings is monkeypatched and we generally want mock mode.
            self.mock_mode = (
                True
                if "PYTEST_CURRENT_TEST" in os.environ
                else (running_in_ci or (dev_mode and not self.api_key))
            )

        # In real mode, ensure API key is present to avoid accidental unauthenticated calls.
        if not self.mock_mode and not self.api_key:
            raise ProviderError("Cerebras API key is required for real client usage")

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a chat completion request.

        Args:
            model: The target model identifier.
            messages: List of messages with keys: {'role': 'user'|'assistant'|'system', 'content': str}.
            **kwargs: Additional provider-specific options (temperature, max_tokens, etc.).

        Returns:
            A dictionary mimicking Cerebras Chat Completions response. In mock mode this is a
            deterministic payload. In real mode, this should call the Cerebras SDK.

        Raises:
            ProviderError: On configuration or upstream errors (in real mode).
        """
        if self.mock_mode:
            # Deterministic mock response for tests/CI:
            last_user = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_user = str(m.get("content", ""))
                    break

            content = f"[cerebras-mock:{model}] echo: {last_user}"
            return {
                "id": "cb-mock-123",
                "object": "chat.completion",
                "created": 0,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

        # Real mode path (placeholder for future SDK integration).
        try:
            # Deferred import to keep module importable without SDK installed.
            # Example structure (commented for now):
            # from cerebras.cloud.sdk import AsyncCerebras
            #
            # client = AsyncCerebras(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout_s)
            # resp = await client.chat.completions.create(model=model, messages=messages, **kwargs)
            # return resp.to_dict() if hasattr(resp, "to_dict") else resp
            raise NotImplementedError(
                "Cerebras SDK integration not implemented yet; running in real mode is disabled"
            )
        except NotImplementedError as err:
            raise ProviderError("Upstream provider error") from err  # normalized message
        except Exception:
            # Normalize any unexpected upstream exception
            raise ProviderError("Upstream provider error") from None
