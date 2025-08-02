from __future__ import annotations

from fastapi import Header

# Import module to ensure pytest monkeypatch on ai_gateway.config.config.get_settings is honored
from ai_gateway.config import config as config_module
from ai_gateway.config.constants import HDR_AUTHORIZATION
from ai_gateway.exceptions.errors import AuthError

SCHEME_BEARER: str = "Bearer"


def _parse_bearer_token(authorization: str | None) -> str:
    """Extract the bearer token from the Authorization header.

    Args:
        authorization: Value of the Authorization header.

    Returns:
        The extracted bearer token string.

    Raises:
        HTTPException: If the header is missing, malformed, has wrong scheme, or token is empty.

    Note:
        This function never logs or returns the token value to avoid secret leakage.
    """
    if not authorization:
        # Standardized 401 via AuthError; handlers will add WWW-Authenticate
        raise AuthError("Missing Authorization header")

    # Expect format: "Bearer <token>", single space
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        raise AuthError("Malformed Authorization header")

    scheme, token = parts[0], parts[1]
    if scheme != SCHEME_BEARER:
        raise AuthError("Invalid auth scheme")

    token = token.strip()
    if not token:
        raise AuthError("Empty bearer token")

    return token


def _parse_allowed_keys(csv: str | None) -> set[str]:
    """Parse a CSV of allowed API keys, trimming whitespace and ignoring empties."""
    if not csv:
        return set()
    # Split by comma, trim whitespace, drop empty results
    return {part.strip() for part in csv.split(",") if part.strip()}


async def auth_bearer(
    authorization: str | None = Header(default=None, alias=HDR_AUTHORIZATION),
) -> str | None:
    """FastAPI dependency that enforces Bearer token authentication.

    Validates that the bearer token in the Authorization header is present in the configured
    ALLOWED_API_KEYS list (comma-separated), with surrounding whitespace trimmed.

    In DEVELOPMENT_MODE with REQUIRE_AUTH disabled, auth is bypassed to enable local testing.

    On failure, responds with HTTP 401 and the 'WWW-Authenticate: Bearer' header, without leaking
    secret values.

    Args:
        authorization: The Authorization header value (injected by FastAPI).

    Returns:
        The validated token string for downstream use if needed.

    Raises:
        HTTPException: With 401 Unauthorized for any authentication error.
    """
    # IMPORTANT:
    # Obtain settings via the imported symbol so pytest monkeypatch on
    # "ai_gateway.config.config.get_settings" takes effect here.
    settings = config_module.get_settings()

    # If we're explicitly in development mode AND auth is disabled by settings,
    # bypass authentication entirely (no header required).
    if getattr(settings, "DEVELOPMENT_MODE", False) and not getattr(settings, "REQUIRE_AUTH", True):
        return None

    # Compute allowed keys BEFORE parsing the token so that any config issues don't depend
    # on token validity and tests can inject permissive settings reliably.
    allowed: set[str] = set()
    # Strict precedence: list field first
    ak_list = getattr(settings, "ALLOWED_API_KEYS", None)
    if isinstance(ak_list, list) and ak_list:
        allowed = {s for s in (str(item).strip() for item in ak_list) if s}
    elif isinstance(ak_list, str) and ak_list.strip():
        # In some setups Settings may coerce to a string; handle that too
        allowed = {part.strip() for part in ak_list.split(",") if part.strip()}

    # Then raw CSV field
    if not allowed:
        ak_raw = getattr(settings, "ALLOWED_API_KEYS_RAW", None)
        if isinstance(ak_raw, str) and ak_raw.strip():
            allowed = _parse_allowed_keys(ak_raw)

    # In development mode with REQUIRE_AUTH=True but no keys configured,
    # allow any token (still requiring proper Authorization header format)
    if getattr(settings, "DEVELOPMENT_MODE", False) and not allowed:
        token = _parse_bearer_token(authorization)
        return token

    # Only now parse and verify the token from the header.
    token = _parse_bearer_token(authorization)

    if token not in allowed:
        # Do not include token in message or logs
        raise AuthError("Invalid credentials")

    return token
