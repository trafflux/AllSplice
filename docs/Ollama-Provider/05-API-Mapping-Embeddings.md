# Feature 05 — API Mapping: Embeddings (POST /{provider}/v1/embeddings → POST /api/embeddings)

Status: ⚠️ Incomplete

Purpose:
Define the Ollama provider mapping for embeddings. Translate the core call `create_embeddings(req)` into Ollama’s `POST /api/embeddings` and transform the response into the OpenAI CreateEmbeddingResponse schema.

Core Integration Reference:
- Core route: `POST /{provider}/v1/embeddings` (Core Feature 08).
- Provider interface method: `async def create_embeddings(req) -> OpenAICreateEmbeddingsResponse` (Core Feature 04).
- Core enforces auth/validation and normalizes exceptions.
- Correlation ID propagated as `request_id`.
- Non-streaming v1 default.

Ollama API:
- Endpoint: `POST {OLLAMA_HOST}/api/embeddings`
- Request (representative):
  {
    "model": "llama3",
    "prompt": "text to embed"
  }
- Response (representative):
  {
    "embedding": [0.1, 0.2, ...],
    "model": "llama3",
    "created_at": "2024-01-02T10:20:30Z"
  }

OpenAI Transformation Rules (per PRD):
- Request:
  - `model` ← req.model
  - `prompt` ← req.input  (support string or list of strings per OpenAI spec; send single prompt per call)
- Response:
  - `object` ← "list"
  - `data[0].object` ← "embedding"
  - `data[0].embedding` ← response.embedding
  - `data[0].index` ← 0
  - `model` ← response.model (or req.model)
  - `usage` ← { "prompt_tokens": 0, "total_tokens": 0 } (Ollama does not provide usage)
  - `created` ← epoch(response.created_at) if available; optional for embeddings spec

Tasks:
1. Request Construction
   - Accept OpenAI inputs: `input` can be str | list[str]. For list inputs:
     - Strategy A (v1): Embed the first item only and document limitation; or
     - Strategy B (preferred): Loop and issue multiple Ollama calls, aggregating results into OpenAI list.
   - Encode JSON: `{ "model": req.model, "prompt": item }`.
   - Status: ⚠️

2. HTTP Call and Timeout
   - POST `/api/embeddings` with base URL from `OLLAMA_HOST` and timeout `REQUEST_TIMEOUT_S`.
   - Headers: `Content-Type: application/json`; optionally include `X-Request-ID`.
   - Status: ⚠️

3. Response Parsing and Mapping
   - Extract `embedding: list[float]`.
   - Map to OpenAI:
     - `object="list"`
     - `data=[ { "object": "embedding", "embedding": [...], "index": i } ]` for each prompt item processed.
     - `model` set to response.model or req.model as fallback.
     - `usage.prompt_tokens=0`, `usage.total_tokens=0`
     - `created` optionally from `created_at` converted to epoch.
   - Status: ⚠️

4. Error Handling
   - Network/HTTP/timeout → raise `ProviderError`.
   - Missing `embedding` → `ProviderError` (malformed upstream response).
   - For batch input strategy, fail only the affected item or fail entire request consistently; document chosen approach (v1: fail entire request).
   - Status: ⚠️

5. Observability
   - Log `request_id`, method=POST, path=/api/embeddings, status_code, duration_ms.
   - Do not log embedding vectors or full prompts; log counts/lengths only.
   - Status: ⚠️

6. Non-Streaming and Options
   - Ensure no streaming parameters included.
   - Confirm no options object required for embeddings on Ollama.
   - Status: ⚠️

Acceptance Criteria:
- `create_embeddings()` returns a valid OpenAI embeddings response for single and list inputs.
- Usage fields populated with zeros as specified.
- Errors normalized without leaking internals.
- Logging is privacy-preserving and includes request_id.

Test & Coverage Targets:
- Unit tests (mock HTTP):
  - Single input string → maps to one embedding item.
  - List input → maps to multiple items (if Strategy B chosen) or documented failure/limitation (if Strategy A).
  - Missing `embedding` field → ProviderError.
  - Timeout and HTTP errors normalized.
- Integration test via core route ensuring OpenAI schema compliance.

Review Checklist:
- Does the implementation honor OpenAI input cardinality?
- Are numerical types preserved (float list)?
- Are logs free of sensitive payloads and including request_id?
