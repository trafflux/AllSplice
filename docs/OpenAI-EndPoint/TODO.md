# TODO — PRD Alignment for Core OpenAI Endpoint Layer

Status as of: 2025-08-03

This document compares the current implementation to the PRD at docs/OpenAI-EndPoint/PRD-OAI-ENDPOINT.md and enumerates remaining work. Status markers:
- ✅ Complete
- ⚠️ Incomplete
- ❌ Incomplete with blocking
- ‼️ Serious issue

## 1) Alignment Summary

Scope per PRD (v1.0):
- Endpoints:
  - GET /<provider>/v1/models
  - POST /<provider>/v1/embeddings
  - POST /<provider>/v1/chat/completions
  - POST /<provider>/v1/completions (Legacy)

Implementation found in src/ai_gateway/api/routes.py with routers:
- /v1 (CustomProcessingProvider)
- /cerebras/v1 (CerebrasProvider)
- /ollama/v1 (OllamaProvider)
- /healthz (operational, not part of PRD but intentionally added)

Current implemented endpoints:
- /{namespace}/models → ✅ present for v1, cerebras, ollama
- /{namespace}/embeddings → ✅ present for v1, cerebras, ollama
- /{namespace}/chat/completions → ✅ present for v1, cerebras, ollama
- /{namespace}/completions (legacy) → ❌ not implemented by design (out-of-scope decision)
- Streaming variants (via stream=true or SSE) → ❌ not implemented (intentionally out-of-scope for v1.0)

Auth:
- Bearer token enforced across provider routes via Depends(auth_bearer) → ✅
- /healthz unauthenticated → ✅

Schemas:
- Chat Completions request/response → ✅ (src/ai_gateway/schemas/openai_chat.py)
- Embeddings request/response → ✅ (src/ai_gateway/schemas/openai_embeddings.py)
- Models list → ✅ (src/ai_gateway/schemas/openai_models.py)

Provider Abstraction:
- Protocol: ChatProvider with chat_completions, list_models, create_embeddings → ✅ (base.py)
- Concrete providers (deterministic stubs): custom, cerebras, ollama → ✅

Middleware/Errors (per project standards):
- Correlation ID, Security headers, Structured logging → ✅ configured in app factory
- Global exception handlers → ✅

Operational:
- /healthz implemented with optional version/build → ✅

Documentation consistency:
- PRD still lists legacy Completions; project decision is to exclude legacy completions in v1.0 → ⚠️ needs explicit cross-doc note in PRD/Docs index or add a deviation note here (kept below).

Testing:
- Stated coverage ~92% and all tests green, including provider and API tests → ✅
- Consider adding /healthz integration test (if not present) → ⚠️ verify/ensure explicit tests cover metadata keys behavior.

## 2) Out-of-Scope Decisions (Authoritative)

- POST /<provider>/v1/completions (Legacy) → Out-of-scope for v1.0 (documented in OAI-LOG.md).
- Streaming responses (for chat/completions and legacy) → Out-of-scope for v1.0.

Actions: Ensure PRD-compat docs reflect these decisions with a clear deviation note and rationale.

## 3) Gaps and Missing Items

1) PRD vs Implementation — Legacy Completions
- Status: ❌ Intentionally not implemented.
- Action: Add explicit Deviation section in PRD or an addendum linking to OAI-LOG.md scope decision. Update any endpoint matrices to mark legacy as out-of-scope (v1.0) with rationale.

2) Streaming behavior in PRD language
- Status: ❌ Not implemented.
- Action: Add explicit “non-streaming only in v1.0” note in endpoints docs (07, 08, 10 docs) and README examples. Ensure tests do not imply streaming; add negative tests if necessary.

3) Documentation completeness for /healthz
- Status: ⚠️ Implemented, not part of PRD.
- Action: Add concise operational doc and examples in README and docs/OpenAI-EndPoint/12-Documentation-and-Readiness.md. Note: unauthenticated, includes optional version/build.

4) Provider docs alignment (Ollama/Cerebras mapping)
- Status: ⚠️ Should confirm per-provider mapping pages fully align with current request/response models and DI.
- Action: Review and adjust docs where necessary (not code).

5) Tests: explicit assertions for auth guards across all provider routes
- Status: ⚠️ Likely present but verify coverage includes 401 path and WWW-Authenticate header.
- Action: Add/confirm tests for unauthorized access to all three endpoints across all three namespaces.

6) Error normalization documentation
- Status: ⚠️ Implemented in code; ensure docs mention standardized error payloads and status mapping for provider/network errors (502).
- Action: Update docs pages to include example error payloads and how exceptions map to HTTP status codes.

