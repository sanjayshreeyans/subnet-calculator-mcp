"""Integration tests exercising the full MCP tool stack."""

from __future__ import annotations

import pytest

from subnet_calculator_mcp.tools import calculate_subnet, mcp


@pytest.mark.asyncio
async def test_calculate_subnet_tool_call() -> None:
    """End-to-end test for the calculate_subnet MCP tool."""
    result = await calculate_subnet(network_base="172.16.0.16", hosts_needed=14)
    assert result["first_usable"] == "172.16.0.17"
    assert result["cidr_prefix"] == 28


@pytest.mark.asyncio
async def test_calculate_subnet_tool_invalid_params() -> None:
    """Invalid parameters should surface as ValueError from validators."""
    with pytest.raises(ValueError):
        await calculate_subnet(network_base="invalid", hosts_needed=-1)


@pytest.mark.asyncio
async def test_mcp_registry_contains_expected_tool() -> None:
    """FastMCP instance should expose the configured tools."""
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    assert {
        "calculate_subnet",
        "calculate_wildcard_mask",
        "validate_ip_in_subnet",
    }.issubset(names)
