# Universal AI Gateway

OpenAI-compatible API server to route chat completions to multiple providers (Custom, Cerebras, Ollama).

## Status
v1.0 implementation complete with authentication, routing, and provider integration. Coverage: 91%.

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
- Tasks: TASKS-1.0.md
- Standards: PROJECT-STANDARDS.md

## Quickstart (after Phase 4)
- Run (dev): `uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000`

## API Endpoints

All endpoints follow the OpenAI Chat Completions API format and require authentication via Bearer token.

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
    "model": "llama3.1",
    "messages": [
      {"role": "user", "content": "Write a Python function to calculate fibonacci numbers"}
    ]
  }'
```

## Authentication

All endpoints require an `Authorization: Bearer <API_KEY>` header. In development mode, authentication is relaxed but still recommended for testing.

### Development Mode
Set `DEVELOPMENT_MODE=true` in your environment to enable relaxed authentication. This allows testing without requiring valid API keys, but still validates the request structure.

### Production Mode
In production, configure `ALLOWED_API_KEYS` with a comma-separated list of valid API keys. The service will reject requests with unauthorized keys.

## Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test categories
pytest tests/api/
pytest tests/providers/
```
