# CURRENT-PLAN.md - Universal AI Gateway v1.0

## Current Status (Updated: 2025-08-02)

✅ **Phase 10 - Authentication and Provider DI Tests**
- Fixed auth middleware to properly enforce authentication when REQUIRE_AUTH=True
- Fixed test_v1_chat_completions_unauthorized to set REQUIRE_AUTH=True
- All tests now passing with 90% coverage
- Provider DI tests implemented and working correctly

✅ **Optional Enhancement A: Introduce Depends-based provider injection**
- Added provider factory functions (get_custom_provider, get_cerebras_provider, get_ollama_provider)
- Updated route handlers to use dependency injection with Depends()
- Updated tests to use app.dependency_overrides instead of monkeypatching
- All tests passing, coverage improved to 90%

## Next Unblocked Tasks

Based on the current repo status (tests green, coverage ~89%, mypy strict clean) and the project standards, I will implement the following unblocked enhancements in this order to maximize quality with minimal risk:

### 1) Optional Enhancement A: Introduce Depends-based provider injection
**Goal:** Replace direct instantiation of providers in ai_gateway.api.routes with FastAPI dependency factories. This enables idiomatic test overrides via app.dependency_overrides instead of monkeypatching module symbols.

**Changes:**
- Add provider factories:
  - get_custom_provider() -> CustomProcessingProvider
  - get_cerebras_provider() -> CerebrasProvider
  - get_ollama_provider() -> OllamaProvider
- Update route handlers to accept providers via Depends.
- Keep try/except ProviderError passthrough logic intact (global handlers normalize 502).
- Type hints and docstrings per standards.

**Test updates:**
- Update tests/api/test_provider_di.py to use app.dependency_overrides for both success and error override scenarios with FakeSuccessProvider and FakeErrorProvider.
- Keep existing success/error assertions (model sentinel and 502 normalization).
- Ensure auth tests remain unaffected.

**Acceptance:**
- pytest passes, coverage stays >= current.
- mypy strict clean.
- README remains valid (no API change).

### 2) Enhancement B: Client wrapper timeout and error path tests
**Goal:** Increase coverage on providers/cerebras_client.py and providers/ollama_client.py to assert timeout propagation and ProviderError normalization.

**Changes:**
- Add unit tests in tests/providers/ to mock underlying client/SDK:
  - Simulate timeout and generic exception paths; assert ProviderError with sanitized message and no stack leakage.
  - Assert REQUEST_TIMEOUT_S pulled from config is applied (e.g., verify passed to client init or request call).
- Strictly hermetic (no network).

**Acceptance:**
- Coverage improves on the client wrappers.
- Existing provider tests remain green.

### 3) Documentation pass
**Goal:** Ensure documentation parity and clarity per standards.

**Changes:**
- README: Verify and, if missing, add curl examples for:
  - /v1/chat/completions
  - /cerebras/v1/chat/completions
  - /ollama/v1/chat/completions
  Include Authorization header examples and development-mode note.
- .env.example: Verify all required variables are present with comments:
  SERVICE_HOST, SERVICE_PORT, LOG_LEVEL, ALLOWED_API_KEYS, CEREBRAS_API_KEY, CEREBRAS_BASE_URL (optional), OLLAMA_HOST, REQUEST_TIMEOUT_S, ENABLE_SECURITY_HEADERS.

**Acceptance:**
- Docs reflect actual behavior and config surface.

## Execution approach

1. Implement DI factories and route changes in a minimal, type-safe way.
2. Update tests incrementally: first adapt provider DI tests using dependency_overrides; then run pytest to confirm no regressions.
3. Add client wrapper tests; run pytest; fix any missed imports/typing.
4. Update README and .env.example to ensure parity.
5. Update docs/TODO.md to log each task's status.

## Outstanding Tasks from PRD-TASKS-1.0.md

Based on the PRD-TASKS-1.0.md file, the following tasks remain to be completed:

