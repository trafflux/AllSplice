# Phase 7 — Ollama Integration

Status: In Progress

Scope
Implement Ollama client and provider, expose `/ollama/v1/chat/completions` using OpenAI-compatible schema, handle errors, and add tests. Keep strict typing and TDD. No real network calls in CI; use mocks.

7.1 Client Wrapper — src/ai_gateway/providers/ollama_client.py
- [x] Async client abstraction:
  - Base URL from Settings.OLLAMA_HOST (default http://localhost:11434)
  - Request timeout from Settings.REQUEST_TIMEOUT_S
  - Method: `async def chat(self, model: str, messages: list[dict[str, str]], **kwargs) -> dict`
- [~] Error mapping: timeouts/network errors → ProviderError (502) in provider layer
  - Status: Implemented at provider layer. Client remains deterministic/mock; real network error mapping deferred until real client integration.
- [x] Docstrings and strict typing
- [x] No secrets logged
Notes: Client exists and is used by OllamaProvider. Deterministic behavior keeps CI hermetic.

7.2 Provider Implementation — src/ai_gateway/providers/ollama.py
- [x] `class OllamaProvider(ChatProvider)` with:
  - `async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse`
- [x] Map OpenAI Chat request → Ollama chat API request
- [x] Transform Ollama response → OpenAI ChatCompletionResponse
  - id: "chatcmpl-<uuid>"
  - object: "chat.completion"
  - created: int(epoch seconds)
  - choices[0]: assistant message, finish_reason="stop", index=0
  - usage: conservative zeros if absent (TODO note)
- [x] Catch client exceptions and raise ProviderError(502)
- [x] Docstrings and strict typing; no secret leakage

7.3 Router Wiring
- [x] Wire `/ollama/v1/chat/completions` to instantiate OllamaProvider and return `provider.chat_completions(req)`
- [x] Retain `Depends(auth_bearer)`

7.4 Tests
- [ ] tests/providers/test_ollama.py
  - Unit tests for mapping in/out with mocked client
  - Error path → ProviderError(502) normalized
  Status: Missing; to be added. [BLOCKER]
- [~] tests/api/test_routes.py
  - `/ollama/v1/chat/completions` returns 200 with valid auth; schema correct
  - 401 without/invalid auth
  Status: Partially passing historically; currently impacted by Settings validation ordering at app creation. Stabilize by monkeypatching `ai_gateway.config.config.get_settings` before `get_app()`, optionally clearing the cache, and asserting standardized `{"error": {...}}` payload plus `WWW-Authenticate` on 401.
- [x] No real network in CI

7.5 Configuration
- [x] Settings include OLLAMA_HOST and REQUEST_TIMEOUT_S with defaults/types and validation
- [ ] Update `.env.example` comments for OLLAMA_HOST (optional; used for Ollama endpoint)
  Status: Missing. [ACTION]

7.6 Docs & Acceptance
- [ ] Update README curl example for `/ollama/v1/chat/completions`
- [~] Phase acceptance:
  - [x] Provider/client implemented with strict typing
  - [x] Route returns OpenAI-compatible response
  - [x] Errors normalized to ProviderError(502)
  - [~] Tests green: regressions due to standardized error handlers and Settings validation timing; to be addressed alongside Phases 8–9.
  Blockers: `tests/providers/test_ollama.py` missing; route tests need stabilization.

Dependencies and Interactions
- Settings fragility from earlier phases: Validation at app creation can preempt test monkeypatches. Mitigate in tests via early monkeypatch and cache clearing. Longer-term fix via DI composition root (Phase 9/10).
- Exceptions standardization from Phase 8 in place; ensure tests assert standardized error envelope.

Current Issues Affecting This Phase
- `tests/api/test_routes.py` failing due to Settings validation when `REQUIRE_AUTH=True` and `DEVELOPMENT_MODE=False` with empty `ALLOWED_API_KEYS` at app creation.
- Middleware auth tests expecting FastAPI default `{"detail": "..."}` need updates to standardized `{"error": {...}}`.
- These are being addressed under Phases 8–10 test updates and DI hardening.

Next Actions (Phase 7 closure)
- [ ] Add `tests/providers/test_ollama.py` (mapping + error path). [BLOCKER]
- [ ] Update `.env.example` with `OLLAMA_HOST` docs.
- [ ] Update README with curl examples for `/ollama/v1/chat/completions`.
- [ ] Stabilize `tests/api/test_routes.py` via early monkeypatch and cache handling; assert standardized error payload and `WWW-Authenticate` header. [BLOCKER]
- [ ] Re-run pytest and ensure coverage ≥ 85% with updated assertions.

Blocking Issues
- Settings construction can fail before tests monkeypatch `get_settings`, causing 401 or ValidationError in route tests.
Mitigations:
- In tests, monkeypatch `ai_gateway.config.config.get_settings` before calling `get_app()` and clear cache (`get_settings.cache_clear()` if applicable).
- Under pytest, consider bypassing `lru_cache` or using a pytest-only path in `get_settings` (fallback already added) to ensure predictable behavior during dependency resolution.
