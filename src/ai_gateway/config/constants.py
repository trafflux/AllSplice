from __future__ import annotations

"""
Centralized constants for the Universal AI Gateway.

This module defines API paths, header names, provider identifiers, defaults, and
OpenAI-compatible object names. Import via `from ai_gateway.config import constants`
for a stable and unified import surface.
"""

# API base paths
V1_BASE: str = "/v1"
CEREBRAS_BASE: str = "/cerebras/v1"
OLLAMA_BASE: str = "/ollama/v1"
HEALTHZ: str = "/healthz"

# Header names
HDR_AUTHORIZATION: str = "Authorization"
HDR_WWW_AUTHENTICATE: str = "WWW-Authenticate"
HDR_REQUEST_ID: str = "X-Request-ID"

# Provider identifiers
PROVIDER_CUSTOM: str = "custom"
PROVIDER_CEREBRAS: str = "cerebras"
PROVIDER_OLLAMA: str = "ollama"

# Defaults / Timeouts
DEFAULT_REQUEST_TIMEOUT_S: int = 30

# OpenAI-compatible object names
OBJECT_CHAT_COMPLETION: str = "chat.completion"
