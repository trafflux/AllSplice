# TODO — Consolidated Outstanding Tasks (Phases 1–10)

This file aggregates pending items from the phase plans and task documents, normalized to the current codebase.

## Phase 7 — Ollama Integration

Status: In Progress

Outstanding:
- [x] Implement tests/providers/test_ollama.py (mapping success + error path raising ProviderError(502), and timeout scenario).
- [x] Update `.env.example` with `OLLAMA_HOST` documentation (optional, used for Ollama endpoint).
- [x] Update README with curl examples for `/ollama/v1/chat/completions`.
- [ ] Stabilize `tests/api/test_routes.py` for `/ollama/v1/chat/completions`:
  - Monkeypatch `ai_gateway.config.config.get_settings` before `get_app()`
  - Clear cache if applicable (`get_settings.cache_clear()`)
  - Assert standardized `{"error": {...}}` payload and `WWW-Authenticate` on 401.
- [ ] Re-run pytest and ensure coverage ≥ 85% with updated assertions.

Blocking:
- Settings construction and cache timing can preempt test monkeypatch, causing 401/ValidationError in route tests.

Mitigations:
- In tests, monkeypatch `get_settings` before creating the app and clear cache.
- Under pytest, consider bypassing `lru_cache` or rely on the pytest-only fallback path in `get_settings`.

## Phase 7 — App Factory and Routing

Status: In Progress

Outstanding:
- [x] Add tests/api/test_app.py to assert routers exist: /v1, /cerebras/v1, /ollama/v1, and /healthz.
- [ ] Ensure app factory does not eagerly construct Settings. Guard ENABLE_SECURITY_HEADERS access (already done).
- [x] Confirm correlation/security middleware ordering matches standards (CorrelationId → SecurityHeaders).

Next steps (logged):
- [ ] Validate via targeted test that get_app() does not construct Settings eagerly (simulate missing env and assert no ValidationError during app creation).

Blocking:
- None.

## Phase 8 — Exceptions and Global Handlers

Status: In Progress

Outstanding:
- [x] Add tests/exceptions/test_handlers.py covering 401/422/502/500 and generic Exception mapping.
- [x] Update tests/middleware/test_auth.py assertions to standardized payload and WWW-Authenticate header.
- [ ] Stabilize tests/api/test_routes.py by monkeypatching ai_gateway.config.config.get_settings before get_app(); ensure ALLOWED_API_KEYS and DEVELOPMENT_MODE set appropriately.

Blocking:
- Route test returns 401 due to settings monkeypatch/cache timing. Proposed: clear get_settings.cache in test prior to patch or bypass lru_cache under pytest.

## Phase 9 — Middleware & Security Hardening

Status: Partially Complete

Outstanding:
- [x] CORS (restricted) implementation and tests (disabled by default; allowlist behavior).
- [ ] Structured logging scaffolding with redaction and request_id propagation; tests/logging/test_structured_logging.py.
- [ ] Expand correlation/security headers tests if coverage gaps remain.

Status notes:
- Correlation ID and Security Headers implemented and tested.
- CORS implemented in app factory, gated by settings (ENABLE_CORS, CORS_ALLOWED_ORIGINS, etc.). Added tests in tests/middleware/test_cors.py for disabled/enabled behavior and preflight.

Blocking:
- None specific to CORS. Structured logging pending.

Next steps (logged):
- [ ] Introduce structured logging setup with redaction of known secret keys and request_id propagation; add smoke tests in tests/logging/.

## Phase 10 — Provider Coverage and DI Stability

Status: Partially Complete

Outstanding:
- [ ] Consolidate DI in app factory with dependency functions to inject providers; add overrides in tests.
- [ ] Implement tests/providers/test_ollama.py mirroring Cerebras coverage (success/error/timeout).
- [ ] Verify client wrappers standardization (timeouts, base URLs, error normalization); add tests.
- [ ] Add tests/api/test_provider_di.py for overrides and fake providers.

Status notes:
- Route tests stability improved by changing app/auth to import config module and reference get_settings dynamically (supports pytest monkeypatch). Further hardening requires completing Phase 8 exception tests.

Blocking:
- API route tests depend on Phase 8 stabilization of auth/settings in test harness.

## Cross-Cutting

- [ ] Keep docs/phase3-tasks.md, docs/phase6-tasks.md, docs/phase8-tasks.md, docs/phase9-tasks.md, docs/phase10-tasks.md aligned with current implementation details.
- [ ] Confirm no secrets appear in logs across providers and middleware; redact if necessary.

## Progress Update (this iteration)

Completed:
- [x] Implemented CORS settings in src/ai_gateway/config/config.py:
  - ENABLE_CORS, CORS_ALLOWED_ORIGINS, CORS_ALLOWED_HEADERS, CORS_ALLOWED_METHODS, CORS_ALLOW_CREDENTIALS
- [x] Wired CORS in app factory (src/ai_gateway/api/app.py) after Correlation and SecurityHeaders; default disabled; allowlist-driven.
- [x] Adjusted app factory to import config module dynamically to honor pytest monkeypatching.
- [x] Updated auth dependency to import config module and call get_settings dynamically, stabilizing authorization in tests.
- [x] Added tests/middleware/test_cors.py:
  - Disabled: no CORS headers
  - Enabled: matching origin allowed; non-allowed blocked
  - Preflight OPTIONS handled
- [x] Majority of suite now green post-changes.

Remaining Unblocked Tasks:
- [ ] Phase 7/10: Stabilize routes tests (tests/api/test_routes.py) for `/ollama/v1/chat/completions` with proper get_settings monkeypatch + cache_clear and standardized error assertions.
- [ ] Phase 9: Implement structured logging module with redaction and request_id propagation, and add tests/logging/test_structured_logging.py.
- [ ] Phase 10: Add DI/provider override tests (tests/api/test_provider_di.py).
- [ ] Re-run pytest to ensure coverage ≥ 85% and adjust tests if needed.

Notes:
- Two tests were failing during intermediate iterations due to app factory reading settings at creation; final code avoids eager settings for SecurityHeaders and gates CORS reading. If any flakiness persists locally, ensure get_settings cache is cleared before patching in tests, as documented.
- New follow-ups from static analysis:
  - src/ai_gateway/middleware/security_headers.py: add missing type annotations for function parameters (mypy complaint on line ~20).
  - Ensure provider timeout normalization paths are covered by integration tests (API layer) to verify 502 mapping via global handlers.
