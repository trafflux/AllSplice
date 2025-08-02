# Phase 6 — Cerebras Integration

Status legend: [ ] not started, [~] in progress, [x] done

Summary:
Per TASKS-1.0.md, Phase 6 covers a Cerebras client, provider, error normalization, and tests. Current repo status: Cerebras client and provider are implemented (mock mode supported), global handlers integrated, and router wiring exists; however, dedicated tests and docs updates are still pending. This document outlines tasks, current status versus the primary project plan, and next steps aligned with project standards.

Scope (from TASKS-1.0.md):
- Client wrapper
- Provider implementation
- Error handling (normalize to ProviderError 502)
- Tests (mock SDK; mapping; error paths)

Acceptance (aligned to Project Standards v1.0):
- Provider abstraction implemented with strict typing and mypy-clean.
- OpenAI Chat Completions compatible request/response mapping (id, object, created, choices, usage).
- Errors normalized to ProviderError(502) and handled by global handlers (Phase 8).
- Tests green, no real network calls in CI (SDK mocked).
- No secret leakage; timeouts configured.

Tasks and Status

6.1 Client Wrapper — src/ai_gateway/providers/cerebras_client.py
- [x] Initialize with:
  - API key from Settings.CEREBRAS_API_KEY (REQUIRED when provider in use)
  - Optional base URL from Settings.CEREBRAS_BASE_URL (coerced to str)
  - Request timeout from Settings.REQUEST_TIMEOUT_S (float seconds)
- [x] Expose async method:
  - async def chat(self, model: str, messages: list[dict[str, str]], **kwargs) -> dict
- [x] Strict typing and docstrings
- [x] Do not log secrets; redact tokens if ever logged
- [x] CI-safe deterministic mock mode (enabled in CI or dev without API key); real mode currently raises normalized ProviderError until SDK integration is added.

Current: Implemented (mock mode functional; real-mode path intentionally not implemented to keep CI hermetic). Follow-ups: integrate official SDK in a later subtask and map SDK exceptions to ProviderError.

6.2 Provider Implementation — src/ai_gateway/providers/cerebras.py
- [x] class CerebrasProvider(ChatProvider)
  - async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse
- [x] Map OpenAI-style request to Cerebras client shape (role/content normalization)
- [x] Transform client response back to OpenAI-compatible response:
  - id: "chatcmpl-<uuid>"
  - object: "chat.completion"
  - created: int(epoch seconds)
  - choices[0]: assistant message, finish_reason mapped, index=0
  - usage: from provider if available; default zeros
- [x] Strict typing; cohesive helpers; no secret leakage

Current: Implemented and uses CerebrasClient. Errors normalized to ProviderError.

6.3 Error Handling
- [x] Normalize SDK/client errors/timeouts to ProviderError(502)
- [x] Ensure timeouts taken from Settings.REQUEST_TIMEOUT_S via client wrapper
- [x] Return standardized error payload via global handlers (Phase 8 already implemented)

Current: Implemented in client and provider: unexpected exceptions become ProviderError("Upstream provider error"), surfaced via global handlers.

6.4 Tests — tests/providers/test_cerebras.py
- [~] Mock the CerebrasClient to assert request mapping fidelity
- [~] Assert response mapping to OpenAI schema
- [~] Error path test: client exception → ProviderError(502) via handlers
- [x] No real network; CI hermetic

Current: File exists (tests/providers/test_cerebras.py) but needs full assertions and mocking to cover mapping and error-paths. [BLOCKER: CI coverage/confidence until tests implemented]

Integration and Router
- [x] src/ai_gateway/api/routes.py:
  - /cerebras/v1/chat/completions path wired to CerebrasProvider
  - Depends(auth_bearer) enforced
- [x] Global exception handlers in place (Phase 8)
- Notes: Update integration tests to reflect functional cerebras endpoint (not 501). [BLOCKER: tests pending]

Configuration and Constants
- [x] Settings file exists (src/ai_gateway/config/config.py)
  - [~] Verify CEREBRAS_API_KEY required only if Cerebras endpoints are used
  - [x] Optional CEREBRAS_BASE_URL present
  - [x] REQUEST_TIMEOUT_S present with defaults
- [x] Constants in src/ai_gateway/config/constants.py include routing prefixes

Documentation
- [ ] README: Add curl example for /cerebras/v1/chat/completions
- [ ] .env.example: Add CEREBRAS_API_KEY, CEREBRAS_BASE_URL comments and safe defaults
- [ ] docs: Note error normalization and mapping details
- Notes: Document CI-safe mock mode behavior and requirement gating of CEREBRAS_API_KEY only when endpoint used.

Notes added in this pass:
- Client supports deterministic mock mode keyed off CI env or dev without API key.
- Real-mode SDK integration intentionally deferred to avoid network in CI; when added, must preserve ProviderError normalization.

Planned Implementation Notes
- Client wrapper: encapsulate SDK initialization; keep constructor signature minimal and testable. Provide base_url and timeout overrides via constructor parameters for test control; default from Settings.
- Provider: lean mapping methods for request and response to keep cyclomatic complexity low; unit test each mapping step.
- Errors: catch specific SDK exceptions if available (Timeouts, Auth, Network) and convert to ProviderError with a safe message.

Immediate Next Steps (Phase 6)
- [ ] Complete tests/providers/test_cerebras.py with full mapping coverage and error-path; use mock client.
- [ ] Update README and .env.example with Cerebras-specific notes and examples.
- [ ] Update tests/api/test_routes.py to assert cerebras behavior (auth, success, error schema).
- [~] Run pytest and mypy; iterate to green. Also verify standardized error payloads across routes.

Cross-Phase Considerations
- Phase 8 (exceptions/handlers) is complete; leverage for ProviderError handling.
- Phase 9/10 (DI and logging) will improve composition root and structured logging; keep provider/client design DI-friendly now (constructor injection).
- Phase 1/13: ensure Settings/docs list Cerebras variables clearly.

Status Summary
- Client Wrapper: [x]
- Provider: [x]
- Error Handling: [x]
- Tests: [~] (file present; assertions/mocks pending)
- Router Wiring: [x] (functional)
- Config/Docs: [~] (variables present; docs/examples pending)
