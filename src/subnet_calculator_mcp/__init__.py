"""Subnet Calculator MCP server package."""

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - package metadata unavailable during tests
    __version__ = version("subnet-calculator-mcp")
except PackageNotFoundError:  # pragma: no cover - fallback for local development
    __version__ = "0.0.0"

__all__ = ["__version__"]
