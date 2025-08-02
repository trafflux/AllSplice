# Phase 3 — Authentication (Auth Dependency) Tasks

Authoritative source: .clinerules/project-standards.md. Python 3.12+, strict typing, mypy-clean, Ruff (lint+format), pytest with asyncio and coverage. Single-source tool configuration in pyproject.toml.

## 3.1 Auth Dependency

- [x] 3.1.1 Implement auth dependency (src/ai_gateway/middleware/auth.py)
  - Parse Authorization: Bearer <token>
  - Validate token against ALLOWED_API_KEYS (CSV, trim whitespace)
  - Return 401 with WWW-Authenticate: Bearer on failure
  - Strict typing, docstrings; no secret logging; mypy/ruff clean
  - Uses centralized config/constants

- [x] 3.1.2 Unit tests for auth dependency (tests/middleware/test_auth.py)
  - Cases:
    - Missing header
    - Malformed header (no space)
    - Wrong scheme (e.g., Basic)
    - Empty token (Bearer " " or missing token)
    - Invalid token (not present in allowed list)
    - Valid single token
    - CSV with whitespace (e.g., " key1 , key2 ,key3 ")
  - Ensure 401 with WWW-Authenticate: Bearer header for failures
  - Ensure no secrets are logged

## 3.2 Wiring (routers)

- [x] 3.2.1 Wire auth dependency into routers (api routes)
  - Depends(auth_bearer) present on protected endpoints in src/ai_gateway/api/routes.py
  - v1, /cerebras/v1, /ollama/v1 protected per design

- [ ] 3.2.2 Integration tests
  - tests/api/test_routes.py to verify Depends(auth_bearer) 401/200 paths
  - Update assertions to standardized error payload shape from global handlers: {"error": {...}}
  - Ensure presence of WWW-Authenticate: Bearer on failures

## 3.3 Config and Constants

- [x] 3.3.1 Ensure config exposes parsed ALLOWED_API_KEYS correctly
  - Confirm trimming and parsing behavior; custom env sources now normalize inputs

- [x] 3.3.2 Add constants for header names / schemes
  - e.g., AUTHORIZATION, BEARER, WWW_AUTHENTICATE

## Acceptance Criteria

- Auth dependency returns 401 with WWW-Authenticate: Bearer on any auth failure.
- Trims whitespace around keys; case-sensitive token matching.
- No secret/token values logged.
- Tests cover error paths and success, including CSV with whitespace.
- Code passes Ruff and mypy (strict), adheres to line length 100, complexity <10.

Notes (updated):
- Routers are now wired (done in later phases). Ensure integration tests reflect standardized error payloads and headers.
