from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error with a standardized shape.

    Attributes:
        message: Human-readable, non-sensitive error message.
        details: Optional dictionary with extra structured context (non-sensitive).
    """

    status_code: int = 500
    error_type: str = "internal_error"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        """Return the standardized error payload."""
        payload: dict[str, Any] = {
            "error": {
                "type": self.error_type,
                "message": self.message,
            }
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload


class AuthError(AppError):
    """Authentication/authorization failure (401)."""

    status_code = 401
    error_type = "auth_error"


class ValidationAppError(AppError):
    """Application-level validation error (422)."""

    status_code = 422
    error_type = "validation_error"


class ProviderError(AppError):
    """Upstream provider failure or timeout (502)."""

    status_code = 502
    error_type = "provider_error"


class InternalError(AppError):
    """Unexpected internal server error (500)."""

    status_code = 500
    error_type = "internal_error"
