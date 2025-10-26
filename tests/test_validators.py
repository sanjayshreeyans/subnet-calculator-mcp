"""Validator tests to ensure robust input handling."""

from __future__ import annotations

import pytest

from subnet_calculator_mcp.validators import (
    NthUsableIpRequest,
    SubnetCalculationRequest,
    SubnetFromMaskRequest,
    ValidateIpRequest,
    WildcardMaskRequest,
)


def test_subnet_calculation_request_invalid_ip() -> None:
    """Invalid IP strings should trigger validation errors."""
    with pytest.raises(ValueError):
        SubnetCalculationRequest.model_validate(
            {"network_base": "999.999.999.999", "hosts_needed": 10}
        )


def test_wildcard_mask_request_invalid_prefix() -> None:
    """CIDR prefixes beyond 32 should be rejected."""
    with pytest.raises(ValueError):
        WildcardMaskRequest.model_validate(
            {"ip_address": "192.168.1.1", "cidr_prefix": 40}
        )


def test_validate_ip_request_network_normalization() -> None:
    """Network strings without alignment should still validate."""
    request = ValidateIpRequest.model_validate(
        {"ip_address": "192.168.1.1", "network": "192.168.1.5/24"}
    )
    assert str(request.network.network_address) == "192.168.1.0"


def test_subnet_from_mask_invalid_mask() -> None:
    """Invalid subnet masks should raise validation errors."""
    with pytest.raises(ValueError):
        SubnetFromMaskRequest.model_validate(
            {"ip_address": "192.168.1.1", "subnet_mask": "255.0.255.0"}
        )


def test_nth_usable_ip_request_invalid_position() -> None:
    """Positions below 1 should fail validation."""
    with pytest.raises(ValueError):
        NthUsableIpRequest.model_validate({"network": "10.0.0.0/24", "position": 0})
