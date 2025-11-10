"""Unit tests for subnet calculation helpers."""

from __future__ import annotations

import ipaddress

import pytest

from subnet_calculator_mcp.calculators import (
    calculate_subnet_from_mask,
    calculate_subnet_info,
    calculate_wildcard_mask,
    get_nth_usable_ip,
    validate_ip_in_subnet,
)


def test_calculate_subnet_14_hosts() -> None:
    """Subnet calculation for 14 hosts should yield a /28 network."""
    result = calculate_subnet_info(ipaddress.IPv4Address("172.16.0.16"), 14)
    assert result["subnet_mask"] == "255.255.255.240"
    assert result["cidr_prefix"] == 28
    assert result["first_usable"] == "172.16.0.17"
    assert result["usable_hosts"] == 14


def test_calculate_subnet_2046_hosts() -> None:
    """Subnet calculation for 2046 hosts should select a /21 network."""
    result = calculate_subnet_info(ipaddress.IPv4Address("192.168.0.0"), 2046)
    assert result["subnet_mask"] == "255.255.248.0"
    assert result["cidr_prefix"] == 21
    assert result["usable_hosts"] == 2046


def test_wildcard_mask_slash30() -> None:
    """Wildcard mask calculation for a /30 subnet."""
    result = calculate_wildcard_mask(ipaddress.IPv4Address("155.74.10.6"), 30)
    assert result["wildcard_mask"] == "0.0.0.3"
    assert result["network_address"] == "155.74.10.4"
    assert result["ospf_network_command"].startswith("network 155.74.10.4 0.0.0.3")


def test_validate_ip_in_subnet() -> None:
    """Validation should confirm IP membership inside a subnet."""
    result = validate_ip_in_subnet(
        ipaddress.IPv4Address("172.16.0.19"),
        ipaddress.IPv4Network("172.16.0.16/28"),
    )
    assert result["is_valid"] is True
    assert result["likely_gateway"] == "172.16.0.17"


def test_calculate_subnet_from_mask() -> None:
    """Reverse subnet calculation should derive accurate network details."""
    result = calculate_subnet_from_mask(
        ipaddress.IPv4Address("192.168.0.1"),
        ipaddress.IPv4Address("255.255.248.0"),
    )
    assert result["network_address"] == "192.168.0.0"
    assert result["cidr_prefix"] == 21


def test_get_nth_usable_ip_edge_cases() -> None:
    """Nth usable IP should handle /31 and error conditions."""
    network = ipaddress.IPv4Network("10.0.0.0/31")
    first = get_nth_usable_ip(network, 1)
    second = get_nth_usable_ip(network, 2)
    assert first["ip_address"] == "10.0.0.0"
    assert second["ip_address"] == "10.0.0.1"

    with pytest.raises(ValueError):
        get_nth_usable_ip(network, 3)


def test_calculate_subnet_impossible_request() -> None:
    """Requests exceeding /8 capacity should raise an error."""
    with pytest.raises(ValueError):
        calculate_subnet_info(ipaddress.IPv4Address("10.0.0.0"), 20_000_000)


# --- Tests for new network analysis tools ---


def test_detect_ip_conflicts_finds_duplicates() -> None:
    """IP conflict detection should identify duplicate IPs."""
    from subnet_calculator_mcp.calculators import detect_ip_conflicts

    assignments = [
        {"device": "Router1", "interface": "Gig0/0", "ip": "192.168.1.1", "mask": "24"},
        {"device": "Router2", "interface": "Gig0/1", "ip": "192.168.1.1", "mask": "24"},
    ]
    result = detect_ip_conflicts(assignments)
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["ip"] == "192.168.1.1"
    assert len(result["conflicts"][0]["conflicting_devices"]) == 2


def test_detect_ip_conflicts_finds_subnet_violations() -> None:
    """IP conflict detection should identify network/broadcast address usage."""
    from subnet_calculator_mcp.calculators import detect_ip_conflicts

    assignments = [
        {
            "device": "Router1",
            "interface": "Gig0/0",
            "ip": "192.168.1.0",
            "mask": "24",
        },  # Network address
        {
            "device": "Router2",
            "interface": "Gig0/1",
            "ip": "192.168.1.255",
            "mask": "24",
        },  # Broadcast address
    ]
    result = detect_ip_conflicts(assignments)
    assert len(result["subnet_violations"]) == 2
    assert result["subnet_violations"][0]["violation_type"] == "network_address"
    assert result["subnet_violations"][1]["violation_type"] == "broadcast_address"


