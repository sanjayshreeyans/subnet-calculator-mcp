"""Core subnet calculation utilities."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

MIN_PREFIX = 8
MAX_HOSTS = 4_294_967_294
DEFAULT_OSPF_AREA = 0


@dataclass(frozen=True)
class NetworkSummary:
    """Pre-computed details about a network used across calculations."""

    network: ipaddress.IPv4Network
    usable_hosts: int
    first_usable: Optional[ipaddress.IPv4Address]
    last_usable: Optional[ipaddress.IPv4Address]


def _usable_host_count(network: ipaddress.IPv4Network) -> int:
    """Return the number of usable host addresses in a network."""
    if network.prefixlen == 32:
        return 1
    if network.prefixlen == 31:
        return 2
    return max(network.num_addresses - 2, 0)


def _first_usable_ip(network: ipaddress.IPv4Network) -> Optional[ipaddress.IPv4Address]:
    """Return the first usable IP address for a network, if any."""
    if network.prefixlen == 32:
        return network.network_address
    if network.prefixlen == 31:
        return network.network_address
    if network.num_addresses <= 2:
        return None
    return network.network_address + 1


def _last_usable_ip(network: ipaddress.IPv4Network) -> Optional[ipaddress.IPv4Address]:
    """Return the last usable IP address for a network, if any."""
    if network.prefixlen == 32:
        return network.network_address
    if network.prefixlen == 31:
        return network.broadcast_address
    if network.num_addresses <= 2:
        return None
    return network.broadcast_address - 1


def _summarize_network(network: ipaddress.IPv4Network) -> NetworkSummary:
    """Collect common network statistics for downstream functions."""
    usable_hosts = _usable_host_count(network)
    return NetworkSummary(
        network=network,
        usable_hosts=usable_hosts,
        first_usable=_first_usable_ip(network),
        last_usable=_last_usable_ip(network),
    )


def _format_ip_binary(value: ipaddress.IPv4Address | str) -> str:
    """Convert an IPv4 address to dotted binary notation."""
    address = ipaddress.IPv4Address(str(value))
    bits = f"{int(address):032b}"
    return ".".join(bits[i : i + 8] for i in range(0, 32, 8))


def _calculate_prefix_for_hosts(hosts_needed: int) -> int:
    """Determine the most specific prefix that can fit the required hosts."""
    if not 0 <= hosts_needed <= MAX_HOSTS:
        raise ValueError("hosts_needed must be between 0 and 4,294,967,294")

    for prefix in range(32, MIN_PREFIX - 1, -1):
        network = ipaddress.IPv4Network(f"0.0.0.0/{prefix}")
        if hosts_needed <= _usable_host_count(network):
            return prefix
    raise ValueError("Unable to determine prefix for requested host count")


def _normalize_network(
    base_ip: ipaddress.IPv4Address, prefix: int
) -> ipaddress.IPv4Network:
    """Create a network aligned to the correct boundary for the prefix."""
    candidate = ipaddress.IPv4Network((base_ip, prefix), strict=False)
    if candidate.prefixlen < MIN_PREFIX:
        raise ValueError(
            f"Cannot fit network {base_ip} within supported prefix range /{MIN_PREFIX}-/32"
        )
    return candidate


def calculate_subnet_info(
    network_base: ipaddress.IPv4Address,
    hosts_needed: int,
    return_format: Literal["detailed", "simple"] = "detailed",
) -> Dict[str, Any]:
    """Calculate detailed subnet information for the requested host count."""
    prefix = _calculate_prefix_for_hosts(hosts_needed)
    network = _normalize_network(network_base, prefix)
    summary = _summarize_network(network)

    if hosts_needed > summary.usable_hosts:
        raise ValueError(f"Cannot fit {hosts_needed} hosts in network {network_base}")

    result: Dict[str, Any] = {
        "network_address": str(summary.network.network_address),
        "subnet_mask": str(summary.network.netmask),
        "cidr_prefix": summary.network.prefixlen,
        "wildcard_mask": str(summary.network.hostmask),
        "first_usable": str(summary.first_usable) if summary.first_usable else None,
        "last_usable": str(summary.last_usable) if summary.last_usable else None,
        "broadcast_address": str(summary.network.broadcast_address),
        "total_addresses": summary.network.num_addresses,
        "usable_hosts": summary.usable_hosts,
    }

    if return_format not in {"detailed", "simple"}:
        raise ValueError("return_format must be 'detailed' or 'simple'")

    if return_format == "detailed":
        result.update(
            {
                "network_binary": _format_ip_binary(summary.network.network_address),
                "mask_binary": _format_ip_binary(summary.network.netmask),
            }
        )

    return result


def calculate_wildcard_mask(
    ip_address: ipaddress.IPv4Address,
    cidr_prefix: int,
    include_ospf_command: bool = True,
    ospf_area: int = DEFAULT_OSPF_AREA,
) -> Dict[str, Any]:
    """Generate wildcard mask details for an IP/prefix combination."""
    if not 0 <= cidr_prefix <= 32:
        raise ValueError("cidr_prefix must be between 0 and 32")

    network = ipaddress.IPv4Network((ip_address, cidr_prefix), strict=False)
    wildcard = network.hostmask
    result: Dict[str, Any] = {
        "network_address": str(network.network_address),
        "subnet_mask": str(network.netmask),
        "wildcard_mask": str(wildcard),
        "cidr_prefix": network.prefixlen,
        "wildcard_binary": _format_ip_binary(wildcard),
    }

    if include_ospf_command:
        result["ospf_network_command"] = (
            f"network {network.network_address} {wildcard} area {ospf_area}"
        )

    return result


def calculate_subnet_from_mask(
    ip_address: ipaddress.IPv4Address,
    subnet_mask: ipaddress.IPv4Address,
) -> Dict[str, Any]:
    """Reverse-calculate subnet information from an IP and mask."""
    network = ipaddress.IPv4Network((ip_address, str(subnet_mask)), strict=False)
    summary = _summarize_network(network)
    return {
        "network_address": str(summary.network.network_address),
        "cidr_prefix": summary.network.prefixlen,
        "wildcard_mask": str(summary.network.hostmask),
        "first_usable": str(summary.first_usable) if summary.first_usable else None,
        "last_usable": str(summary.last_usable) if summary.last_usable else None,
        "broadcast_address": str(summary.network.broadcast_address),
        "total_addresses": summary.network.num_addresses,
        "usable_hosts": summary.usable_hosts,
    }


def validate_ip_in_subnet(
    ip_address: ipaddress.IPv4Address,
    network: ipaddress.IPv4Network,
    return_gateway: bool = True,
) -> Dict[str, Any]:
    """Validate whether an IP belongs to the provided subnet."""
    normalized_network = ipaddress.IPv4Network(str(network), strict=False)
    summary = _summarize_network(normalized_network)
    is_member = ip_address in normalized_network

    is_network_address = is_member and ip_address == normalized_network.network_address
    has_broadcast = normalized_network.prefixlen < 31
    is_broadcast_address = (
        is_member
        and has_broadcast
        and (ip_address == normalized_network.broadcast_address)
    )

    is_usable = (is_member and not is_network_address and not is_broadcast_address) or (
        normalized_network.prefixlen >= 31 and is_member
    )

    likely_gateway: Optional[str] = None
    if return_gateway and summary.first_usable:
        likely_gateway = str(summary.first_usable)

    position_in_subnet: Optional[int] = None
    addresses_remaining: Optional[int] = None
    if is_member and summary.first_usable and summary.last_usable:
        if normalized_network.prefixlen >= 31:
            offset = int(ip_address) - int(summary.first_usable)
            position_in_subnet = offset + 1
        else:
            if is_network_address or is_broadcast_address:
                position_in_subnet = None
            else:
                offset = int(ip_address) - int(summary.first_usable)
                position_in_subnet = offset + 1
        if position_in_subnet is not None:
            addresses_remaining = summary.usable_hosts - position_in_subnet

    return {
        "is_valid": is_member,
        "ip_address": str(ip_address),
        "network_address": str(normalized_network.network_address),
        "subnet_mask": str(normalized_network.netmask),
        "cidr_prefix": normalized_network.prefixlen,
        "is_network_address": is_network_address,
        "is_broadcast_address": is_broadcast_address,
        "is_usable": bool(is_usable),
        "likely_gateway": likely_gateway,
        "position_in_subnet": position_in_subnet,
        "addresses_remaining": addresses_remaining,
    }


def get_nth_usable_ip(
    network: ipaddress.IPv4Network,
    position: int,
) -> Dict[str, Any]:
    """Return the Nth usable IP within the network."""
    if position < 1:
        raise ValueError("position must be greater than or equal to 1")

    normalized_network = ipaddress.IPv4Network(str(network), strict=False)
    summary = _summarize_network(normalized_network)

    if summary.usable_hosts == 0:
        raise ValueError(f"Network {normalized_network} has no usable hosts")

    if position > summary.usable_hosts:
        raise ValueError(
            f"Network {normalized_network} only has {summary.usable_hosts} usable hosts"
        )

    if normalized_network.prefixlen >= 31:
        target_ip = normalized_network.network_address + (position - 1)
    else:
        assert summary.first_usable is not None  # defensive - ensured by usable hosts
        target_ip = summary.first_usable + (position - 1)

    return {
        "ip_address": str(target_ip),
        "position": position,
        "network_address": str(normalized_network.network_address),
        "is_last_usable": position == summary.usable_hosts,
        "total_usable": summary.usable_hosts,
    }


# --- Tool 1: IP Conflict Detection ---
def detect_ip_conflicts(
    ip_assignments: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Analyzes a list of IP assignments to find duplicates and subnet violations.

    Args:
        ip_assignments: List of dicts with keys: device, interface, ip, mask

    Returns:
        Dict containing conflicts, subnet_violations, gateway_conflicts
    """
    ip_map: dict[str, list[dict[str, str]]] = {}
    conflicts: list[dict[str, Any]] = []
    subnet_violations: list[dict[str, Any]] = []

    for item in ip_assignments:
        ip_str = str(item["ip"])
        ip = ipaddress.IPv4Address(ip_str)
        mask = str(item["mask"])

        # Create network from IP and mask
        network = ipaddress.IPv4Network(f"{ip_str}/{mask}", strict=False)

        # Check if IP is network or broadcast address (subnet violation)
        is_network = ip == network.network_address
        is_broadcast = network.prefixlen < 31 and ip == network.broadcast_address

        if is_network or is_broadcast:
            violation_type = "network_address" if is_network else "broadcast_address"
            subnet_violations.append(
                {
                    "device": item["device"],
                    "interface": item["interface"],
                    "ip": ip_str,
                    "mask": mask,
                    "network": str(network),
                    "violation_type": violation_type,
                    "message": f"IP {ip_str} is the {violation_type} of network {network}",
                }
            )

        # Check for duplicate IPs
        if ip_str in ip_map:
            # This is a conflict
            conflicts.append(
                {
                    "ip": ip_str,
                    "conflicting_devices": [
                        *ip_map[ip_str],
                        {"device": item["device"], "interface": item["interface"]},
                    ],
                    "message": f"IP {ip_str} is assigned to multiple devices",
                }
            )
        else:
            ip_map[ip_str] = [
                {"device": item["device"], "interface": item["interface"]}
            ]

    return {
        "conflicts": conflicts,
        "subnet_violations": subnet_violations,
        "total_ips_checked": len(ip_assignments),
    }


