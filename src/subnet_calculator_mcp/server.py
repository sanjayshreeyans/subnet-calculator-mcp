"""Entry point for the Subnet Calculator MCP server."""

from __future__ import annotations

import argparse

from .tools import mcp


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the Subnet Calculator MCP server",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transport mode for the MCP server (only stdio is supported).",
    )
    return parser.parse_args()


def main() -> None:
    """Start the MCP server using the selected transport."""
    _parse_args()
    mcp.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