## 4) Feature Breakdown into Tasks

Feature 01 — PRD Deviation and Scope Clarification
- Task 01.1: Add “Scope Deviations for v1.0” section to PRD-OAI-ENDPOINT.md referencing OAI-LOG.md decisions. Status: ⚠️
- Task 01.2: Update docs/OpenAI-EndPoint/03-Scope.md to explicitly list legacy Completions and Streaming as out-of-scope with rationale. Status: ⚠️
- Task 01.3: Update endpoint matrix pages (07, 08, 10) to mark non-streaming only for v1.0. Status: ⚠️

Feature 02 — Health Endpoint Documentation
- Task 02.1: Add /healthz documentation in docs/OpenAI-EndPoint/12-Documentation-and-Readiness.md with sample response including optional version/build. Status: ⚠️
- Task 02.2: Add curl example for /healthz to README.md and examples section. Status: ⚠️

Feature 03 — Auth and Error Behavior Documentation
- Task 03.1: Update docs/OpenAI-EndPoint/06-Authentication-and-Headers-Handling.md to confirm Bearer token header is required for all provider routes and unauthenticated for /healthz. Status: ⚠️
- Task 03.2: Document standardized error payload format and handlers in a subsection of 12-Documentation-and-Readiness.md (or a new page) with examples (401/422/502). Status: ⚠️

Feature 04 — Testing Enhancements
- Task 04.1: Ensure explicit tests exist for /healthz (200, payload keys presence/absence). Status: ⚠️
- Task 04.2: Verify tests cover unauthorized access (401 + WWW-Authenticate) for models, embeddings, chat across all namespaces. Add missing tests. Status: ⚠️
- Task 04.3: Add negative tests for streaming params (if present in requests) to ensure non-streaming behavior is clear or validation errors are handled as expected. Status: ⚠️
- Task 04.4: Maintain coverage ≥ 85% post-changes. Status: ⚠️

Feature 05 — Documentation Consistency and Examples
- Task 05.1: Review and update per-provider docs (docs/Ollama-Provider/*) to ensure they match the current non-streaming, non-legacy scope for v1.0. Status: ⚠️
- Task 05.2: Add curl examples for GET /models, POST /embeddings, POST /chat/completions for /v1, /cerebras/v1, /ollama/v1 in README.md. Status: ⚠️

## 5) Detailed Task List (Actionable)

- [ ] 01.1 PRD addendum: Scope Deviations (legacy completions excluded; streaming excluded) → ⚠️
- [ ] 01.2 Update 03-Scope.md to reflect deviations and rationale → ⚠️
- [ ] 01.3 Update endpoint docs 07, 08, 10 with “non-streaming in v1.0” notes → ⚠️
- [ ] 02.1 Add /healthz section to 12-Documentation-and-Readiness.md → ⚠️
- [ ] 02.2 README: curl example for /healthz and quickstart note → ⚠️
- [ ] 03.1 Update 06-Authentication-and-Headers-Handling.md for provider routes vs /healthz → ⚠️
- [ ] 03.2 Document standardized error payloads and mapping (401/422/502/500) with examples → ⚠️
- [ ] 04.1 Add/verify /healthz tests: status and optional metadata keys → ⚠️
- [ ] 04.2 Add/verify unauthorized tests for each endpoint across all namespaces → ⚠️
- [ ] 04.3 Add negative tests/clarifications regarding streaming params → ⚠️
- [ ] 04.4 Ensure coverage threshold remains ≥ 85% after changes → ⚠️
- [ ] 05.1 Align Ollama/Cerebras docs pages with v1.0 scope (non-streaming, no legacy completions) → ⚠️
- [ ] 05.2 README curl examples for models/embeddings/chat for all namespaces → ⚠️

## 6) Notes and Rationale

- Legacy Completions endpoint is explicitly excluded from v1.0 implementation per project decision captured in OAI-LOG.md. This deviates from the PRD which lists it in-scope; we retain the decision and document it.
- Streaming responses are excluded for v1.0 to keep complexity down and maintain deterministic tests; can be revisited in a subsequent version if needed.
- /healthz is an operational endpoint added for readiness and observability; while not in PRD scope, it is a best-practice addition and will be documented succinctly.

## 7) Status Summary

- Core endpoints (models, embeddings, chat) implemented for v1, cerebras, ollama: ✅
- Auth + DI present and tested: ✅
- Health endpoint implemented: ✅ (docs pending)
- Legacy Completions: ❌ (intentionally out-of-scope)
- Streaming: ❌ (intentionally out-of-scope)
- Documentation/test deltas: ⚠️ (see tasks above)
