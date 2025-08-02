from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import sys
import time
from typing import Any

from starlette.types import Scope

try:
    # Optional import; only used to pull request_id if middleware is installed.
    from ai_gateway.middleware.correlation import get_request_id
except Exception:  # pragma: no cover - defensive

    def get_request_id() -> str | None:
        return None


REDACTION_MASK = "****"

# Simple token-like detector to avoid logging obvious secrets if they sneak into messages.
# Matches long base64/hex-like strings or typical bearer/api tokens.
_SECRET_PATTERN = re.compile(
    r"""(?ix)
    \b(eyJ[0-9A-Za-z_\-]+\.|                           # JWT-like
       [A-Za-z0-9_\-]{24,}|                            # long opaque
       sk-[A-Za-z0-9]{16,}|                            # OpenAI-like keys
       (?:api|token|key|secret)[=:]\s*[^\s'"]{8,}      # key=value forms
    )\b
    """
)


def _redact(s: str) -> str:
    return _SECRET_PATTERN.sub(REDACTION_MASK, s)


class RedactingFilter(logging.Filter):
    """
    Logging filter that redacts secrets and normalizes optional fields.
    Does not assign dynamic attributes that confuse static typing.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        # Redact headers if present
        headers = getattr(record, "headers", None)
        if isinstance(headers, dict):
            record.headers = _redact_headers(headers)

        # Redact common string fields if present
        for attr in ("msg", "message", "pathname", "filename"):
            if hasattr(record, attr):
                val = getattr(record, attr)
                if isinstance(val, str):
                    setattr(record, attr, _redact(val))

        # Redact args conservatively
        if hasattr(record, "args") and record.args:
            with contextlib.suppress(Exception):  # pragma: no cover - defensive
                record.args = _redact_record_args(record.args)

        return True


class RequestContextFormatter(logging.Formatter):
    """
    Structured JSON formatter.
    Emits: timestamp, level, request_id, message, and optional HTTP fields if present.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        ts = time.time()
        # Resolve request_id without relying on dynamic attributes on LogRecord
        request_id = _resolve_request_id(record)
        base: dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "message": _redact(record.getMessage()),
            "request_id": request_id,
        }
        # Capture optional HTTP/request fields commonly attached to records
        for key in ("method", "path", "provider", "status_code", "duration_ms"):
            if hasattr(record, key):
                base[key] = getattr(record, key)
        # Include redacted headers if they were provided
        headers = getattr(record, "headers", None)
        if isinstance(headers, dict):
            base["headers"] = headers
        # Include logger name for debugging
        base["logger"] = record.name
        return json.dumps(base, ensure_ascii=False)


def _resolve_log_level() -> int:
    """
    Resolve log level from environment without constructing Settings.
    Falls back to INFO.
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    mapping = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return mapping.get(level, logging.INFO)


def configure_logging(*, level: int | None = None) -> None:
    """
    Configure root logger with a structured JSON formatter and redaction.
    Idempotent: safe to call multiple times.

    Does NOT import settings; reads LOG_LEVEL env directly if level is None.
    """
    root = logging.getLogger()
    # Idempotency: if a handler with our formatter is already present, return.
    for h in root.handlers:
        if isinstance(getattr(h, "formatter", None), RequestContextFormatter):
            return

    log_level = level if level is not None else _resolve_log_level()
    root.setLevel(log_level)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(RequestContextFormatter())
    handler.addFilter(RedactingFilter())

    # Remove default handlers that FastAPI/uvicorn may attach when run under pytest
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)


def _resolve_request_id(record: logging.LogRecord) -> str | None:
    """
    Determine request_id from:
      1) record.request_id if middleware attached it via extra
      2) correlation contextvar
      3) X-Request-ID header (case-insensitive) if headers present
    """
    explicit = getattr(record, "request_id", None)
    if isinstance(explicit, str) and explicit:
        return explicit
    try:
        from ai_gateway.middleware.correlation import get_request_id as _get

        rid = _get()
    except Exception:  # pragma: no cover - defensive
        rid = None
    if isinstance(rid, str) and rid:
        return rid
    headers = getattr(record, "headers", None)
    if isinstance(headers, dict):
        cand = headers.get("X-Request-ID") or headers.get("x-request-id")
        if isinstance(cand, str) and cand:
            return cand
    return None


def _redact_headers(headers: dict[str, Any]) -> dict[str, Any]:
    # Redact Authorization header entirely; redact token-like values elsewhere.
    new: dict[str, Any] = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            new[k] = REDACTION_MASK
        elif isinstance(v, str):
            new[k] = _redact(v)
        else:
            new[k] = v
    return new


def _redact_record_args(args: Any) -> Any:
    if isinstance(args, tuple):
        return tuple(_redact(a) if isinstance(a, str) else a for a in args)
    if isinstance(args, dict):
        return {k: (_redact(v) if isinstance(v, str) else v) for k, v in args.items()}
    return args


class RequestLogger:
    """
    Helper to log per-request lifecycle with structured fields.
    Attach to request.state.logger in middleware for convenience.
    """

    def __init__(self, scope: Scope) -> None:
        self._logger = logging.getLogger("ai_gateway.request")
        self._start = time.perf_counter()
        self._method = scope.get("method")
        self._path = scope.get("path")

    def log(self, level: int, message: str, **fields: Any) -> None:
        duration_ms = (time.perf_counter() - self._start) * 1000.0
        extra = {
            "method": self._method,
            "path": self._path,
            "duration_ms": round(duration_ms, 2),
        }
        if fields:
            extra.update(fields)
        self._logger.log(level, message, extra=extra)
        self._logger.log(level, message, extra=extra)
