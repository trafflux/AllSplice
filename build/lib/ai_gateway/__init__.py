"""Top-level package for ai_gateway.

Exposes version/build metadata for operational endpoints (e.g., /healthz).
These values may be overridden by CI at build time.
"""

# Default semantic version; CI can replace this during build/publish.
__version__ = "0.0.0"

# Optional build identifier (e.g., short git SHA or build number). May be overridden by CI.
__build__: str | None = None

__all__ = ["__version__", "__build__"]
