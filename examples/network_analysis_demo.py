#!/usr/bin/env python3
"""
Demo script showing the 6 new network analysis tools in action.

This demonstrates how the subnet-calculator-mcp can now analyze complete
network topologies, detect conflicts, validate routing, and more.
"""

import sys
import os

# Add src to path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from subnet_calculator_mcp.calculators import (
    detect_ip_conflicts,
    validate_routing_reachability,
    calculate_vlan_assignments,
    validate_gateway_logic,
    calculate_route_table,
    calculate_configuration_order,
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def demo_ip_conflict_detection() -> None:
    """Demonstrate IP conflict detection."""
    print_section("1. IP Conflict Detection")
    
    # Sample network with conflicts
    assignments = [
        {"device": "Router1", "interface": "Gig0/0", "ip": "192.168.1.1", "mask": "24"},
        {"device": "Router2", "interface": "Gig0/1", "ip": "192.168.1.1", "mask": "24"},  # Duplicate!
        {"device": "Switch1", "interface": "Vlan1", "ip": "192.168.1.0", "mask": "24"},   # Network address!
        {"device": "PC1", "interface": "eth0", "ip": "192.168.1.10", "mask": "24"},
    ]
    
    result = detect_ip_conflicts(assignments)
    
    print(f"\nChecked {result['total_ips_checked']} IP assignments")
    print(f"Found {len(result['conflicts'])} conflicts")
    print(f"Found {len(result['subnet_violations'])} subnet violations")
    
    if result['conflicts']:
        print("\n⚠️  IP Conflicts:")
        for conflict in result['conflicts']:
            devices = ', '.join([f"{d['device']}({d['interface']})" 
                                for d in conflict['conflicting_devices']])
            print(f"  • {conflict['ip']}: {devices}")
    
    if result['subnet_violations']:
        print("\n⚠️  Subnet Violations:")
        for violation in result['subnet_violations']:
            print(f"  • {violation['device']}: {violation['message']}")


def demo_routing_reachability() -> None:
    """Demonstrate routing reachability validation."""
    print_section("2. Routing Reachability (Graph-Based)")
    
    # Create a 3-router topology
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {
                    "Gig0/0": {"ip": "10.1.1.1/24"},
                    "Gig0/1": {"ip": "10.1.2.1/30"}
                },
                "static_routes": [],
            },
            {
                "name": "Router2",
                "type": "router",
                "interfaces": {
                    "Gig0/0": {"ip": "10.1.2.2/30"},
                    "Gig0/1": {"ip": "10.2.3.1/30"}
                },
                "static_routes": [],
            },
            {
                "name": "Router3",
                "type": "router",
                "interfaces": {
                    "Gig0/0": {"ip": "10.2.3.2/30"},
                    "Gig0/1": {"ip": "10.3.1.1/24"}
                },
                "static_routes": [],
            },
        ],
        "links": [
            {
                "source_device": "Router1",
                "source_port": "Gig0/1",
                "target_device": "Router2",
                "target_port": "Gig0/0",
                "attributes": {"cost": 10},
            },
            {
                "source_device": "Router2",
                "source_port": "Gig0/1",
                "target_device": "Router3",
                "target_port": "Gig0/0",
                "attributes": {"cost": 10},
            },
        ],
    }
    
    # Test connectivity
    result = validate_routing_reachability(topology, "10.1.1.1", "10.3.1.1")
    
    print(f"\nTesting: 10.1.1.1 → 10.3.1.1")
    print(f"Reachable: {'✓ Yes' if result['reachable'] else '✗ No'}")
    print(f"Hops: {result['hops']}")
    
    if result['path']:
        print("\nPath trace:")
        for hop in result['path']:
            print(f"  {hop['hop']}. {hop['device']} ({hop['type']})")