# --- Tool 2: Routing Reachability (uses world_model.py) ---
def validate_routing_reachability(
    topology: dict[str, Any],
    source_ip: str,
    destination_ip: str,
) -> dict[str, Any]:
    """
    Simulates L3 routing path between two IPs using graph-based world model.

    This uses networkx to build a full network graph and find the shortest path,
    simulating OSPF-style routing behavior.

    Args:
        topology: Full network topology with devices and links
        source_ip: Source IP address
        destination_ip: Destination IP address

    Returns:
        Dict with reachable status, path trace, and hop information
    """
    # Import here to avoid circular dependencies
    from .world_model import NetworkGraph

    try:
        # Build the network graph
        net_graph = NetworkGraph(topology)

        # Use graph pathfinding to determine reachability
        result = net_graph.find_l3_path(source_ip, destination_ip)

        return result

    except Exception as e:
        return {
            "reachable": False,
            "path": [],
            "hops": 0,
            "error": f"Failed to analyze topology: {str(e)}",
        }


# --- Tool 3: VLAN Assignments ---
def calculate_vlan_assignments(
    topology: dict[str, Any], vlan_policy: dict[str, Any]
) -> dict[str, Any]:
    """
    Calculates port modes (access/trunk) based on topology and VLAN policy.

    Args:
        topology: Network topology with devices and connections
        vlan_policy: VLAN policy rules

    Returns:
        Dict with port_assignments and vlan_propagation info
    """
    port_assignments: list[dict[str, Any]] = []
    vlan_propagation: dict[str, Any] = {}

    devices = topology.get("devices", [])
    connections = topology.get("connections", [])

    # Analyze each connection to determine trunk vs access
    for conn in connections:
        device_a = conn.get("device_a", "")
        port_a = conn.get("port_a", "")
        device_b = conn.get("device_b", "")
        port_b = conn.get("port_b", "")

        # Simple heuristic: switch-to-switch = trunk, switch-to-host = access
        device_a_info: dict[str, Any] = next(
            (d for d in devices if d.get("name") == device_a), {}
        )
        device_b_info: dict[str, Any] = next(
            (d for d in devices if d.get("name") == device_b), {}
        )

        type_a = device_a_info.get("type", "host")
        type_b = device_b_info.get("type", "host")

        if type_a == "switch" and type_b == "switch":
            mode = "trunk"
            allowed_vlans = vlan_policy.get("trunk_vlans", [1])
        elif type_a == "switch" or type_b == "switch":
            mode = "access"
            allowed_vlans = [vlan_policy.get("default_vlan", 1)]
        else:
            mode = "access"
            allowed_vlans = [vlan_policy.get("default_vlan", 1)]

        port_assignments.append(
            {
                "device": device_a,
                "port": port_a,
                "mode": mode,
                "vlans": allowed_vlans,
            }
        )

        port_assignments.append(
            {
                "device": device_b,
                "port": port_b,
                "mode": mode,
                "vlans": allowed_vlans,
            }
        )

    return {
        "port_assignments": port_assignments,
        "vlan_propagation": vlan_propagation,
    }


