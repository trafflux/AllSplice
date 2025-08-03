# Universal AI Gateway

OpenAI-compatible API server to route chat completions to multiple providers (Custom, Cerebras, Ollama).

## Status
v1.0 implementation complete with authentication, routing, and provider integration.
- OpenAI compatibility updated (Phases 1–6): permissive schemas, expanded fields, headers parity, embeddings dimensions.
- Test suite green; coverage ~89% across src.

## Quickstart

### Prerequisites
- Python 3.12+
- uv package manager

### Setup
```bash
# Install dependencies
uv pip install -e .

# Copy environment template
cp .env.example .env

# Edit .env with your configuration (see below for details)

# Run in development mode
uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000
```

### Development Mode
For local development, set `DEVELOPMENT_MODE=true` in your `.env` file. This relaxes authentication requirements while still allowing you to test the API structure.

## Configuration
See `.env.example` for all available environment variables. Key settings include:
- `ALLOWED_API_KEYS`: Comma-separated list of valid API keys (required in production)
- `CEREBRAS_API_KEY`: API key for Cerebras provider
- `CEREBRAS_BASE_URL`: Optional custom Cerebras endpoint
- `OLLAMA_HOST`: Ollama server URL (default: http://localhost:11434)
- `REQUEST_TIMEOUT_S`: Request timeout in seconds (default: 30)
- `ENABLE_SECURITY_HEADERS`: Enable security headers (default: true)

## Docs
- PRD: PRD-1.0.md
- OpenAI Endpoint Design: docs/OpenAI-EndPoint/
- OAI Standards Report: docs/OAI-Standards/Report.md
- OAI Change Log: docs/OAI-Standards/OAI-CHANGE-LOG.md

## Quickstart (after Phase 4)
- Run (dev): `uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000`

## API Endpoints

All endpoints follow the OpenAI Chat Completions API format and require authentication via Bearer token.

Compatibility highlights:
- Requests are permissive (extra fields ignored) to accommodate evolving OpenAI SDK parameters.
- Chat messages accept content as string or minimal parts (text, image_url). Roles include system, user, assistant, tool, developer, function.
- Frequently used OpenAI fields supported on /chat/completions requests:
  - user, logit_bias, logprobs, top_logprobs, tools, tool_choice, functions, function_call,
    response_format, stream, stream_options, seed, metadata, store, parallel_tool_calls.
  - Streaming responses remain out-of-scope for v1; stream flags are accepted and handled non-streaming.
- Response parity:
  - Choice supports optional logprobs when available; response models are permissive to extra fields.
- Headers:
  - Responses include both X-Request-ID and x-request-id for SDK compatibility.
  - 401 includes WWW-Authenticate: Bearer.

### Health Check — GET /healthz
```bash
curl -X GET "http://localhost:8000/healthz"
```

### Default (Custom) — POST /v1/chat/completions
Routes to Custom Processing Provider (mock responses for development).

Example:
```bash
curl -s -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### Cerebras — POST /cerebras/v1/chat/completions
Routes to Cerebras Cloud API (requires CEREBRAS_API_KEY).

Example:
```bash
curl -s -X POST "http://localhost:8000/cerebras/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8b",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms"}
    ]
  }'
```

### Ollama — POST /ollama/v1/chat/completions
Routes to local or remote Ollama instance (requires OLLAMA_HOST configured).

Example:
```bash
curl -s -X POST "http://localhost:8000/ollama/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "granite3.3:2b",
    "messages": [
      {"role": "developer", "content": "You are a helpful assistant."},
      {"role": "user", "content": [
        {"type": "text", "text": "Write a Python function to calculate Fibonacci numbers"}
      ]}
    ],
    "response_format": {"type": "json_object"},
    "logprobs": true,
    "top_logprobs": 5,
    "user": "example-user"
  }'
```

Notes:
- For JSON responses, set response_format to {"type":"json_object"}.
- If logprobs are supported upstream, Choice.logprobs may be present in the response.
- Streaming is not enabled in v1; requests with stream=true are processed non-streaming.

## Authentication

All endpoints require an `Authorization: Bearer <API_KEY>` header. In development mode, authentication is relaxed but still recommended for testing.

Headers behavior:
- Request ID: Responses include both `X-Request-ID` and `x-request-id`.
- Unauthorized: 401 responses include `WWW-Authenticate: Bearer`.

### Development Mode
Set `DEVELOPMENT_MODE=true` in your environment to enable relaxed authentication. This allows testing without requiring valid API keys, but still validates the request structure.

### Production Mode
In production, configure `ALLOWED_API_KEYS` with a comma-separated list of valid API keys. The service will reject requests with unauthorized keys.

## Testing

Run the test suite:
```bash
# Run all tests
pytest -q

# Run with coverage
pytest --cov=src --cov-report=term-missing
```

Compatibility tests (what to look for):
- Chat: Accepts extra OpenAI fields (tools/tool_choice/response_format/logprobs/etc.) without 422.
- Messages: Accepts content as string or minimal parts (text/image_url); supports developer/function roles.
- Headers: Response includes both X-Request-ID and x-request-id; 401 contains WWW-Authenticate: Bearer.
- Embeddings: Accepts dimensions and forwards to provider when supported; deterministic fallbacks respect the requested dimensions in dev/local mode.
