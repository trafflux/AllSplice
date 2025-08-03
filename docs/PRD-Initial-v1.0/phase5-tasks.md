# Phase 5 — Providers: Interface, Custom Provider, and Router Wiring

Status legend: [ ] not started, [~] in progress, [x] done

## 5.1 Provider Interface
- [x] Create base interface using typing.Protocol
- [x] Strict types with Pydantic models from schemas.openai_chat
- [x] Docstrings and mypy-strict friendly signatures
- [~] Tests for typing-level expectations
  - Notes: Protocol defined in src/ai_gateway/providers/base.py and used by providers. A dedicated typing-focused test (e.g., tests/providers/test_base_typing.py) is still missing to assert static expectations and sample conformance. mypy strict remains green. [BLOCKER: None; coverage/quality gap]

## 5.2 CustomProcessingProvider
- [x] Implement deterministic OpenAI-compatible response
- [x] Generate id as `chatcmpl-<uuid>`, `object="chat.completion"`, `created=int(time.time())`
- [x] choices[0] with `finish_reason="stop"`, echo model, safe static content
- [x] usage provided (zeros for now with TODO)
- [x] Minimal structured logging without secrets
- [x] Tests verifying schema, id prefix, object literal, created int, finish_reason, usage, determinism
  - Notes: Provider implemented in src/ai_gateway/providers/custom.py and validated by tests/providers/test_custom.py. No external SDKs/logging integrations yet (deferred to later phases).

## 5.3 Wire provider into /v1/chat/completions
- [x] Update router to use CustomProcessingProvider via simple resolver (TODO DI composition root)
- [x] Keep auth via Depends(auth_bearer)
- [~] Tests: 200 with auth and schema conformance; 401 without; cerebras functional; ollama pending
  - Notes: tests/api/test_routes.py present for v1 path and auth. Cerebras is now implemented (Phase 6) and routed; tests should be updated to assert success path with mock client and standardized error payloads on failures. Ollama wiring exists but requires verification/tests. Settings DI reconstruction during requests remains a fragility causing intermittent validation errors; composition root will address. [BLOCKER: CI flakiness until tests/DI stabilized]

## 5.4 Resolve outstanding diagnostics
- [~] Ensure providers and routes are mypy-clean under strict
  - Notes: mypy strict generally green. Pyright/Pylance may warn on provider imports; ignore in favor of mypy. Re-verify after Phase 6 wiring.
- [x] App import for exceptions.handlers integrated in Phase 8; handlers are registered in app factory.
- [~] Auth middleware strictness cleanup
  - Notes: src/ai_gateway/middleware/auth.py retains conditional logic for ALLOWED_API_KEYS formats and test-time behavior. Needs simplification once DI is centralized. Functionally correct. [BLOCKER: None; CI stability risk due to test fragility]

## 5.5 Logging (minimal)
- [x] Provider logs one structured info line with request meta (no secrets)
  - Notes: Temporary print-based logging helper guarded and marked for replacement by Phase 10 logging module.

## 5.6 Docs / Checklists
- [x] Create this phase5-tasks.md with acceptance criteria and progress
- [x] Update phase4-tasks.md to mark 4.2.1 complete after wiring
  - Notes: Phase 4 file updated to reflect v1 router using CustomProcessingProvider and updated cerebras status.

## 5.7 Tests and Coverage
- [x] Add unit tests for provider and router path
- [~] Run pytest and ensure coverage remains ≥ 85% for business logic
  - Notes: Coverage ~86% on stable runs. Intermittent Settings validation in auth dependency can reduce effective coverage in failing runs. Stabilizing DI and updating tests for standardized error payloads and cerebras wiring will keep reporting consistent. Provider tests are green. [BLOCKER: CI flakiness until DI/test updates]

## Acceptance Criteria
- Provider interface and CustomProcessingProvider implemented with strict typing and docstrings. [Met]
- /v1/chat/completions uses CustomProcessingProvider and remains protected by bearer auth. [Met]
- Responses conform to OpenAI Chat Completions schema fields used to date: id, object, created, model, choices, usage. [Met]
- Cerebras provider exists and router wired; tests to be added in Phase 6. [Partially met]
- Tests green (middleware, schemas, providers, api), coverage ≥ 85%. [Partially met due to DI/test fragility]
- No secret leakage in logs; minimal structured logging present. [Met]

## Remaining Errors and Dependencies
- Errors:
  - tests/api/test_routes.py::test_v1_chat_completions_authorized and ::test_cerebras_and_ollama_are_501 can fail with Settings validation: “ALLOWED_API_KEYS must not be empty when REQUIRE_AUTH=True and DEVELOPMENT_MODE=False”. Root cause: dependency resolution constructs a fresh Settings ignoring monkeypatched values unless ALLOWED_API_KEYS_RAW and DEVELOPMENT_MODE are provided. Mitigation added in tests and auth normalization; still fragile.
  - tests/middleware/test_auth.py token-positive cases failed initially due to ALLOWED_API_KEYS normalization; addressed by auth changes and test env/key setup, verify again after DI improvements.
- Diagnostics:
  - Pylance warnings about unknown provider types in routes; mypy should remain clean for Phase 5 scope.
  - Auth middleware contains conditional paths to accommodate CSV vs list and test-time settings; flagged for refactor.
- Dependencies / Future Phases:
  - Phase 8: Global exception handlers module; firm app registration; normalize error schema.
  - Phase 9/10: Composition root for DI (inject Settings, Providers); centralized logging; this will remove Settings monkeypatch fragility and temporary print logging.
  - Phase 6/7: Additional providers and clients introduce proper request→provider mapping and will benefit from the DI foundation above.
