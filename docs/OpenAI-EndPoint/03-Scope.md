# Feature 03 — Scope

Status: ⚠️ Incomplete

Purpose:
Define the explicit scope and out-of-scope items for the Core OpenAI Endpoint Layer to align all contributors and ensure focused delivery for v1.

Outcomes:
- Clear statement of what is included in v1 vs. deferred.
- Boundary conditions for responsibilities across routing, validation, provider interface, and error handling.
- Explicit exclusions to prevent scope creep.

In-Scope (v1):
- Routing mechanism using `/{provider}/v1/...` segment to dispatch to provider modules.
- OpenAI-compatible endpoints:
  - GET `/{provider}/v1/models`
  - POST `/{provider}/v1/embeddings`
  - POST `/{provider}/v1/completions` (legacy)
  - POST `/{provider}/v1/chat/completions`
- Definition of a standard provider interface/base class for provider modules.
- Parsing, validation, and shaping of requests/responses to OpenAI schemas.
- Standard HTTP methods, headers, and response codes per OpenAI spec.
- Bearer token authentication handling (using existing auth middleware) across all endpoints.

Out-of-Scope (v1):
- Implementations of any concrete provider module (handled by separate project/features).
- GUI for configuration/management.
- New auth mechanisms beyond bearer token already in place.
- Rate-limiting (candidate for future version).
- Streaming responses (unless explicitly added by later features; default non-streaming).
- Additional OpenAI endpoints beyond the four listed.

Tasks:
1. Scope Declaration
   - Write a concise scope statement mirroring the PRD.
   - Add explicit limitations (no provider-specific logic in core).
   - Status: ⚠️

2. Endpoint Matrix
   - Produce a matrix mapping endpoint → request schema → response schema → HTTP codes.
   - Include legacy note for `completions` vs. chat completions.
   - Status: ⚠️

3. Non-Goals
   - Document out-of-scope topics and rationale.
   - Provide references to where/when they may be addressed (future features/releases).
   - Status: ⚠️

4. Cross-Cutting Concerns
   - Clarify responsibility split for auth, middleware, error handlers, and logging within the core.
   - Status: ⚠️

Dependencies:
- Feature 01 — Architecture overview.
- Feature 02 — Goals and Objectives.
- Feature 04 — Provider interface (referenced but defined there).
- Features 07–10 — Endpoint-specific details.

Acceptance Criteria:
- A finalized scope document is present with in-scope and out-of-scope tables/sections.
- Endpoint matrix lists schemas and expected HTTP codes.
- Non-goals clearly stated to prevent scope creep in v1.

Test & Coverage Targets:
- N/A for documentation-only. Enforced indirectly via endpoint and provider tests that assert behavior consistent with scope.

Review Checklist:
- Does the scope prevent provider-specific logic from leaking into the core?
- Are unsupported endpoints and features clearly marked out-of-scope?
- Is the legacy `completions` endpoint captured distinctly from chat completions?