# --- Tool 4: Gateway Logic ---
def validate_gateway_logic(
    device: str, device_ip: str, device_gateway: str, topology: dict[str, Any]
) -> dict[str, Any]:
    """
    Validates if a device's gateway is valid and reachable on the L2 segment.

    Args:
        device: Device name
        device_ip: Device IP with mask (e.g., "192.168.1.10/24")
        device_gateway: Gateway IP address
        topology: Network topology

    Returns:
        Dict with gateway_valid, gateway_reachable, path_to_gateway
    """
    try:
        # Parse device IP and network
        device_network = ipaddress.IPv4Network(device_ip, strict=False)
        gateway_ip = ipaddress.IPv4Address(device_gateway)

        # Check if gateway is in same subnet
        gateway_in_subnet = gateway_ip in device_network

        if not gateway_in_subnet:
            return {
                "gateway_valid": False,
                "gateway_reachable": False,
                "path_to_gateway": [],
                "message": f"Gateway {device_gateway} is not in the same subnet as {device_ip}",
            }

        # Check if gateway is not network or broadcast address
        is_network = gateway_ip == device_network.network_address
        is_broadcast = (
            device_network.prefixlen < 31
            and gateway_ip == device_network.broadcast_address
        )

        if is_network or is_broadcast:
            violation = "network" if is_network else "broadcast"
            return {
                "gateway_valid": False,
                "gateway_reachable": False,
                "path_to_gateway": [],
                "message": f"Gateway {device_gateway} is the {violation} address",
            }

        # Check topology for L2 connectivity (same VLAN/segment)
        # Simplified: assume gateway is reachable if in same subnet
        devices = topology.get("devices", [])
        gateway_device = next(
            (
                d
                for d in devices
                if any(
                    str(iface_data.get("ip", "")).startswith(device_gateway)
                    for iface_data in d.get("interfaces", {}).values()
                )
            ),
            None,
        )

        if gateway_device:
            return {
                "gateway_valid": True,
                "gateway_reachable": True,
                "path_to_gateway": [
                    {"device": device, "ip": device_ip},
                    {
                        "device": gateway_device.get("name", "Gateway"),
                        "ip": device_gateway,
                    },
                ],
                "message": "Gateway is valid and reachable",
            }

        return {
            "gateway_valid": True,
            "gateway_reachable": False,
            "path_to_gateway": [],
            "message": "Gateway is in correct subnet but device not found in topology",
        }

    except (ValueError, ipaddress.AddressValueError) as e:
        return {
            "gateway_valid": False,
            "gateway_reachable": False,
            "path_to_gateway": [],
            "message": f"Invalid IP address format: {str(e)}",
        }


