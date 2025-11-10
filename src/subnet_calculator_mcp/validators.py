"""Pydantic schema definitions for MCP tool inputs."""

from __future__ import annotations

import ipaddress
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from .calculators import MAX_HOSTS


class SubnetCalculationRequest(BaseModel):
    """Input schema for subnet calculation requests."""

    network_base: ipaddress.IPv4Address = Field(..., description="Base IP address")
    hosts_needed: int = Field(
        ...,
        ge=0,
        le=MAX_HOSTS,
        description="Number of usable hosts required",
    )
    return_format: Literal["detailed", "simple"] = Field(
        default="detailed",
        description="Response format",
    )

    model_config = {
        "extra": "forbid",
    }

    @field_validator("network_base")
    @classmethod
    def validate_network_base(
        cls, value: str | ipaddress.IPv4Address, _: ValidationInfo
    ) -> ipaddress.IPv4Address:
        return ipaddress.IPv4Address(value)


class WildcardMaskRequest(BaseModel):
    """Input schema for wildcard mask calculations."""

    ip_address: ipaddress.IPv4Address
    cidr_prefix: int = Field(..., ge=0, le=32)
    include_ospf_command: bool = Field(default=True, description="Include OSPF command")

    model_config = {
        "extra": "forbid",
    }

    @field_validator("ip_address")
    @classmethod
    def validate_ip(
        cls, value: str | ipaddress.IPv4Address, _: ValidationInfo
    ) -> ipaddress.IPv4Address:
        return ipaddress.IPv4Address(value)


class ValidateIpRequest(BaseModel):
    """Input schema for IP validation within a subnet."""

    ip_address: ipaddress.IPv4Address
    network: ipaddress.IPv4Network
    return_gateway: bool = Field(default=True)

    model_config = {
        "extra": "forbid",
    }

    @field_validator("ip_address", mode="before")
    @classmethod
    def validate_ip_address(
        cls, value: str | ipaddress.IPv4Address, _: ValidationInfo
    ) -> ipaddress.IPv4Address:
        return ipaddress.IPv4Address(value)

    @field_validator("network", mode="before")
    @classmethod
    def validate_network(
        cls, value: str | ipaddress.IPv4Network, _: ValidationInfo
    ) -> ipaddress.IPv4Network:
        return ipaddress.IPv4Network(value, strict=False)


class SubnetFromMaskRequest(BaseModel):
    """Input schema for reverse subnet calculations."""

    ip_address: ipaddress.IPv4Address
    subnet_mask: ipaddress.IPv4Address

    model_config = {
        "extra": "forbid",
    }

    @field_validator("ip_address", mode="before")
    @classmethod
    def validate_ip(
        cls, value: str | ipaddress.IPv4Address, _: ValidationInfo
    ) -> ipaddress.IPv4Address:
        return ipaddress.IPv4Address(value)

    @field_validator("subnet_mask", mode="before")
    @classmethod
    def validate_subnet_mask(
        cls, value: str | ipaddress.IPv4Address, _: ValidationInfo
    ) -> ipaddress.IPv4Address:
        mask = ipaddress.IPv4Address(value)
        ipaddress.IPv4Network(("0.0.0.0", str(mask)))
        return mask


class NthUsableIpRequest(BaseModel):
    """Input schema for retrieving the Nth usable IP address."""

    network: ipaddress.IPv4Network
    position: int = Field(..., ge=1)

    model_config = {
        "extra": "forbid",
    }

    @field_validator("network")
    @classmethod
    def validate_network(
        cls, value: str | ipaddress.IPv4Network, _: ValidationInfo
    ) -> ipaddress.IPv4Network:
        return ipaddress.IPv4Network(value, strict=False)


# --- Tool 1: IP Conflict Detection ---
class IPAssignment(BaseModel):
    """Schema for a single IP assignment."""

    device: str
    interface: str
    ip: ipaddress.IPv4Address
    mask: str

    model_config = {"extra": "forbid"}

    @field_validator("ip", mode="before")
    @classmethod
    def validate_ip(
        cls, value: str | ipaddress.IPv4Address, _: ValidationInfo
    ) -> ipaddress.IPv4Address:
        return ipaddress.IPv4Address(value)


class DetectIPConflictsRequest(BaseModel):
    """Input schema for IP conflict detection."""

    ip_assignments: List[IPAssignment]
    model_config = {"extra": "forbid"}


# --- World Model Topology Schemas ---
class Device(BaseModel):
    """Schema for a network device in the topology."""

    name: str
    type: str  # "router", "switch", "pc", "server", etc.
    interfaces: Dict[str, Dict[str, Any]]  # e.g., {"Gig0/1": {"ip": "10.0.0.1/24"}}
    static_routes: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class Link(BaseModel):
    """Schema for a network link between devices."""

    source_device: str
    source_port: str
    target_device: str
    target_port: str
    attributes: Dict[str, Any] = Field(default_factory=dict)  # e.g., {"cost": 10}

    model_config = {"extra": "forbid"}


class NetworkTopology(BaseModel):
    """Schema for complete network topology."""

    devices: List[Device]
    links: List[Link]

    model_config = {"extra": "forbid"}


# --- Tool 2: Routing Reachability ---
class ValidateRoutingReachabilityRequest(BaseModel):
    """Input schema for routing reachability validation using full topology."""

    topology: NetworkTopology
    source_ip: str
    destination_ip: str

    model_config = {"extra": "forbid"}


# --- Tool 3: VLAN Assignments ---
class VlanAssignmentRequest(BaseModel):
    """Input schema for VLAN assignment calculation."""

    topology: Dict[str, Any]
    vlan_policy: Dict[str, Any]
    model_config = {"extra": "forbid"}


# --- Tool 4: Gateway Logic ---
class ValidateGatewayRequest(BaseModel):
    """Input schema for gateway validation."""

    device: str
    ip: str
    gateway: ipaddress.IPv4Address
    topology: Dict[str, Any]

    model_config = {"extra": "forbid"}

    @field_validator("gateway", mode="before")
    @classmethod
    def validate_gateway_ip(
        cls, value: str | ipaddress.IPv4Address, _: ValidationInfo
    ) -> ipaddress.IPv4Address:
        return ipaddress.IPv4Address(value)


# --- Tool 5: Route Table Builder ---
class RouteTableRequest(BaseModel):
    """Input schema for route table calculation."""

    directly_connected: List[Dict[str, Any]]
    static_routes: List[Dict[str, Any]]
    model_config = {"extra": "forbid"}


# --- Tool 6: Configuration Order ---
class ConfigOrderRequest(BaseModel):
    """Input schema for configuration order calculation."""

    topology: Dict[str, Any]
    requirements: List[str]
    model_config = {"extra": "forbid"}
