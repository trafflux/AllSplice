# Feature 10 — Endpoint: POST /{provider}/v1/chat/completions

Status: ⚠️ Incomplete

Purpose:
Define transport, validation, provider dispatch, and response shaping for the OpenAI-compatible Chat Completions endpoint. This is the primary, modern endpoint and must strictly adhere to OpenAI Chat Completions schema.

Outcomes:
- Deterministic route for chat-based generation across providers.
- Provider-agnostic dispatch to `create_chat_completion()`.
- OpenAI ChatCompletion response compliance, including messages array and optional parameters.

Scope:
- Transport only: Parse `{provider}` from path, validate body against OpenAI ChatCompletion request schema (messages, model, and optional params), resolve provider, call `create_chat_completion()`, return OpenAI schema response.
- No provider-specific branching or knowledge in the route.
- Errors normalized via global handlers.
- Non-streaming behavior for v1 unless explicitly added later.

OpenAI Behavior Requirements:
- Path: `POST /{provider}/v1/chat/completions`
- Request body conforms to ChatCompletion request schema:
  - Required: `model`, `messages: [{role, content, ...}]`
  - Optional: `temperature`, `top_p`, `n`, `max_tokens`, `presence_penalty`, `frequency_penalty`, `stop`, `user`, `logit_bias`, `response_format`, `seed`, `stream` (non-streaming default for v1).
- 200 OK with payload conforming to ChatCompletion response schema:
  - `id`, `object: "chat.completion"`, `created`, `model`, `choices[*].message{role, content}`, `choices[*].finish_reason`, `usage`
- Standard error codes:
  - 401 Unauthorized
  - 404 Not Found (unknown provider)
  - 422 Unprocessable Entity (validation)
  - 502 Bad Gateway (provider failure via normalization)

Tasks:
1. Route Declaration
   - Document FastAPI route signature: `POST /{provider}/v1/chat/completions`.
   - Require bearer auth.
   - Status: ⚠️

2. Request Validation
   - Validate messages array: roles in allowed set (system, user, assistant, tool), content normalization.
   - Enforce Pydantic model forbidding extra fields.
   - Acknowledge optional parameters, defaulting behavior per spec (non-streaming v1).
   - Status: ⚠️

3. Provider Resolution
   - Resolve `{provider}` to implementation via DI/registry.
   - Unknown provider → 404 standardized error payload.
   - Status: ⚠️

4. Invoke Provider
   - Call `await provider.create_chat_completion(req)`.
   - Pass `request_id` and timeout context where applicable.
   - Streaming behavior:
     - v1 default is non-streaming. If `stream=true`, return 404/405/400 per project decision and document explicitly.
   - Status: ⚠️

5. Response Mapping
   - Ensure response matches OpenAI ChatCompletion schema:
     - `id` format `chatcmpl-<ulid/uuid>`
     - `object: "chat.completion"`
     - `created` epoch seconds
     - `choices[*].message.role` in allowed set; `choices[*].message.content` string (or appropriate structure per schema version in use)
     - `choices[*].finish_reason` mapped to OpenAI enum
     - `usage` present (if provider missing, set conservative defaults or zeros)
   - Status: ⚠️

6. Error Handling
   - Provider/network/timeout errors → `ProviderError` → 502 via handler.
   - Validation failures → 422 via global handler.
   - Auth failures → 401 with `WWW-Authenticate: Bearer`.
   - Status: ⚠️

7. Observability
   - Log `request_id`, `provider`, route, status_code, duration_ms.
   - Avoid logging message content; log counts/tokens if needed without PII.
   - Status: ⚠️

Dependencies:
- Feature 05 — Routing and Namespace Resolution.
- Feature 04 — Provider Interface Definition (`create_chat_completion()`).
- Feature 06 — Authentication and Headers Handling.
- Global exception handlers and structured logging middleware.

Acceptance Criteria:
- Documented route and behavior satisfy OpenAI Chat Completions API.
- Unknown provider returns standardized 404 error.
- Successful responses strictly match OpenAI response schema; errors normalized.
- Streaming stance documented for v1.

Test & Coverage Targets:
- Integration tests:
  - Success with mock provider returns correct OpenAI chat response.
  - Unknown provider → 404 standardized error.
  - Unauthorized → 401 with `WWW-Authenticate: Bearer`.
  - Validation errors (malformed messages) → 422 standardized payload.
  - If `stream=true` supplied, behavior matches documented decision.
- Logs include required fields; message content not logged.

Review Checklist:
- No provider-specific branching in transport layer.
- Response strictly matches OpenAI chat completion schema.
- Privacy-aware logging and consistent error semantics.
