# Feature 07 — API Mapping: Chat Completions (POST /{provider}/v1/chat/completions → POST /api/chat)

Status: ✅ Provider mapping implemented; ✅ Client is real HTTP with CI-safe fallbacks; ✅ Router-first pass-through in place; ✅ Structured responses supported via response_format=json; ⚙️ Enrichment toggle available (ENABLE_ENRICHMENT) for future layers without behavior change.

Purpose:
Define a DRY, best-practice mapping between OpenAI Chat Completions and Ollama /api/chat for non-streaming v1.0. The provider acts as a router-first adapter: it faithfully forwards OpenAI fields to Ollama (via `options` and `format`), normalizes upstream responses to OpenAI schema, and remains ready for future enrichment layers (prompt compression, context optimization, tool routing) controlled by a single feature toggle.

Core Integration Reference:
- Core route: `POST /{provider}/v1/chat/completions` (Core Feature 10).
- Provider interface method: `async def chat_completions(req) -> ChatCompletionResponse` (Core Feature 04).
- Core handles bearer auth, request validation (Pydantic), routing, and global error normalization. Provider focuses on mapping, timeouts, correlation header forwarding, and raising `ProviderError` for upstream issues.
- Non-streaming only in v1.0. If `stream=true` is provided by client, the provider rejects deterministically (ProviderError → normalized to 502).

Ollama API (non-streaming):
- Endpoint: `POST {OLLAMA_HOST}/api/chat`
- Request (representative):
  {
    "model": "llama3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Write a haiku."}
    ],
    "stream": false,
    "format": "json",  // optional from OpenAI response_format mapping
    "options": {
      "num_predict": 256,
      "stop": ["###"],
      "temperature": 0.7,
      "top_p": 0.9,
      "seed": 123,
      // captured pass-through fields for future use:
      "top_k": 40,
      "presence_penalty": 0.0,
      "frequency_penalty": 0.0,
      "logprobs": null,
      "logit_bias": {"123": 1.5},
      "n": 1,
      "user": "caller-id",
      "tools": [{"type": "function", "function": {"name": "toolA", "parameters": {}}}],
      "tool_choice": "auto",
      "structured": true // when response_format=json_object
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

OpenAI → Ollama Request Mapping (Router-first):
- Required:
  - `model` ← req.model
  - `messages` ← req.messages (role/content)
  - `stream` ← false (v1.0; reject if true)
- `format`:
  - If req.response_format == {"type": "json_object"} → `"format": "json"`
  - Otherwise omit `format`
- `options` (direct mappings):
  - `num_predict` ← req.max_tokens
  - `stop` ← req.stop (str | list[str] normalized to list[str])
  - `temperature` ← req.temperature
  - `top_p` ← req.top_p
  - `seed` ← req.seed
- `options` (pass-through captures for parity and future enrichment):
  - `top_k` ← req.top_k
  - `presence_penalty` ← req.presence_penalty
  - `frequency_penalty` ← req.frequency_penalty
  - `logprobs` ← req.logprobs
  - `logit_bias` ← req.logit_bias
  - `n` ← req.n
  - `user` ← req.user
  - `tools` ← req.tools
  - `tool_choice` ← req.tool_choice
- Structured responses:
  - When `format=json` is set (from response_format), provider also sets `options.structured=true`.
  - If ENABLE_ENRICHMENT is enabled, provider adds `options.enforce_structured=true` and `options.enrichment={"enabled": true}`.

Ollama → OpenAI Response Mapping:
- `id` ← generated as `chatcmpl-<uuid>`
- `object` ← "chat.completion"
- `created` ← epoch(datetime.fromisoformat(created_at)) or now on parse failure
- `model` ← req.model (or response.model if provided)
- `choices[0]`:
  - `index` ← 0
  - `message` ← response.message (role/content)
  - `finish_reason` ← "stop" when `done == true` or `done_reason == "stop"`
- `usage`:
  - `prompt_tokens` ← prompt_eval_count (fallback 0)
  - `completion_tokens` ← eval_count (fallback 0)
  - `total_tokens` ← sum

Tasks:
1. Request Construction
   - Build JSON body honoring OpenAI fields and nest generation parameters under `options`.
   - Translate response_format={"type":"json_object"} → `"format": "json"` and set `options.structured=true`.
   - Omit unset optionals; do not send null.
   - Status: ✅ (Provider constructs options and format; client performs real HTTP)

2. Streaming Behavior (v1)
   - v1.0 excludes streaming. If `req.stream == true`, raise ProviderError (normalized to 502).
   - Status: ✅

3. HTTP Call and Timeout
   - POST `/api/chat` to `OLLAMA_HOST` with timeout `REQUEST_TIMEOUT_S`.
   - Headers: `Content-Type: application/json`; forward `X-Request-ID` when available.
   - Status: ✅

4. Response Parsing and Mapping
   - Extract: `message{role,content}`, `created_at`, `model`, `prompt_eval_count`, `eval_count`, `done`, `done_reason`.
   - Map to OpenAI schema; `id` with `chatcmpl-` prefix; `created` epoch parse fallback to now.
   - Status: ✅

5. Finish Reason Normalization
   - Prefer `done_reason`; fallback "stop" when `done == true`.
   - Status: ✅

6. Router-first Captures (Tools/Functions)
   - Capture `tools`, `tool_choice`, `function_call` into `options` for future orchestration.
   - Status: ✅ (captured, not enforced)

7. Error Handling
   - httpx timeout/network/status → ProviderError (via provider normalization).
   - Malformed response (missing message) → ProviderError.
   - Status: ✅

8. Observability
   - Log `request_id`, provider="ollama", method, path, status_code, duration_ms (see logging module).
   - Never log secrets or raw prompts.
   - Status: ✅

Acceptance Criteria:
- `chat_completions()` returns OpenAI-compliant response with `choices[0].message` and `usage`.
- Streaming disabled with deterministic error.
- Router-first parity: OpenAI options intercepted and forwarded/captured in `options`.
- Structured responses supported via `response_format=json_object`.

Test & Coverage Targets:
- Unit tests:
  - Mapping of `response_format` to `format`, and options pass-through including structured hint.
  - Streaming rejection.
  - Invalid upstream payload → ProviderError.
  - Client header forwarding (`X-Request-ID`) and localhost fallback behavior.
- Integration tests via core to assert schema shape and normalized errors.

Review Checklist (DRY/Best Practices):
- No duplicate mapping logic; shared helper paths where possible.
- Minimal optional fields; no nulls; normalized types (e.g., stop to list[str]).
- Low cyclomatic complexity and cohesive functions; strict typing; lint clean.
