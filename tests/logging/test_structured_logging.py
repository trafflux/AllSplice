import json
import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ai_gateway.api.app import get_app
from ai_gateway.logging.setup import configure_logging


@pytest.mark.anyio
async def test_access_log_contains_request_id_and_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure predictable log level without importing settings
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    app: FastAPI = get_app()

    # Capture logs emitted to root logger
    records: list[logging.LogRecord] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
            records.append(record)

    # Replace handlers with a capturing one but still run through our formatter/filter via configure_logging
    configure_logging()
    root = logging.getLogger()
    # Keep our configured handler (with our formatter) and add capture to inspect structured output
    capture = CaptureHandler(level=logging.INFO)
    root.addHandler(capture)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rid = "req-xyz-123"
        res = await client.get(
            "/healthz", headers={"X-Request-ID": rid, "Authorization": "Bearer sk-SECRET"}
        )
        assert res.status_code == 200
        # Find the access log record emitted by StructuredLoggingMiddleware
        access = None
        for r in records:
            if r.name == "ai_gateway.access":
                access = r
                break
        assert access is not None, "access log record not captured"
        # Format via our configured formatter to get JSON string
        fmt = root.handlers[0].formatter
        assert fmt is not None
        formatted = fmt.format(access)
        payload = json.loads(formatted)
        # Required fields
        assert payload["level"] in {"INFO", "DEBUG"}
        assert payload["request_id"] == rid
        assert payload["method"] == "GET"
        assert payload["path"] == "/healthz"
        assert isinstance(payload["status_code"], int)
        assert "duration_ms" in payload
        assert payload["message"] == "request completed"


@pytest.mark.anyio
async def test_redaction_of_authorization_and_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    app: FastAPI = get_app()

    # Force DEBUG to verify level switching
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    configure_logging()

    logs: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
            logger = logging.getLogger()
            fmt = logger.handlers[0].formatter
            assert fmt is not None
            formatted = fmt.format(record)
            logs.append(formatted)

    root = logging.getLogger()
    root.addHandler(Capture())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = "Bearer sk-THISISASECRETKEYSHOULDBEREDACTED"
        res = await client.get("/healthz", headers={"Authorization": token})
        assert res.status_code == 200

    # Find access JSON line and ensure redaction applied to message if any token-like substrings appear
    joined = "\n".join(logs)
    assert "sk-THISISASECRETKEYSHOULDBEREDACTED" not in joined
    assert "****" in joined
