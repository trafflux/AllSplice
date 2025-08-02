from __future__ import annotations

from typing import Any

import anyio

from ai_gateway.config.config import get_settings


class OllamaClient:
    """Thin async client wrapper for Ollama chat API.

    This wrapper intentionally avoids importing external SDKs; it exposes a minimal
    interface that can be mocked in tests. Network I/O is represented via a placeholder
    to keep CI deterministic; Phase 12 may replace with real HTTP calls.
    """

    def __init__(self, base_url: str | None = None, timeout_s: int | None = None) -> None:
        settings = get_settings()
        resolved_base = base_url or (settings.OLLAMA_HOST or "http://localhost:11434")
        # Ensure a plain string for internal use, regardless of Pydantic URL types.
        self._base_url = str(resolved_base)
        self._timeout_s = float(timeout_s or settings.REQUEST_TIMEOUT_S or 30)

    async def chat(
        self, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
        """Perform a chat call against Ollama.

        Args:
            model: Model name to use.
            messages: Sequence of {"role": "...", "content": "..."} dicts in OpenAI format.
            **kwargs: Additional provider-specific args (ignored for now).

        Returns:
            A dict emulating Ollama's response structure that will be mapped by the provider.

        Notes:
            This mock implementation returns a deterministic response to keep tests hermetic.
            Replace with real HTTP logic (httpx.AsyncClient) in a later phase.
        """
        # Simulate I/O latency without actual network dependency
        with anyio.move_on_after(self._timeout_s):
            await anyio.sleep(0)  # yield control

        # Deterministic mock echo of last user content (if any)
        last = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        content = f"Ollama mock reply to: {last.get('content') if last else ''}".strip()

        return {
            "model": model,
            "message": {"role": "assistant", "content": content or "Hello from Ollama mock."},
            "done_reason": "stop",
        }
