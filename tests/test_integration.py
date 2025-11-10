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


@pytest.mark.asyncio
async def test_detect_ip_conflicts_tool() -> None:
    """Test IP conflict detection tool integration."""
    from subnet_calculator_mcp.tools import detect_ip_conflicts

    assignments = [
        {"device": "R1", "interface": "Gig0/0", "ip": "10.0.0.1", "mask": "24"},
        {"device": "R2", "interface": "Gig0/1", "ip": "10.0.0.1", "mask": "24"},
    ]

    result = await detect_ip_conflicts(assignments)
    assert "conflicts" in result
    assert len(result["conflicts"]) == 1


@pytest.mark.asyncio
async def test_validate_routing_reachability_tool() -> None:
    """Test routing reachability validation tool integration."""
    from subnet_calculator_mcp.tools import validate_routing_reachability

    topology = {
        "devices": [
            {
                "name": "R1",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "10.0.1.1/24"}},
                "static_routes": [],
            },
            {
                "name": "R2",
                "type": "router",
                "interfaces": {"Gig0/1": {"ip": "10.0.2.1/24"}},
                "static_routes": [],
            },
        ],
        "links": [
            {
                "source_device": "R1",
                "source_port": "Gig0/1",
                "target_device": "R2",
                "target_port": "Gig0/0",
                "attributes": {},
            }
        ],
    }

    result = await validate_routing_reachability(topology, "10.0.1.1", "10.0.2.1")
    assert result["reachable"] is True
    assert result["hops"] == 1


@pytest.mark.asyncio
async def test_calculate_vlan_assignments_tool() -> None:
    """Test VLAN assignment calculation tool integration."""
    from subnet_calculator_mcp.tools import calculate_vlan_assignments

    topology = {
        "devices": [
            {"name": "SW1", "type": "switch"},
            {"name": "SW2", "type": "switch"},
        ],
        "connections": [
            {"device_a": "SW1", "port_a": "G0/1", "device_b": "SW2", "port_b": "G0/1"}
        ],
    }
    vlan_policy = {"trunk_vlans": [1, 10], "default_vlan": 1}

    result = await calculate_vlan_assignments(topology, vlan_policy)
    assert "port_assignments" in result
    assert len(result["port_assignments"]) > 0


@pytest.mark.asyncio
async def test_validate_gateway_logic_tool() -> None:
    """Test gateway validation tool integration."""
    from subnet_calculator_mcp.tools import validate_gateway_logic

    topology = {
        "devices": [
            {
                "name": "Gateway",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "192.168.1.1/24"}},
            }
        ]
    }

    result = await validate_gateway_logic(
        "PC1", "192.168.1.10/24", "192.168.1.1", topology
    )
    assert result["gateway_valid"] is True


@pytest.mark.asyncio
async def test_calculate_route_table_tool() -> None:
    """Test route table calculation tool integration."""
    from subnet_calculator_mcp.tools import calculate_route_table

    connected = [{"network": "10.0.0.0/24", "interface": "Gig0/0"}]
    static = [{"network": "192.168.0.0/16", "next_hop": "10.0.0.1", "metric": 1}]

    result = await calculate_route_table(connected, static)
    assert "routing_table" in result
    assert len(result["routing_table"]) == 2


@pytest.mark.asyncio
async def test_calculate_configuration_order_tool() -> None:
    """Test configuration order calculation tool integration."""
    from subnet_calculator_mcp.tools import calculate_configuration_order

    topology = {"devices": []}
    requirements = ["ip_addressing", "vlan_creation", "routing_protocol"]

    result = await calculate_configuration_order(topology, requirements)
    assert "configuration_order" in result
    assert len(result["configuration_order"]) == 3


@pytest.mark.asyncio
async def test_mcp_registry_contains_new_tools() -> None:
    """FastMCP instance should expose all new network analysis tools."""
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}

    expected_new_tools = {
        "detect_ip_conflicts",
        "validate_routing_reachability",
        "calculate_vlan_assignments",
        "validate_gateway_logic",
        "calculate_route_table",
        "calculate_configuration_order",
    }

    assert expected_new_tools.issubset(names)