def test_detect_ip_conflicts_clean_network() -> None:
    """IP conflict detection should return empty lists for clean config."""
    from subnet_calculator_mcp.calculators import detect_ip_conflicts

    assignments = [
        {"device": "Router1", "interface": "Gig0/0", "ip": "192.168.1.1", "mask": "24"},
        {"device": "Router2", "interface": "Gig0/1", "ip": "192.168.1.2", "mask": "24"},
    ]
    result = detect_ip_conflicts(assignments)
    assert len(result["conflicts"]) == 0
    assert len(result["subnet_violations"]) == 0
    assert result["total_ips_checked"] == 2


def test_validate_gateway_logic_valid_gateway() -> None:
    """Gateway validation should pass for valid same-subnet gateway."""
    from subnet_calculator_mcp.calculators import validate_gateway_logic

    topology = {
        "devices": [
            {
                "name": "Gateway",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "192.168.1.1/24"}},
            }
        ]
    }
    result = validate_gateway_logic("PC1", "192.168.1.10/24", "192.168.1.1", topology)
    assert result["gateway_valid"] is True
    assert result["gateway_reachable"] is True


def test_validate_gateway_logic_wrong_subnet() -> None:
    """Gateway validation should fail for gateway in different subnet."""
    from subnet_calculator_mcp.calculators import validate_gateway_logic

    topology = {"devices": []}
    result = validate_gateway_logic("PC1", "192.168.1.10/24", "192.168.2.1", topology)
    assert result["gateway_valid"] is False
    assert result["gateway_reachable"] is False
    assert "not in the same subnet" in result["message"]


def test_validate_gateway_logic_network_address() -> None:
    """Gateway validation should fail for network address as gateway."""
    from subnet_calculator_mcp.calculators import validate_gateway_logic

    topology = {"devices": []}
    result = validate_gateway_logic("PC1", "192.168.1.10/24", "192.168.1.0", topology)
    assert result["gateway_valid"] is False
    assert "network address" in result["message"]


def test_calculate_route_table_combines_routes() -> None:
    """Route table calculation should combine connected and static routes."""
    from subnet_calculator_mcp.calculators import calculate_route_table

    connected = [{"network": "192.168.1.0/24", "interface": "Gig0/0"}]
    static = [{"network": "10.0.0.0/8", "next_hop": "192.168.1.254", "metric": 1}]

    result = calculate_route_table(connected, static)
    assert result["coverage_analysis"]["total_routes"] == 2
    assert result["coverage_analysis"]["connected_routes"] == 1
    assert result["coverage_analysis"]["static_routes"] == 1
    assert len(result["routing_table"]) == 2


def test_calculate_vlan_assignments_basic() -> None:
    """VLAN assignment should determine port modes based on topology."""
    from subnet_calculator_mcp.calculators import calculate_vlan_assignments

    topology = {
        "devices": [
            {"name": "Switch1", "type": "switch"},
            {"name": "Switch2", "type": "switch"},
        ],
        "connections": [
            {
                "device_a": "Switch1",
                "port_a": "Gig0/1",
                "device_b": "Switch2",
                "port_b": "Gig0/1",
            }
        ],
    }
    vlan_policy = {"trunk_vlans": [1, 10, 20], "default_vlan": 1}

    result = calculate_vlan_assignments(topology, vlan_policy)
    assert len(result["port_assignments"]) == 2
    # Switch-to-switch should be trunk
    assert all(p["mode"] == "trunk" for p in result["port_assignments"])


def test_calculate_configuration_order_sorts_by_priority() -> None:
    """Configuration order should sort tasks by dependency priority."""
    from subnet_calculator_mcp.calculators import calculate_configuration_order

    topology = {"devices": []}
    requirements = ["routing_protocol", "ip_addressing", "vlan_creation"]

    result = calculate_configuration_order(topology, requirements)
    # VLAN creation should come before IP addressing, which comes before routing
    order = [step["task"] for step in result["configuration_order"]]
    assert order.index("vlan_creation") < order.index("ip_addressing")
    assert order.index("ip_addressing") < order.index("routing_protocol")
