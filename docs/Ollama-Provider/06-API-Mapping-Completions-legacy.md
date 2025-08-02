# Feature 06 — API Mapping: Completions (POST /{provider}/v1/completions → POST /api/generate)

Status: ⚠️ Incomplete

Purpose:
Specify the Ollama provider mapping for legacy text completions. Translate the core call `create_completion(req)` into Ollama’s `POST /api/generate` and transform the response into the OpenAI Completion response schema, aligning with the Core OpenAI Endpoint Layer’s transport and schema constraints.

Core Integration Reference:
- Core route: `POST /{provider}/v1/completions` (Core Feature 09).
- Provider interface method: `async def create_completion(req) -> OpenAICompletionResponse` (Core Feature 04).
- Core handles bearer auth, request validation, routing, and error normalization. Provider focuses on request/response mapping, timeouts, and error normalization to `ProviderError`.
- Non-streaming default for v1. If `stream=true` is passed, behavior must match core policy (documented below).

Ollama API:
- Endpoint: `POST {OLLAMA_HOST}/api/generate`
- Request (representative):
  {
    "model": "llama3",
    "prompt": "Write a poem.",
    "stream": false,
    "suffix": "optional",
    "options": {
      "num_predict": 128,
      "stop": ["###"],
      "temperature": 0.7,
      "top_p": 0.9,
      "seed": 123
    }
  }
- Response (non-streaming representative):
  {
    "model": "llama3",
    "created_at": "2024-01-02T10:20:30Z",
    "response": "The generated text...",
    "done": true,
    "done_reason": "stop",  // not always present; some impls only emit `done: true`
    "prompt_eval_count": 12,
    "eval_count": 130
  }

OpenAI Transformation Rules (per PRD):
- Request mapping:
  - `model` ← req.model
  - `prompt` ← req.prompt
  - `stream` ← req.stream (v1 default non-streaming; see behavior below)
  - `suffix` ← req.suffix
  - Parameters nested under `options`:
    - `num_predict` ← req.max_tokens
    - `stop` ← req.stop
    - `temperature` ← req.temperature
    - `top_p` ← req.top_p
    - `seed` ← req.seed
- Response mapping:
  - `id` ← generate `cmpl-<ulid/uuid>`
  - `object` ← "text_completion"
  - `created` ← epoch(response.created_at)
  - `model` ← response.model or req.model
  - `choices[0].text` ← response.response
  - `choices[0].finish_reason` ← derive from `done` / `done_reason` (if `done == true` → "stop"; otherwise map best-effort)
  - `choices[0].index` ← 0
  - `usage.prompt_tokens` ← response.prompt_eval_count (fallback 0)
  - `usage.completion_tokens` ← response.eval_count (fallback 0)
  - `usage.total_tokens` ← sum of the above

Tasks:
1. Request Construction
   - Build JSON body from OpenAI request, placing generation parameters into `options`.
   - Ensure unset optional fields are omitted (do not send nulls).
   - Status: ⚠️

2. Streaming Behavior (v1)
   - v1 default: non-streaming. If `req.stream == true`, choose one:
     - A) Return a deterministic error (e.g., `ProviderError` leading to HTTP 400/405 per core policy).
     - B) Force non-streaming by setting `stream=false` and document this behavior.
   - Align with core Feature 09 documented behavior to maintain consistency.
   - Status: ⚠️

3. HTTP Call and Timeout
   - POST `/api/generate` to `OLLAMA_HOST` with timeout `REQUEST_TIMEOUT_S`.
   - Headers: `Content-Type: application/json`; optionally include `X-Request-ID`.
   - Status: ⚠️

4. Response Parsing and Mapping
   - Extract fields: `response`, `created_at`, `model`, `prompt_eval_count`, `eval_count`, `done`, `done_reason`.
   - Map to OpenAI Completion response structure as specified.
   - Generate `id` with `cmpl-` prefix.
   - If `created_at` missing/unparseable, set a reasonable epoch fallback (e.g., current time or 0) and log a warning.
   - Status: ⚠️

5. Finish Reason Normalization
   - If `done_reason` present, map to OpenAI-compatible values: "stop", "length" (num_predict exhausted), etc.
   - If missing, infer "stop" when `done == true`, else set a conservative default and log debug note.
   - Status: ⚠️

6. Error Handling
   - Network/HTTP/timeout → raise `ProviderError` with minimal public message.
   - Missing `response` → `ProviderError` (malformed upstream).
   - Status: ⚠️

7. Observability
   - Log `request_id`, method=POST, path=/api/generate, status_code, duration_ms.
   - Avoid logging prompts or generated text; optionally log input length and result length only.
   - Status: ⚠️

Acceptance Criteria:
- `create_completion()` returns an OpenAI-compliant response with correct choices and usage.
- Streaming behavior is consistent with the core policy and documented.
- Errors are normalized; no provider internals leaked.
- Logging includes request_id, excludes sensitive data.

Test & Coverage Targets:
- Unit tests (mock HTTP):
  - Happy path mapping with all option fields.
  - Missing optional fields (suffix, options) → still valid mapping.
  - Streaming request behavior per chosen policy.
  - Missing `response` field → ProviderError.
  - Timeout/HTTP errors → ProviderError.
- Integration test via core route with this provider mock ensuring response schema compliance.

Review Checklist:
- Are all relevant OpenAI fields populated and typed correctly?
- Is `finish_reason` mapped appropriately under different `done`/`done_reason` cases?
- Are usage tokens computed as specified and robust to missing counts?