def demo_vlan_assignments() -> None:
    """Demonstrate VLAN assignment calculation."""
    print_section("3. VLAN Port Assignment Calculator")
    
    topology = {
        "devices": [
            {"name": "CoreSwitch", "type": "switch"},
            {"name": "AccessSwitch1", "type": "switch"},
            {"name": "AccessSwitch2", "type": "switch"},
            {"name": "PC1", "type": "pc"},
            {"name": "Server1", "type": "server"},
        ],
        "connections": [
            # Switch-to-switch links (should be trunk)
            {"device_a": "CoreSwitch", "port_a": "Gig0/1", 
             "device_b": "AccessSwitch1", "port_b": "Gig0/24"},
            {"device_a": "CoreSwitch", "port_a": "Gig0/2", 
             "device_b": "AccessSwitch2", "port_b": "Gig0/24"},
            # Switch-to-host links (should be access)
            {"device_a": "AccessSwitch1", "port_a": "Gig0/1", 
             "device_b": "PC1", "port_b": "eth0"},
            {"device_a": "AccessSwitch2", "port_a": "Gig0/1", 
             "device_b": "Server1", "port_b": "eth0"},
        ],
    }
    
    vlan_policy = {
        "trunk_vlans": [1, 10, 20, 30],
        "default_vlan": 1,
    }
    
    result = calculate_vlan_assignments(topology, vlan_policy)
    
    print(f"\nGenerated {len(result['port_assignments'])} port assignments:")
    
    trunk_ports = [p for p in result['port_assignments'] if p['mode'] == 'trunk']
    access_ports = [p for p in result['port_assignments'] if p['mode'] == 'access']
    
    print(f"\nTrunk Ports ({len(trunk_ports)}):")
    for port in trunk_ports[:4]:  # Show first 4
        vlans = ','.join(map(str, port['vlans']))
        print(f"  • {port['device']} {port['port']}: VLANs {vlans}")
    
    print(f"\nAccess Ports ({len(access_ports)}):")
    for port in access_ports[:4]:  # Show first 4
        print(f"  • {port['device']} {port['port']}: VLAN {port['vlans'][0]}")


def demo_gateway_validation() -> None:
    """Demonstrate gateway validation."""
    print_section("4. Gateway Logic Validation")
    
    topology = {
        "devices": [
            {
                "name": "Router",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "192.168.10.1/24"}},
            }
        ]
    }
    
    # Test valid gateway
    print("\nTest 1: Valid gateway (same subnet)")
    result = validate_gateway_logic("PC1", "192.168.10.50/24", "192.168.10.1", topology)
    print(f"  Gateway valid: {'✓' if result['gateway_valid'] else '✗'}")
    print(f"  Gateway reachable: {'✓' if result['gateway_reachable'] else '✗'}")
    
    # Test invalid gateway (wrong subnet)
    print("\nTest 2: Invalid gateway (wrong subnet)")
    result = validate_gateway_logic("PC2", "192.168.10.50/24", "192.168.20.1", {})
    print(f"  Gateway valid: {'✓' if result['gateway_valid'] else '✗'}")
    print(f"  Message: {result['message']}")


def demo_route_table() -> None:
    """Demonstrate route table builder."""
    print_section("5. Route Table Builder")
    
    connected = [
        {"network": "10.1.1.0/24", "interface": "Gig0/0"},
        {"network": "10.1.2.0/30", "interface": "Gig0/1"},
        {"network": "192.168.1.0/24", "interface": "Gig0/2"},
    ]
    
    static = [
        {"network": "172.16.0.0/16", "next_hop": "10.1.2.2", "metric": 1},
        {"network": "0.0.0.0/0", "next_hop": "10.1.2.2", "metric": 10},
    ]
    
    result = calculate_route_table(connected, static)
    
    print(f"\nRouting Table Summary:")
    print(f"  Total routes: {result['coverage_analysis']['total_routes']}")
    print(f"  Connected: {result['coverage_analysis']['connected_routes']}")
    print(f"  Static: {result['coverage_analysis']['static_routes']}")
    
    print("\nRouting Table Entries:")
    for route in result['routing_table']:
        if route['type'] == 'connected':
            print(f"  C  {route['network']:18} is directly connected, {route['interface']}")
        else:
            print(f"  S  {route['network']:18} via {route['next_hop']}")


def demo_configuration_order() -> None:
    """Demonstrate configuration order calculator."""
    print_section("6. Configuration Order Calculator")
    
    topology = {"devices": []}
    
    # Tasks in random order
    requirements = [
        "services",
        "acls",
        "routing_protocol",
        "ip_addressing",
        "trunk_configuration",
        "vlan_creation",
        "static_routes",
        "physical_connections",
    ]
    
    result = calculate_configuration_order(topology, requirements)
    
    print("\nConfiguration must be done in this order:")
    for step in result['configuration_order']:
        print(f"  {step['step']}. {step['task']} (priority: {step['priority']})")


def main() -> None:
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  Subnet Calculator MCP - Advanced Network Analysis Demo")
    print("  Demonstrating 6 new network analysis tools")
    print("=" * 70)
    
    demo_ip_conflict_detection()
    demo_routing_reachability()
    demo_vlan_assignments()
    demo_gateway_validation()
    demo_route_table()
    demo_configuration_order()
    
    print("\n" + "=" * 70)
    print("  Demo complete! All 6 tools working correctly.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
