# Phase 10 — Provider Coverage and DI Stability

Status: Partially Complete

Scope: Improve provider dependency injection (DI), add Ollama provider test coverage mirroring Cerebras, standardize client wrappers for timeouts and error normalization, and ensure OpenAI-compatible mappings are consistent across providers.

## Tasks

1) Provider DI Composition in App Factory
- Create a composition root in ai_gateway.api.app.get_app() to construct provider instances (custom, cerebras, ollama) using settings and client wrappers.
- Expose dependency functions (Depends) to inject providers into routes, enabling test-time substitution via overrides.
- Acceptance:
  - Providers resolved via DI; tests can override dependencies easily.
  - No circular imports; keep DI wiring cohesive in api/ layer.
- Status: Partially implemented. Providers exist; DI wiring and explicit dependency override functions still needed.

2) Ollama Provider Tests and Behavior Parity
- Add tests/providers/test_ollama.py mirroring Cerebras tests to validate:
  - OpenAI Chat request → Ollama mapping and back.
  - Error normalization to ProviderError → 502 from routes via global handlers.
  - REQUEST_TIMEOUT_S honored by client wrapper calls.
- Acceptance:
  - Tests pass; mappings align with OpenAI-compatible response schema.
- Status: Not started. Tracked in TODO.

3) Client Wrappers Standardization
- Ensure cerebras_client.py and ollama_client.py:
  - Initialize underlying SDK/client with base URLs and timeouts from settings.
  - Wrap third-party exceptions into ProviderError with safe messages (raise ... from None).
  - Support mock_mode for tests (based on environment or settings).
- Acceptance:
  - Both clients consistent in API, error handling, and timeouts.
  - No leaking of provider stack traces.
- Status: Implemented in outline; requires verification and dedicated tests to confirm timeouts and error normalization.

4) Mapping and Schema Consistency
- Verify providers/cerebras.py and providers/ollama.py:
  - Normalize roles/content.
  - created as epoch seconds; id as chatcmpl-<ulid/uuid>; object = chat.completion.
  - Map finish_reason to OpenAI enum values.
  - Populate usage if available; else conservative zeros with TODO marker.
- Acceptance:
  - Responses match OpenAI Chat Completions schema across providers.
  - Existing schema tests stay green.
- Status: Partially implemented; schema model tests pass but provider-level coverage is incomplete.

5) Additional DI Tests
- Add tests/api/test_provider_di.py to confirm:
  - Overriding provider dependencies in app works.
  - Fake providers used in tests produce expected route outputs.
- Status: Not started. Tracked in TODO.

## Tests

- tests/providers/test_ollama.py
  - Success path returns 200 with schema-compliant payload.
  - Provider failure normalized to 502 standardized error payload.
  - Timeout path uses REQUEST_TIMEOUT_S.
- tests/api/test_provider_di.py
  - Override dependencies and ensure endpoints respond using the fake provider.
- Re-run existing tests to ensure no regressions in Cerebras and default provider behavior.

## Dependencies and Order

- DI wiring should follow Phase 9 middleware updates but is otherwise independent.
- Client wrapper standardization pre-requisite for Ollama parity tests.

## Acceptance Criteria (Phase 10)

- DI implemented; providers easily swappable in tests.
- Ollama provider tests cover success/error/timeout; pass consistently.
- Client wrappers standardized, robust, and type-checked.
- All tests green; mypy strict remains clean.

## Notes / Blockers

- Real external SDKs must remain mocked; ensure no network calls in CI.
- Blocking: API route tests currently returning 401 due to settings monkeypatch/cache behavior. Mitigations in place (pytest fallback in get_settings; DEVELOPMENT_MODE tolerance in auth for tests) but tests still need cache_clear+order fixes. Phase 10 tasks depend on stable auth config in the test harness. Tracked in TODO.
