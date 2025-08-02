# Phase 9 — Middleware & Security Hardening

Status: Partially Complete

Scope
Implement correlation ID propagation, security headers, restricted CORS (disabled by default), and structured logging with redaction. Ensure strict typing and standardized error handling.

9.1 Correlation ID — src/ai_gateway/middleware/correlation.py
- [x] Middleware extracts X-Request-ID or generates a new request_id.
- [x] Contextvar propagation for request_id.
- [x] Tests in tests/middleware/test_correlation_id.py validate presence and behavior.

9.2 Security Headers — src/ai_gateway/middleware/security_headers.py
- [x] Middleware sets:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - Referrer-Policy: no-referrer
  - Permissions-Policy: ()
- [x] Enabled by default; can be toggled via settings.
- [x] Tests in tests/middleware/test_security_headers.py verify header presence and toggling.
- [x] Typing: verified and clean (addressed earlier note).

9.3 CORS (restricted) — app factory
- [x] Implemented in app factory with settings toggles (ENABLE_CORS, CORS_ALLOWED_ORIGINS, CORS_ALLOWED_HEADERS, CORS_ALLOWED_METHODS, CORS_ALLOW_CREDENTIALS).
- [x] Disabled by default; allowlist behavior when enabled.
- [x] tests/middleware/test_cors.py validate disabled/enabled behavior and preflight.

9.4 Structured Logging — src/ai_gateway/logging/setup.py
- [ ] Structured JSON or key-value formatter emitting:
  - timestamp, level, request_id, method, path, provider, status_code, duration_ms, message
- [ ] Redaction of known secrets (Authorization tokens, API keys) in logs.
- [ ] Wiring via LOG_LEVEL from Settings without eager Settings construction at app creation.
- [ ] Tests in tests/logging/test_structured_logging.py:
  - Inject X-Request-ID and assert log contains it.
  - Ensure sensitive values are redacted.
Status: Pending implementation.

Interactions and Notes
- App factory get_app() avoids eager Settings construction, ensuring tests can monkeypatch get_settings before app instantiation.
- CorrelationIdMiddleware must execute before SecurityHeaders at runtime; install order set accordingly (SecurityHeaders added first, then CorrelationId, so Correlation runs first).

Current Status Summary
- Correlation ID, Security Headers, and CORS implemented and tested.
- Structured logging scaffolding outstanding with tests.

Next Actions
- [ ] Implement logging setup with redaction and request_id propagation.
- [ ] Add tests/logging/test_structured_logging.py to assert fields and redaction.
- [ ] Optionally expand coverage on edge branches if coverage gaps remain.

Test/Coverage Snapshot (as of latest run)
- pytest: PASS (all tests)
- Total coverage: 89% (≥ 85% target)
