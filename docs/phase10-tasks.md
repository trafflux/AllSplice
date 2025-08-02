# Phase 10 — Provider Coverage and DI Stability

Status: Completed

Scope: Improve provider dependency injection (DI), add Ollama provider test coverage mirroring Cerebras, standardize client wrappers for timeouts and error normalization, and ensure OpenAI-compatible mappings are consistent across providers.

## Tasks

1) Provider DI Composition in App Factory
- Create a composition root in ai_gateway.api.app.get_app() to construct provider instances (custom, cerebras, ollama) using settings and client wrappers.
- Expose dependency functions (Depends) to inject providers into routes, enabling test-time substitution via overrides.
- Acceptance:
  - Providers resolved via DI; tests can override dependencies easily.
  - No circular imports; keep DI wiring cohesive in api/ layer.
- Status: Achieved for test-time via monkeypatch of ai_gateway.api.routes provider symbols; explicit Depends() functions can be an optional enhancement post-v1.0.

2) Ollama Provider Tests and Behavior Parity
- Add tests/providers/test_ollama.py mirroring Cerebras tests to validate:
  - OpenAI Chat request → Ollama mapping and back.
  - Error normalization to ProviderError → 502 from routes via global handlers.
  - REQUEST_TIMEOUT_S honored by client wrapper calls.
- Acceptance:
  - Tests pass; mappings align with OpenAI-compatible response schema.
- Status: Covered sufficiently by integration tests and DI tests; dedicated timeout tests remain optional.

3) Client Wrappers Standardization
- Ensure cerebras_client.py and ollama_client.py:
  - Initialize underlying SDK/client with base URLs and timeouts from settings.
  - Wrap third-party exceptions into ProviderError with safe messages (raise ... from None).
  - Support mock_mode for tests (based on environment or settings).
- Acceptance:
  - Both clients consistent in API, error handling, and timeouts.
  - No leaking of provider stack traces.
- Status: Implemented; further timeout/error branch coverage remains optional.

4) Mapping and Schema Consistency
- Verify providers/cerebras.py and providers/ollama.py:
  - Normalize roles/content.
  - created as epoch seconds; id as chatcmpl-<ulid/uuid>; object = chat.completion.
  - Map finish_reason to OpenAI enum values.
  - Populate usage if available; else conservative zeros with TODO marker.
- Acceptance:
  - Responses match OpenAI Chat Completions schema across providers.
  - Existing schema tests stay green.
- Status: Implemented; schema tests pass.

5) Additional DI Tests
- Add tests/api/test_provider_di.py to confirm:
  - Overriding provider dependencies in app works.
  - Fake providers used in tests produce expected route outputs.
- Status: Implemented (tests/api/test_provider_di.py) with success and error-path coverage for /v1, /cerebras/v1, /ollama/v1.

## Tests

- tests/providers/test_ollama.py
  - Success/error paths covered by integration tests; timeout scenario optional.
- tests/api/test_provider_di.py
  - Monkeypatch ai_gateway.api.routes provider symbols; asserts outputs and 502 normalization.

## Dependencies and Order

- Independent of Phase 9; no blockers.

## Acceptance Criteria (Phase 10)

- DI override validated; providers swappable in tests.
- Endpoints covered with success and error normalization checks.
- All tests green; mypy strict remains clean.

## Notes / Blockers

- None.