### Phase 0 - Repo Scaffolding and CI/CD
- [ ] 0.2 Add pyproject.toml with dependencies (partial - move pytest/mypy configs to pyproject.toml)
- [ ] 0.3 Configure tooling (partial - all tool configs must be in pyproject.toml)
- [ ] 0.4 CI workflow (partial - needs coverage threshold enforcement)
- [ ] 0.5 Makefile (partial - verify all targets match standards)

### Phase 1 - Configuration and Constants
- [ ] 1.1 Centralized configuration (partial - verify REQUEST_TIMEOUT_S and ENABLE_SECURITY_HEADERS)
- [ ] 1.2 Constants (partial - confirm all required constants exist)
- [ ] 1.3 Tests (partial - ensure coverage includes all fields)

### Phase 2 - OpenAI Chat Completions Schemas
- [ ] 2.1 Request/Response Models (partial - confirm models forbid extra by default)
- [ ] 2.2 Tests (partial - ensure test coverage includes extra fields rejection)

### Phase 3 - Authentication Dependency
- [x] 3.1 Bearer token auth (completed)
- [ ] 3.2 Wiring dependency into routers with Depends
- [ ] 3.3 Tests (partial - need comprehensive auth tests)

### Phase 4 - App Factory, Routers, Provider Abstraction
- [ ] 4.1 Provider interface (partial - needs implementation)
- [ ] 4.2 Routers (partial - needs implementation)
- [ ] 4.3 App factory (partial - needs implementation)
- [ ] 4.4 Tests (partial - needs implementation)

### Phase 5 - Custom Processing Provider
- [ ] 5.1 Implementation (partial - needs implementation)
- [ ] 5.2 Tests (partial - needs implementation)

### Phase 6 - Cerebras Integration
- [ ] 6.1 Client wrapper (partial - needs implementation)
- [ ] 6.2 Provider implementation (partial - needs implementation)
- [ ] 6.3 Error handling (partial - needs implementation)
- [ ] 6.4 Tests (partial - needs implementation)

### Phase 7 - Ollama Integration
- [ ] 7.1 Client wrapper (partial - needs implementation)
- [ ] 7.2 Provider implementation (partial - needs implementation)
- [ ] 7.3 Error handling (partial - needs implementation)
- [ ] 7.4 Tests (partial - needs implementation)

### Phase 8 - Exceptions and Global Handlers
- [ ] 8.1 Custom exceptions (partial - needs implementation)
- [ ] 8.2 Global handlers (partial - needs implementation)
- [ ] 8.3 Tests (partial - needs implementation)

### Phase 9 - Middleware: Security and Correlation
- [ ] 9.1 Correlation ID (partial - needs implementation)
- [ ] 9.2 Security headers (partial - needs implementation)
- [ ] 9.3 Tests (partial - needs implementation)

### Phase 10 - Logging
- [ ] 10.1 Setup (partial - needs implementation)
- [ ] 10.2 Integration (partial - needs implementation)
- [ ] 10.3 Tests (partial - needs implementation)

### Phase 11 - API Integration Tests and Coverage
- [ ] 11.1 Integration tests with httpx AsyncClient (partial - needs implementation)
- [ ] 11.2 Coverage enforcement (partial - needs implementation)

### Phase 12 - Run and Containerization
- [ ] 12.1 Local run (partial - needs verification)
- [ ] 12.2 Docker (partial - needs implementation)
- [ ] 12.3 Smoke test (partial - needs implementation)

### Phase 13 - Documentation and Examples
- [ ] 13.1 README.md (partial - needs curl examples)
- [ ] 13.2 .env.example (partial - needs all required variables)
- [ ] 13.3 Examples (partial - needs implementation)

### Phase 14 - Release Checklist
- [ ] CI green; mypy/ruff clean; coverage met
- [ ] Tag v1.0.0; update CHANGELOG.md
- [ ] Confirm in-scope endpoints only; streaming and other OpenAI endpoints out-of-scope
