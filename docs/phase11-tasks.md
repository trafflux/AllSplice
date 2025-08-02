# Phase 11 — Test Stabilization, DI Hardening, and Coverage

Status: In Progress

Scope
Focus on stabilizing the test harness around settings/auth, consolidating dependency injection (DI) for providers, and closing gaps in Ollama test coverage. Execute mypy and pytest, resolve errors, and bring coverage back to target. Address incomplete items from Phases 7–10 that depend on these changes.

11.1 Dependency Injection (DI) Hardening
Tasks:
- [ ] Introduce provider factory functions in app factory to allow dependency overrides in tests.
- [ ] Centralize composition root: resolve providers via small callables (e.g., get_custom_provider, get_cerebras_provider, get_ollama_provider).
- [ ] Ensure DI does not instantiate settings eagerly within module import; only inside callables.
- [ ] Tests: add tests/api/test_provider_di.py to validate overrides using FastAPI dependency_overrides.

Acceptance:
- [ ] Providers can be swapped in tests without patching internals.
- [ ] No eager settings evaluation on import.

11.2 Settings/Test Harness Stabilization
Tasks:
- [x] Ensure ai_gateway.config.config.get_settings pytest fallback path is in place (already added).
- [ ] Update tests to clear get_settings cache before monkeypatch when required.
- [ ] Option: Under pytest, bypass lru_cache or document cache clearing pattern in fixtures.
- [x] Verify middleware/auth.py imports get_settings symbol from config module (already ensured).
- [x] Add DEVELOPMENT_MODE tolerance in auth for tests when no keys configured (keeps header requirement).

Acceptance:
- [ ] tests/api/test_routes.py stable for 200/401 paths across /v1, /cerebras/v1, /ollama/v1.
- [x] No premature ValidationError from settings during app creation in tests (pytest fallback active).

11.3 Ollama Provider Test Coverage
Tasks:
- [ ] Implement tests/providers/test_ollama.py: success mapping, error mapping (raises ProviderError(502)), timeout behavior if applicable.
- [ ] Mirror structure used in tests/providers/test_cerebras.py.
- [ ] Ensure no real network calls; mock client.

Acceptance:
- [ ] All Ollama tests pass and contribute to coverage target.

11.4 Exceptions and Global Handlers Tests
Tasks:
- [ ] Implement tests/exceptions/test_handlers.py covering 401/422/502/500 and generic Exception mapping to standardized payload.
- [ ] Update tests/middleware/test_auth.py to expect standardized payload and WWW-Authenticate header.

Acceptance:
- [ ] Handlers behave consistently and tests pass.

11.5 App Factory Assertions
Tasks:
- [ ] Implement tests/api/test_app.py to assert routers exist: /v1, /cerebras/v1, /ollama/v1, /healthz.
- [ ] Confirm middleware order: CorrelationId → SecurityHeaders.

Acceptance:
- [ ] App factory wiring verified by tests.

11.6 Documentation and Examples
Tasks:
- [ ] Update README with curl example for /ollama/v1/chat/completions.
- [ ] Update .env.example with OLLAMA_HOST notes.

Acceptance:
- [ ] Documentation reflects current endpoints and configuration.

11.7 Quality Gates
Tasks:
- [ ] Run mypy (strict) and resolve type errors.
- [ ] Run pytest; fix failures.
- [ ] Ensure coverage ≥ 85% for business logic.

Acceptance:
- [ ] CI-quality local run: mypy clean, tests pass, coverage threshold met.

Blockers
- Route tests still return 401 due to cache/patch timing. Required test fixes: clear get_settings.cache before monkeypatch, then build app; ensure order consistently.
- DI refactor should avoid circular imports; prefer local imports inside factories if needed.

Cross-Phase Dependencies to Close
- Phase 7: tests/providers/test_ollama.py; README and .env.example updates; route test stabilization.
- Phase 8: exceptions handler tests; auth tests update.
- Phase 9: foundation for CORS/logging can proceed after DI/settings stabilization from this phase.
- Phase 10: DI composition root aligns with this phase; finalize provider override tests.

Execution Plan
1) Implement DI factory functions and minimal code touches in app factory (if needed).
2) Add/adjust tests: provider DI, handlers, app assertions, Ollama provider.
3) Update README and .env.example.
4) Run mypy/pytest; iterate until clean.
