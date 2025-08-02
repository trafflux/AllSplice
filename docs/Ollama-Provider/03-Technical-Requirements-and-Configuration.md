# Feature 03 — Technical Requirements and Configuration

Status: ⚠️ Incomplete

Purpose:
Detail environment assumptions, configuration, and connectivity for the Ollama provider, ensuring reliable operation within the Core OpenAI Endpoint Layer and alignment with organization standards.

Outcomes:
- Explicit env var contract and defaults.
- Connectivity and timeout behavior clearly specified.
- Non-streaming default behavior documented with fallback semantics.

Core Integration Context:
- Core handles transport/auth/validation and injects provider implementation (Core Feature 05).
- Provider uses Core config values (pydantic-settings) such as `REQUEST_TIMEOUT_S`.
- Correlation ID (request_id) is propagated from middleware; provider should pass along to client/logs.

Environment and Configuration:
- OLLAMA_HOST (e.g., `http://localhost:11434`) — required for local development; configurable per env.
- REQUEST_TIMEOUT_S (default 30) — applied to all outbound HTTP calls to Ollama.
- LOG_LEVEL (default INFO) — logging verbosity; avoid secrets in logs.
- ENABLE_SECURITY_HEADERS (default true) — handled by core middleware (not provider).
- SERVICE_HOST/PORT — core service bind; provider does not bind sockets.

Connectivity:
- The Ollama REST API must be reachable at `OLLAMA_HOST`.
- Health of Ollama is out of scope for provider; failures are normalized to `ProviderError`.
- DNS/Network issues must be retried only if configured; default: no retries (fail fast with timeout).

Tasks:
1. Env Var Contract
   - Document required/optional env vars and defaults (see above).
   - Ensure `OLLAMA_HOST` can be overridden without code changes (config-driven).
   - Status: ⚠️

2. HTTP Client Configuration
   - Use async HTTP client with:
     - Base URL = `OLLAMA_HOST`
     - Timeout = `REQUEST_TIMEOUT_S`
     - JSON Content-Type headers
     - Optional header for `X-Request-ID` if supported/desired for tracing
   - Status: ⚠️

3. Non-Streaming Default
   - Define default behavior when `stream=true` is passed by core request:
     - v1 default: return a deterministic, documented error (e.g., 400 Not Implemented for streaming) or ignore and force non-streaming if API supports it.
     - Align with Core Feature 09/10 stance to ensure consistent transport behavior.
   - Status: ⚠️

4. Error Normalization Path
   - Convert HTTP/network/timeouts into `ProviderError` with minimal public details.
   - Map HTTP status codes to internal error taxonomy (log internals; do not leak).
   - Status: ⚠️

5. Logging and Redaction
   - Include: `request_id`, `provider="ollama"`, `method`, `path`, `status_code`, `duration_ms`.
   - Do not log prompts, messages, embeddings, or secrets; log sizes/lengths only if necessary.
   - Status: ⚠️

6. Dependency Boundaries
   - Provider must not import core FastAPI/router modules.
   - Accept typed OpenAI models from core schemas; return typed OpenAI responses.
   - Status: ⚠️

Dependencies:
- Core Feature 04 — Provider Interface.
- Core Feature 11 — Standards, Tooling, and QA.
- Core config via pydantic-settings.

Acceptance Criteria:
- Config and env vars documented; provider uses only config, no hard-coded URLs.
- HTTP client has explicit timeout and content-type defaults.
- Non-streaming stance documented and consistent with core endpoints.
- Logging fields standardized; no sensitive data recorded.

Test & Coverage Targets:
- Unit tests mocking HTTP client for timeout and error normalization.
- Tests verifying base URL and timeout taken from config.
- Logs verified to contain request_id and exclude secrets.

Review Checklist:
- Can the provider run against different OLLAMA_HOST without code changes?
- Are timeouts and non-streaming behavior consistent with core?
- Are logs structured and privacy-preserving?
