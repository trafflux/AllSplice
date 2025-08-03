# Feature 01 — Introduction and Integration Overview

Status: ✅ Complete

Purpose:
Establish the Ollama provider’s role as a translation layer that implements the Core Provider Interface and maps OpenAI-compatible requests/responses to/from Ollama’s REST API. Leverage the Core OpenAI Endpoint Layer’s routing, auth, logging, and error normalization.

Outcomes:
- Clear description of where the Ollama provider plugs into the Core Endpoint Layer.
- Documented request/response mappings at a high level for models, embeddings, and chat completions.
- Legacy Completions explicitly excluded in v1.0 per Core OSI Final Summary.
- Defined operational assumptions for local Ollama instance and timeouts.

Core Integration Context (from OpenAI Endpoint Layer):
- Namespace-based routing dispatches `/{provider}/v1/...` to provider via DI (Feature 05 of core).
- Provider methods required (Feature 04 of core):
  - `list_models()`
  - `create_embeddings(req)`
  - `create_chat_completion(req)`
- Legacy `create_completion(req)` is out-of-scope for v1.0.
- Global behaviors:
  - Bearer auth enforced at transport layer; provider does not handle auth.
  - Errors normalized to `ProviderError` by the core handlers.
  - Correlation ID propagation via `request_id`.
  - Strict input/output alignment with OpenAI schemas.

Assumptions:
- Ollama is reachable at `http://localhost:11434` (configurable via env `OLLAMA_HOST`).
- Non-streaming only in v1.0; `stream=true` requests are rejected deterministically (normalized to 502 by core handler).
- All outbound calls include explicit timeout from `REQUEST_TIMEOUT_S`.

Tasks:
1. Integration Narrative
   - Describe provider lifecycle when a core route resolves `/ollama/...`.
   - Clarify that schemas validated by core are passed to provider as typed models.
   - Provider raises ProviderError for upstream issues which core normalizes to 502.
   - Status: ✅

2. High-Level Mapping Summary
   - Map OpenAI endpoints to Ollama API:
     - GET `/{provider}/v1/models` → GET `/api/tags`
     - POST `/{provider}/v1/embeddings` → POST `/api/embeddings`
     - POST `/{provider}/v1/chat/completions` → POST `/api/chat`
   - Status: ✅
     - POST `/{provider}/v1/completions` → Excluded in v1.0 (use chat completions)
     - POST `/{provider}/v1/chat/completions` → POST `/api/chat`
   - Status: ⚠️

3. Operational Parameters
   - Base URL from config `OLLAMA_HOST` (default http://localhost:11434).
   - Timeout from config `REQUEST_TIMEOUT_S` applied to all client calls.
   - Propagate `X-Request-ID` when available; avoid logging message or prompt content.
   - JSON encoding with `Content-Type: application/json`.
   - Status: ✅

4. Non-Goals
   - Streaming support is excluded in v1.0; provider rejects `stream=true`.
   - No transport/auth logic inside provider; this is delegated to the core layer.
   - Legacy Completions endpoint not implemented in v1.0.
   - Status: ✅

Dependencies:
- Core Feature 04 — Provider Interface Definition.
- Core Feature 05 — Routing and Namespace Resolution.
- Core middleware and exception handlers.

Acceptance Criteria:
- Overview demonstrates correct plug-in points with the Core layer.
- High-level mappings are listed for models, embeddings, and chat completions only.
- Operational assumptions are explicit and aligned to config-driven base URL and timeouts.
- Legacy completions called out as excluded.

Review Checklist:
- Does the overview avoid duplicating transport responsibilities?
- Are mappings clearly tied to the correct Ollama endpoints?
- Are configuration and timeouts documented?
