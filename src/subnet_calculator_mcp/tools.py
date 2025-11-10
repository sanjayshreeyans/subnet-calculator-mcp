"""MCP tool implementations for subnet calculations."""

from __future__ import annotations

from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from .calculators import (
    calculate_configuration_order as compute_configuration_order,
    calculate_route_table as compute_route_table,
    calculate_subnet_from_mask as compute_subnet_from_mask,
    calculate_subnet_info as compute_subnet_info,
    calculate_vlan_assignments as compute_vlan_assignments,
    calculate_wildcard_mask as compute_wildcard_mask,
    detect_ip_conflicts as compute_ip_conflicts,
    get_nth_usable_ip as compute_nth_usable_ip,
    validate_gateway_logic as compute_gateway_logic,
    validate_ip_in_subnet as compute_validate_ip,
    validate_routing_reachability as compute_routing_reachability,
)
from .validators import (
    ConfigOrderRequest,
    DetectIPConflictsRequest,
    NthUsableIpRequest,
    RouteTableRequest,
    SubnetCalculationRequest,
    SubnetFromMaskRequest,
    ValidateGatewayRequest,
    ValidateIpRequest,
    ValidateRoutingReachabilityRequest,
    VlanAssignmentRequest,
    WildcardMaskRequest,
)

mcp = FastMCP("subnet-calculator")


@mcp.tool()
async def calculate_subnet(
    network_base: str,
    hosts_needed: int,
    return_format: str = "detailed",
) -> Dict[str, Any]:
    """Calculate subnet details given a base IP and required hosts."""
    request = SubnetCalculationRequest.model_validate(
        {
            "network_base": network_base,
            "hosts_needed": hosts_needed,
            "return_format": (
                return_format.lower()
                if isinstance(return_format, str)
                else return_format
            ),
        }
    )
    return compute_subnet_info(
        request.network_base,
        request.hosts_needed,
        request.return_format,
    )


@mcp.tool()
async def calculate_wildcard_mask(
    ip_address: str,
    cidr_prefix: int,
    include_ospf_command: bool = True,
) -> Dict[str, Any]:
    """Generate OSPF wildcard mask details for a subnet."""
    request = WildcardMaskRequest.model_validate(
        {
            "ip_address": ip_address,
            "cidr_prefix": cidr_prefix,
            "include_ospf_command": include_ospf_command,
        }
    )
    return compute_wildcard_mask(
        request.ip_address,
        request.cidr_prefix,
        request.include_ospf_command,
    )


@mcp.tool()
async def validate_ip_in_subnet(
    ip_address: str,
    network: str,
    return_gateway: bool = True,
) -> Dict[str, Any]:
    """Validate that an IP address belongs to a subnet and provide context."""
    request = ValidateIpRequest.model_validate(
        {
            "ip_address": ip_address,
            "network": network,
            "return_gateway": return_gateway,
        }
    )
    return compute_validate_ip(
        request.ip_address,
        request.network,
        request.return_gateway,
    )


@mcp.tool()
async def calculate_subnet_from_mask(
    ip_address: str,
    subnet_mask: str,
) -> Dict[str, Any]:
    """Calculate network information from an IP address and subnet mask."""
    request = SubnetFromMaskRequest.model_validate(
        {
            "ip_address": ip_address,
            "subnet_mask": subnet_mask,
        }
    )
    return compute_subnet_from_mask(
        request.ip_address,
        request.subnet_mask,
    )


@mcp.tool()
async def get_nth_usable_ip(
    network: str,
    position: int,
) -> Dict[str, Any]:
    """Return the Nth usable IP address in a subnet."""
    request = NthUsableIpRequest.model_validate(
        {
            "network": network,
            "position": position,
        }
    )
    return compute_nth_usable_ip(
        request.network,
        request.position,
    )


@mcp.tool()
async def detect_ip_conflicts(
    ip_assignments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Detects IP address conflicts and subnet violations from a list of assignments."""
    request = DetectIPConflictsRequest.model_validate(
        {"ip_assignments": ip_assignments}
    )
    return compute_ip_conflicts(
        [assignment.model_dump() for assignment in request.ip_assignments]
    )


@mcp.tool()
async def validate_routing_reachability(
    topology: Dict[str, Any],
    source_ip: str,
    destination_ip: str,
) -> Dict[str, Any]:
    """
    Validates L3 reachability between two IP addresses using full topology.

    Uses graph theory (networkx) to simulate routing and find the shortest path
    between devices, similar to OSPF behavior. Requires complete topology with
    devices and links.
    """
    request = ValidateRoutingReachabilityRequest.model_validate(
        {
            "topology": topology,
            "source_ip": source_ip,
            "destination_ip": destination_ip,
        }
    )
    return compute_routing_reachability(
        request.topology.model_dump(),
        request.source_ip,
        request.destination_ip,
    )


@mcp.tool()
async def calculate_vlan_assignments(
    topology: Dict[str, Any], vlan_policy: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculates port modes (access/trunk) based on topology and VLAN policy."""
    request = VlanAssignmentRequest.model_validate(
        {"topology": topology, "vlan_policy": vlan_policy}
    )
    return compute_vlan_assignments(request.topology, request.vlan_policy)


@mcp.tool()
async def validate_gateway_logic(
    device: str, ip: str, gateway: str, topology: Dict[str, Any]
) -> Dict[str, Any]:
    """Validates if a device's gateway is valid and reachable on the L2 segment."""
    request = ValidateGatewayRequest.model_validate(
        {"device": device, "ip": ip, "gateway": gateway, "topology": topology}
    )
    return compute_gateway_logic(
        request.device, str(request.ip), str(request.gateway), request.topology
    )


@mcp.tool()
async def calculate_route_table(
    directly_connected: List[Dict[str, Any]],
    static_routes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Builds and validates a device's routing table."""
    request = RouteTableRequest.model_validate(
        {
            "directly_connected": directly_connected,
            "static_routes": static_routes,
        }
    )
    return compute_route_table(
        request.directly_connected,
        request.static_routes,
    )


@mcp.tool()
async def calculate_configuration_order(
    topology: Dict[str, Any], requirements: List[str]
) -> Dict[str, Any]:
    """Calculates the dependency order for network configuration tasks."""
    request = ConfigOrderRequest.model_validate(
        {"topology": topology, "requirements": requirements}
    )
    return compute_configuration_order(request.topology, request.requirements)


__all__ = [
    "mcp",
    "calculate_subnet",
    "calculate_wildcard_mask",
    "validate_ip_in_subnet",
    "calculate_subnet_from_mask",
    "get_nth_usable_ip",
    "detect_ip_conflicts",
    "validate_routing_reachability",
    "calculate_vlan_assignments",
    "validate_gateway_logic",
    "calculate_route_table",
    "calculate_configuration_order",
]
