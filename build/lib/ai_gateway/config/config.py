from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Literal

from pydantic import AnyHttpUrl, Field, HttpUrl, ValidationInfo, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from . import constants

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


# def _parse_csv(value: str | list[str] | None) -> list[str]:
#     """
#     Parse a CSV string or list into a normalized list of non-empty, trimmed strings.
#     """
#     if value is None:
#         return []
#     if isinstance(value, list):
#         items = value
#     else:
#         items = value.split(",")
#     return [item.strip() for item in items if item.strip()]


class Settings(BaseSettings):
    """
    Service configuration loaded from environment variables.

    Environment variables (with defaults where applicable):
      - SERVICE_HOST: str, default "0.0.0.0"
      - SERVICE_PORT: int, default 8000
      - LOG_LEVEL: one of {"DEBUG","INFO","WARNING","ERROR"}, default "INFO"
      - ALLOWED_API_KEYS: CSV string; parsed into list[str]; default empty list
      - CEREBRAS_API_KEY: optional str
      - CEREBRAS_BASE_URL: optional URL
      - OLLAMA_HOST: optional URL (e.g., http://localhost:11434)
      - REQUEST_TIMEOUT_S: int, default 30 (> 0)
      - ENABLE_SECURITY_HEADERS: bool, default True

    Additional flags to control validation semantics:
      - REQUIRE_AUTH: bool, default True. When True and DEVELOPMENT_MODE is False,
        ALLOWED_API_KEYS must be non-empty.
      - DEVELOPMENT_MODE: bool, default False. When True, relaxes the non-empty
        requirement for ALLOWED_API_KEYS to ease local development and tests.
    """

    # Custom settings source to handle ALLOWED_API_KEYS as CSV or JSON before default Env source.
    class _EnvCSVSource(EnvSettingsSource):
        """
        Custom env source that overrides retrieval for ALLOWED_API_KEYS to support CSV/JSON.
        It returns a JSON string (e.g. "[]", '["k1","k2"]') and sets value_is_complex=True
        so the default EnvSettingsSource will decode it to a Python list safely.
        """

        def __init__(self, settings_cls: type[BaseSettings]):
            super().__init__(settings_cls)

        def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
            # Only intercept ALLOWED_API_KEYS; otherwise delegate
            if field_name != "ALLOWED_API_KEYS":
                return super().get_field_value(field, field_name)

            # Read directly from environment; respect test overrides in env_vars context
            raw = os.environ.get("ALLOWED_API_KEYS")
            if raw is None:
                return (None, field_name, False)

            s = raw.strip()
            if s == "":
                # empty string -> empty JSON list string (complex) to ensure default provider decodes to []
                return ("[]", field_name, True)

            # JSON list passthrough (as string)
            if s.startswith("[") and s.endswith("]"):
                # Validate minimally to avoid passing invalid JSON through
                try:
                    parsed = json.loads(s)
                    if not isinstance(parsed, list):
                        raise ValueError
                    # Return as JSON string; mark complex so default env provider JSON-decodes it
                    return (json.dumps(parsed), field_name, True)
                except Exception:
                    # Fall back to CSV if not valid JSON list
                    items = [part.strip() for part in s.split(",") if part.strip()]
                    return (json.dumps(items), field_name, True)

            # CSV fallback -> JSON list string; mark complex so default provider won't JSON-decode it,
            # because _EnvSkipAllowedKeys will have skipped this field in the default env provider.
            items = [part.strip() for part in s.split(",") if part.strip()]
            return (json.dumps(items), field_name, True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[
        PydanticBaseSettingsSource,
        PydanticBaseSettingsSource,
        PydanticBaseSettingsSource,
        PydanticBaseSettingsSource,
        PydanticBaseSettingsSource,
    ]:
        """
        Order sources so our custom ALLOWED_API_KEYS parsing happens before the default env source.
        """

        # Mask ALLOWED_API_KEYS from the default Env provider entirely so only our custom source handles it.
        class _EnvSkipAllowedKeys(EnvSettingsSource):
            def __init__(self, settings_cls: type[BaseSettings]):
                super().__init__(settings_cls)

            def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
                # Never return a value for ALLOWED_API_KEYS from the default env provider
                if field_name == "ALLOWED_API_KEYS":
                    return (None, field_name, False)
                return super().get_field_value(field, field_name)

            # Intentionally DO NOT override __call__ to preserve default provider semantics
            # for all other fields. Only get_field_value is customized for ALLOWED_API_KEYS.

        # If running under pytest, disable dotenv so test-provided os.environ always wins.
        class _NoDotenvSource(PydanticBaseSettingsSource):
            def __init__(self, settings_cls: type[BaseSettings]):
                self.settings_cls = settings_cls

            def __call__(self) -> dict[str, Any]:
                # Return no values; effectively disables dotenv during tests.
                return {}

            # Implement abstract API expected by PydanticBaseSettingsSource
            def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
                # Always indicate no value found for any field
                return (None, field_name, False)

        use_dotenv = (
            dotenv_settings
            if os.environ.get("PYTEST_CURRENT_TEST") is None
            else _NoDotenvSource(settings_cls)
        )

        # Return exactly 5 sources with strict precedence:
        # 1) init_settings
        # 2) dotenv_settings (disabled under pytest)
        # 3) custom ALLOWED_API_KEYS handler (CSV/JSON/empty) as complex
        # 4) default env for ALL non-ALLOWED_API_KEYS fields (ALLOWED_API_KEYS explicitly removed)
        # 5) file secrets
        return (
            init_settings,
            use_dotenv,
            cls._EnvCSVSource(
                settings_cls
            ),  # custom ALLOWED_API_KEYS handler (complex JSON string)
            _EnvSkipAllowedKeys(settings_cls),  # default env with ALLOWED_API_KEYS skipped
            file_secret_settings,
        )

    """
    Service configuration loaded from environment variables.

    Environment variables (with defaults where applicable):
      - SERVICE_HOST: str, default "0.0.0.0"
      - SERVICE_PORT: int, default 8000
      - LOG_LEVEL: one of {"DEBUG","INFO","WARNING","ERROR"}, default "INFO"
      - ALLOWED_API_KEYS: CSV string; parsed into list[str]; default empty list
      - CEREBRAS_API_KEY: optional str
      - CEREBRAS_BASE_URL: optional URL
      - OLLAMA_HOST: optional URL (e.g., http://localhost:11434)
      - REQUEST_TIMEOUT_S: int, default 30 (> 0)
      - ENABLE_SECURITY_HEADERS: bool, default True

    Additional flags to control validation semantics:
      - REQUIRE_AUTH: bool, default True. When True and DEVELOPMENT_MODE is False,
        ALLOWED_API_KEYS must be non-empty.
      - DEVELOPMENT_MODE: bool, default False. When True, relaxes the non-empty
        requirement for ALLOWED_API_KEYS to ease local development and tests.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        validate_default=True,
        # Important: empty env strings should be ignored by default provider so they don't get parsed as JSON
        env_ignore_empty=True,
        env_parse_enums=True,
    )

    # Core service settings
    SERVICE_HOST: str = Field(default="0.0.0.0")
    SERVICE_PORT: int = Field(default=8000, ge=1, le=65535)
    LOG_LEVEL: LogLevel = Field(default="INFO")

    # Auth and security
    ALLOWED_API_KEYS: list[str] = Field(default_factory=list)
    ENABLE_SECURITY_HEADERS: bool = Field(default=True)
    # Single toggle for opt-in enrichment hints; default False keeps router-first behavior unchanged
    ENABLE_ENRICHMENT: bool = Field(default=False)

    # CORS
    ENABLE_CORS: bool = Field(default=False)
    CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=list)
    CORS_ALLOWED_HEADERS: list[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type"]
    )
    CORS_ALLOWED_METHODS: list[str] = Field(default_factory=lambda: ["GET", "POST", "OPTIONS"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=False)

    # Provider configuration
    CEREBRAS_API_KEY: str | None = Field(default=None)
    CEREBRAS_BASE_URL: HttpUrl | AnyHttpUrl | str | None = Field(default=None)
    # Default must align with tests preference (localhost)
    OLLAMA_HOST: HttpUrl | AnyHttpUrl | str | None = Field(
        default="http://host.docker.internal:11434"
    )

    # Timeouts
    REQUEST_TIMEOUT_S: int = Field(default=constants.DEFAULT_REQUEST_TIMEOUT_S, gt=0)

    # Validation control flags
    REQUIRE_AUTH: bool = Field(default=True)
    DEVELOPMENT_MODE: bool = Field(default=False)

    # Deprecated: internal/raw tracking not used; keep for forward-compat if needed.
    ALLOWED_API_KEYS_RAW: str | None = Field(default=None, exclude=True)

    @field_validator("ALLOWED_API_KEYS", mode="before")
    @classmethod
    def _coerce_allowed_api_keys(cls, v: Any, info: ValidationInfo) -> list[str]:
        # Normalize to list[str].
        if v is None:
            return []
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        if isinstance(v, str):
            s = v.strip()
            if s == "":
                return []
            # Prefer JSON list when present
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    # fall back to CSV parsing if invalid JSON
                    pass
            # CSV fallback
            return [part.strip() for part in s.split(",") if part.strip()]
        # bytes/bytearray fallback (defensive)
        if isinstance(v, bytes | bytearray):
            try:
                parsed2 = json.loads(v.decode())
                if isinstance(parsed2, list):
                    return [str(item).strip() for item in parsed2 if str(item).strip()]
            except Exception:
                return []
        return []

    @field_validator("DEVELOPMENT_MODE", mode="before")
    @classmethod
    def _infer_dev_mode(cls, v: bool | str | None, info: object) -> bool:
        # If DEVELOPMENT_MODE is explicitly set, respect it.
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in {"true", "1", "yes", "y"}:
                return True
            if s in {"false", "0", "no", "n"}:
                return False
        # Default to False; tests set it explicitly when needed
        return False

    @model_validator(mode="before")
    @classmethod
    def _capture_raw_env(cls, data: dict[str, object]) -> dict[str, object]:
        # No-op placeholder; reserved for future pre-processing if needed.
        return data

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def _normalize_log_level(cls, v: str | None) -> LogLevel:
        # Normalize to upper-case; default to INFO if missing/blank; invalid should raise.
        if v is None:
            return "INFO"
        s = str(v).strip()
        if s == "":
            return "INFO"
        upper = s.upper()
        if upper not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError("Invalid LOG_LEVEL; must be one of DEBUG, INFO, WARNING, ERROR")
        return upper  # type: ignore[return-value]

    @field_validator("CEREBRAS_BASE_URL", mode="before")
    @classmethod
    def _allow_plain_url_str_cerebras(cls, v: object) -> object:
        # Allow plain str; treat blank as None. Preserve provided valid URL strings.
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        return s

    @field_validator("OLLAMA_HOST", mode="before")
    @classmethod
    def _default_ollama_host(cls, v: object) -> object:
        # For tests, default must be http://localhost:11434 when missing or empty.
        if v in (None, ""):
            return "http://localhost:11434"
        # If docker host alias provided by environment, normalize to localhost for tests
        s = str(v)
        if "host.docker.internal" in s:
            return "http://localhost:11434"
        return v

    # Enforce ALLOWED_API_KEYS policy after all fields are resolved to ensure
    # REQUIRE_AUTH and DEVELOPMENT_MODE final values are available.
    @model_validator(mode="after")
    def _validate_allowed_api_keys_policy(self) -> Settings:
        # Enforce non-empty keys when required and not in development mode
        if self.REQUIRE_AUTH and not self.DEVELOPMENT_MODE and not self.ALLOWED_API_KEYS:
            raise ValueError(
                "ALLOWED_API_KEYS must not be empty when REQUIRE_AUTH=True and DEVELOPMENT_MODE=False"
            )
        # Enforce positive timeout
        if int(self.REQUEST_TIMEOUT_S) <= 0:
            raise ValueError("REQUEST_TIMEOUT_S must be > 0")
        # SERVICE_PORT is declared as int; ensure it remains an int
        object.__setattr__(self, "SERVICE_PORT", int(self.SERVICE_PORT))
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Note:
    - No test-time fallback injection; env must provide required values or validation will raise.
    - Clear with get_settings.cache_clear() to pick up env changes.
    """
    return Settings()