# --- Tool 5: Route Table Builder ---
def calculate_route_table(
    directly_connected: list[dict[str, Any]],
    static_routes: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Builds and validates a device's routing table.

    Args:
        directly_connected: List of directly connected networks
        static_routes: List of static route configurations

    Returns:
        Dict with routing_table, coverage_analysis, next_hop_validation
    """
    routing_table: list[dict[str, Any]] = []

    # Add directly connected routes
    for route in directly_connected:
        network = route.get("network", "")
        interface = route.get("interface", "")
        routing_table.append(
            {
                "network": network,
                "type": "connected",
                "interface": interface,
                "metric": 0,
                "admin_distance": 0,
            }
        )

    # Add static routes
    for route in static_routes:
        network = route.get("network", "")
        next_hop = route.get("next_hop", "")
        routing_table.append(
            {
                "network": network,
                "type": "static",
                "next_hop": next_hop,
                "metric": route.get("metric", 1),
                "admin_distance": route.get("admin_distance", 1),
            }
        )

    # Simple validation: check for duplicate networks
    networks_seen = set()
    next_hop_validation: list[dict[str, Any]] = []

    for route in routing_table:
        network = route["network"]
        if network in networks_seen:
            next_hop_validation.append(
                {
                    "network": network,
                    "status": "duplicate",
                    "message": f"Multiple routes to {network}",
                }
            )
        else:
            networks_seen.add(network)
            next_hop_validation.append(
                {
                    "network": network,
                    "status": "valid",
                    "message": "Route appears valid",
                }
            )

    coverage_analysis = {
        "total_routes": len(routing_table),
        "connected_routes": len(directly_connected),
        "static_routes": len(static_routes),
    }

    return {
        "routing_table": routing_table,
        "coverage_analysis": coverage_analysis,
        "next_hop_validation": next_hop_validation,
    }


# --- Tool 6: Configuration Order ---
def calculate_configuration_order(
    topology: dict[str, Any], requirements: list[str]
) -> dict[str, Any]:
    """
    Calculates the dependency order for network configuration tasks.

    Args:
        topology: Network topology
        requirements: List of configuration requirements

    Returns:
        Dict with configuration_order as a list of steps
    """
    # Basic dependency order for common network tasks
    task_priority = {
        "physical_connections": 1,
        "vlan_creation": 2,
        "trunk_configuration": 3,
        "access_port_configuration": 4,
        "ip_addressing": 5,
        "default_gateway": 6,
        "routing_protocol": 7,
        "static_routes": 8,
        "acls": 9,
        "services": 10,
    }

    configuration_order: list[dict[str, Any]] = []

    # Sort requirements by priority
    sorted_requirements = sorted(
        requirements,
        key=lambda x: task_priority.get(x.lower().replace(" ", "_"), 99),
    )

    for idx, requirement in enumerate(sorted_requirements, 1):
        task_key = requirement.lower().replace(" ", "_")
        priority = task_priority.get(task_key, 99)

        configuration_order.append(
            {
                "step": idx,
                "task": requirement,
                "priority": priority,
                "description": f"Configure {requirement}",
            }
        )

    return {"configuration_order": configuration_order}
