# Feature 07 — API Mapping: Chat Completions (POST /{provider}/v1/chat/completions → POST /api/chat)

Status: ⚠️ Incomplete

Purpose:
Specify the Ollama provider mapping for Chat Completions. Translate the core call `create_chat_completion(req)` into Ollama’s `POST /api/chat` and transform the response into the OpenAI ChatCompletion response schema, aligning strictly with the Core OpenAI Endpoint Layer’s transport and schema constraints.

Core Integration Reference:
- Core route: `POST /{provider}/v1/chat/completions` (Core Feature 10).
- Provider interface method: `async def create_chat_completion(req) -> OpenAIChatCompletionResponse` (Core Feature 04).
- Core handles bearer auth, request validation (Pydantic), routing, and global error normalization. Provider focuses on request/response mapping, timeouts, and raising `ProviderError` for upstream issues.
- Non-streaming default for v1. If `stream=true` is provided by client, behavior must match core policy (documented below).

Ollama API:
- Endpoint: `POST {OLLAMA_HOST}/api/chat`
- Request (representative):
  {
    "model": "llama3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Write a haiku."}
    ],
    "stream": false,
    "format": "json",  // optional, from OpenAI response_format mapping
    "options": {
      "temperature": 0.7,
      "top_p": 0.9,
      "stop": ["###"],
      "seed": 123,
      "num_predict": 256
    }
  }
- Response (non-streaming representative):
  {
    "model": "llama3",
    "created_at": "2024-01-02T10:20:30Z",
    "message": { "role": "assistant", "content": "A short verse..." },
    "done": true,
    "done_reason": "stop",
    "prompt_eval_count": 12,
    "eval_count": 130
  }

OpenAI Transformation Rules (per PRD + Core):
- Request mapping:
  - `model` ← req.model
  - `messages` ← req.messages (directly compatible structure role/content)
  - `stream` ← req.stream (v1 default non-streaming; see behavior below)
  - `format` ← from `req.response_format`:
    - If `{"type": "json_object"}`, set `"format": "json"`
    - If unspecified or not json_object, omit `format`
  - Parameters nested under `options` (same as generate):
    - `num_predict` ← req.max_tokens
    - `stop` ← req.stop
    - `temperature` ← req.temperature
    - `top_p` ← req.top_p
    - `seed` ← req.seed
- Response mapping (OpenAI ChatCompletion):
  - `id` ← generate `chatcmpl-<ulid/uuid>`
  - `object` ← "chat.completion"
  - `created` ← epoch(response.created_at) (fallback if missing)
  - `model` ← response.model or req.model
  - `choices[0].index` ← 0
  - `choices[0].message` ← response.message (role/content)
  - `choices[0].finish_reason` ← derive from `done`/`done_reason` (default "stop" when `done == true`)
  - `usage.prompt_tokens` ← response.prompt_eval_count (fallback 0)
  - `usage.completion_tokens` ← response.eval_count (fallback 0)
  - `usage.total_tokens` ← sum

Tasks:
1. Request Construction
   - Build JSON body honoring allowed OpenAI fields and nesting generation parameters under `options`.
   - For `response_format`, only translate `{"type": "json_object"}` to `"format": "json"`. Otherwise omit.
   - Omit unset optional fields; do not send nulls.
   - Status: ⚠️

2. Streaming Behavior (v1)
   - v1 default: non-streaming. If `req.stream == true`, choose one in sync with core Feature 10:
     - A) Return `ProviderError` leading to HTTP 400/405 (document exact core mapping).
     - B) Force non-streaming by setting `stream=false`, with documented rationale.
   - Status: ⚠️

3. HTTP Call and Timeout
   - POST `/api/chat` to `OLLAMA_HOST` with timeout `REQUEST_TIMEOUT_S`.
   - Headers: `Content-Type: application/json`; optionally include `X-Request-ID`.
   - Status: ⚠️

4. Response Parsing and Mapping
   - Extract fields: `message{role,content}`, `created_at`, `model`, `prompt_eval_count`, `eval_count`, `done`, `done_reason`.
   - Map to OpenAI ChatCompletion response structure as specified.
   - Generate `id` with `chatcmpl-` prefix.
   - If `created_at` missing/unparseable, use safe fallback (e.g., current epoch or 0) and log a warning.
   - Status: ⚠️

5. Finish Reason Normalization
   - Map `done_reason` if available; otherwise infer "stop" when `done == true`.
   - Consider "length" mapping if `num_predict` likely exhausted (heuristic, optional).
   - Status: ⚠️

6. Tool/Function or Tool Roles (Compatibility Note)
   - If OpenAI messages contain roles beyond {system,user,assistant,tool}, validate upstream (core). Provider should be robust to the subset and ignore unsupported fields not present due to core validation.
   - Status: ⚠️

7. Error Handling
   - Network/HTTP/timeout → raise `ProviderError` with minimal message.
   - Missing `message` or malformed fields → `ProviderError`.
   - Status: ⚠️

8. Observability
   - Log `request_id`, method=POST, path=/api/chat, status_code, duration_ms.
   - Avoid logging message content; optionally log tokens/lengths only.
   - Status: ⚠️

Acceptance Criteria:
- `create_chat_completion()` returns an OpenAI-compliant ChatCompletion response with populated `choices[0].message` and `usage`.
- Streaming behavior aligns with core policy and is clearly documented.
- Errors normalized with no leakage; logs privacy-preserving and include request_id.

Test & Coverage Targets:
- Unit tests (mock HTTP):
  - Happy path mapping including `response_format` to `format`.
  - Optional parameters omitted vs. set; mapping to `options`.
  - Streaming request behavior per chosen policy.
  - Missing `message` or malformed response → ProviderError.
  - Timeout/HTTP errors → ProviderError.
- Integration tests via core route asserting schema shape and error normalization.

Review Checklist:
- Are roles and message structures preserved correctly?
- Is `finish_reason` mapped properly under `done`/`done_reason` variants?
- Are usage token fields robust to missing upstream counts?
