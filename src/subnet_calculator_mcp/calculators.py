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
