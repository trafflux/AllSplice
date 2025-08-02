# Feature 04 — Provider Interface Definition

Status: ⚠️ Incomplete

Purpose:
Define the standard provider interface (base protocol) that all backend provider modules must implement to ensure the Core OpenAI Endpoint Layer remains provider-agnostic and easily extensible.

Outcomes:
- A clear, versioned interface contract covering required methods, inputs, and outputs.
- Mapping rules to and from OpenAI-compatible schemas.
- Guidance on error normalization, timeouts, and metadata propagation (e.g., request IDs).

Scope:
- Methods required in v1:
  - list_models()
  - create_embeddings()
  - create_completion() (legacy)
  - create_chat_completion()
- Strict typing aligned to OpenAI schemas for requests and responses.
- Async, non-blocking calls with explicit timeouts.

Tasks:
1. Interface Contract Specification
   - Specify Python Protocol with async methods:
     - `async def list_models(...) -> OpenAIListModelsResponse`
     - `async def create_embeddings(req: OpenAICreateEmbeddingsRequest) -> OpenAICreateEmbeddingsResponse`
     - `async def create_completion(req: OpenAICompletionRequest) -> OpenAICompletionResponse`
     - `async def create_chat_completion(req: OpenAIChatCompletionRequest) -> OpenAIChatCompletionResponse`
   - Inputs/Outputs must be typed using the project’s OpenAI schema models.
   - Status: ⚠️

2. Schema Mapping Rules
   - Define normalization rules:
     - Roles and content normalization.
     - Timestamps: `created` set to epoch seconds.
     - IDs: `id` style `chatcmpl-<ulid/uuid>` for chat; analogous for others.
     - `object` fields set to OpenAI-compatible values (e.g., `chat.completion`).
     - `finish_reason` values mapped to OpenAI enum.
     - `usage` populated from provider data if available; otherwise set conservative defaults or zeros with TODO markers for enhancement.
   - Status: ⚠️

3. Error Normalization
   - Define provider exceptions → unified `ProviderError` (HTTP 502 in handlers).
   - Disallow leaking provider stack traces; log internal details only.
   - Network/timeout errors normalized consistently.
   - Status: ⚠️

4. Context Propagation
   - Require passing a `request_id` (from correlation middleware) to providers where possible.
   - Define explicit timeout handling from config (`REQUEST_TIMEOUT_S`).
   - Status: ⚠️

5. Backwards Compatibility
   - Capture `completions` (legacy) vs `chat.completions` differences and shared fields.
   - Document how streaming is treated in v1 (default non-streaming).
   - Status: ⚠️

6. Provider Implementation Guide Stub
   - Outline steps to add a new provider:
     - Implement interface
     - Bind in app factory via configuration
     - Add provider-specific unit tests and mapping tests
     - Ensure OpenAI schema conformance and error normalization
   - Status: ⚠️

Dependencies:
- Feature 01 — Architecture overview
- Feature 02 — Goals and Objectives
- Feature 03 — Scope
- Features 07–10 — Endpoint behavior dependent on this interface

Acceptance Criteria:
- A versioned interface (v1) with clearly documented method signatures and semantics.
- Explicit mapping rules to OpenAI schemas for each method.
- Error normalization strategy documented; no leakage of provider internals.
- Context propagation (request_id, timeouts) specified.

Test & Coverage Targets:
- Validation via provider unit tests (mocked) and API integration tests.
- Ensure that replacing provider implementations does not require core changes.
- Downstream tests contribute to ≥ 85% coverage.

Review Checklist:
- Do all required OpenAI endpoints have corresponding interface methods?
- Are input/output models strictly typed and aligned with schemas?
- Are error and timeout behaviors unambiguous?
- Can a new provider be swapped in without core changes?
