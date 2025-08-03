# Phase 8 — Exceptions and Global Handlers

Status: In Progress

Objective:
Introduce a standardized exception model and global handlers to normalize error responses across the API, ensure compliance with Project Standards section 8, and improve test stability by making error shapes deterministic.

Scope:
- Custom exception types with strict typing and docstrings.
- Global exception handlers that return a standardized error payload and correct HTTP codes.
- Register handlers in the FastAPI app factory.
- Switch auth dependency to raise AuthError (401) and maintain WWW-Authenticate: Bearer.
- Wrap provider failures into ProviderError (502) in providers (Cerebras/Ollama).
- Tests for handlers and updates to existing tests as needed.

Checklist:
[x] 8.1 Exceptions (src/ai_gateway/exceptions/errors.py)
  - Implemented:
    - AuthError (401)
    - ValidationAppError (422)
    - ProviderError (502)
    - InternalError (500)
  - Fields: message: str, details: dict[str, object] | None = None
  - Docstrings and strict typing.
  - No secrets in messages.

[x] 8.2 Global Handlers (src/ai_gateway/exceptions/handlers.py)
  - register_exception_handlers(app: FastAPI) implemented:
    - AuthError → 401 with standardized payload and header WWW-Authenticate: Bearer
    - ValidationAppError → 422
    - ProviderError → 502
    - InternalError → 500
    - Fallback: generic Exception → 500 InternalError shape; safe message
  - Standardized payload structure:
    {
      "error": {
        "type": "string",
        "message": "string",
        "details": { ... optional ... }
      }
    }

[x] 8.3 Integration
  - api/app.py: register_exception_handlers(app) called in get_app().
  - middleware/auth.py: raises AuthError on failures (Missing/Malformed/Invalid scheme/Empty token/Invalid credentials).
  - providers/ollama.py and providers/cerebras.py: wrap client failures in ProviderError; surfaced via global handlers.

[~] 8.4 Tests
  - TODO: Add tests/exceptions/test_handlers.py to cover:
    - AuthError (401) payload and WWW-Authenticate header. [BLOCKER]
    - ValidationAppError (422), ProviderError (502), InternalError (500), and generic Exception → 500. [BLOCKER]
  - TODO: Update existing middleware auth tests to assert standardized payload:
    - Replace assertions expecting {"detail": "..."} with checks for body["error"]["type"] and ["message"]; assert WWW-Authenticate header. [BLOCKER]
  - TODO: Adjust tests/api/test_routes.py to ensure settings are patched or env set before app creation; patch ai_gateway.config.config.get_settings before calling get_app(). [BLOCKER]

[~] 8.5 Documentation
  - TODO: Update README to document the error payload format and semantics.
  - TODO: Note DI for Settings/Providers to be addressed in Phase 9/10 to reduce config fragility.

Acceptance Criteria:
- Handlers registered: all errors conform to standardized payload. [Partially met; tests pending]
- WWW-Authenticate header is present on 401 responses. [Implemented; tests pending]
- Providers wrap provider errors into ProviderError. [Implemented]
- Tests for exceptions and handlers pass. [Pending]
- Overall test suite passes on CI (or non-related failures explicitly deferred to next phase). [Pending]
- No secret leakage in logged or returned error messages. [Implemented]

Notes:
- Blocking issue: tests/api/test_routes.py::test_cerebras_and_ollama_endpoints returns 401 due to Settings patching vs. cache timing; monkeypatch applies but allowed keys are not observed in dependency path. Proposed mitigation: clear get_settings cache in test before monkeypatch or bypass cache under pytest.
- Settings DI hardening remains a Phase 9/10 task; tests must still patch early to avoid reconstruction issues.

Commands (for local dev):
- pytest -q
- mypy
- ruff check && ruff format

Immediate Next Tasks (to complete Phase 8):
- [ ] Add tests/exceptions/test_handlers.py covering 401/422/502/500 and generic Exception mapping. [BLOCKER]
- [ ] Update tests/middleware/test_auth.py assertions to standardized payload shape:
      expect body["error"]["type"] and ["message"]; also assert WWW-Authenticate header. [BLOCKER]
- [ ] Stabilize tests/api/test_routes.py by monkeypatching ai_gateway.config.config.get_settings before get_app() and ensuring ALLOWED_API_KEYS and DEVELOPMENT_MODE are set appropriately for the test. [BLOCKER]
- [ ] Re-run pytest and mypy; iterate until green.
