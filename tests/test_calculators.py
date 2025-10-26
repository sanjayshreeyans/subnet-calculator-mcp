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
