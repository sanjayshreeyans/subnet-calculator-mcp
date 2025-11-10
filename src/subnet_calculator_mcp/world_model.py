"""Network world model using graph theory for topology analysis."""

from __future__ import annotations

import ipaddress
from typing import Any, Dict, Optional

import networkx as nx


class NetworkGraph:
    """Graph-based network topology model for advanced analysis."""

    def __init__(self, topology_data: Dict[str, Any]) -> None:
        """
        Initialize the network graph from topology data.

        Args:
            topology_data: Dict with 'devices' and 'links' keys
        """
        self.graph: nx.Graph = nx.Graph()
        self.device_data: Dict[str, Dict[str, Any]] = {}
        self._build_graph(topology_data)

    def _build_graph(self, topology: Dict[str, Any]) -> None:
        """Build the networkx graph from topology specification."""
        # 1. Add all devices as nodes with their attributes
        for device in topology.get("devices", []):
            device_name = device["name"]
            self.graph.add_node(device_name, **device)
            self.device_data[device_name] = device

        # 2. Add all links as edges
        for link in topology.get("links", []):
            source = link["source_device"]
            target = link["target_device"]
            edge_key = f"{link['source_port']}-{link['target_port']}"

            self.graph.add_edge(
                source,
                target,
                key=edge_key,
                source_port=link["source_port"],
                target_port=link["target_port"],
                **link.get("attributes", {}),
            )

    def find_l3_path(self, source_ip: str, dest_ip: str) -> Dict[str, Any]:
        """
        Find Layer 3 routing path between two IP addresses.

        Uses Dijkstra's shortest path algorithm to simulate OSPF-style routing.

        Args:
            source_ip: Source IP address (can include /prefix)
            dest_ip: Destination IP address (can include /prefix)

        Returns:
            Dict with reachable status, path, and hop information
        """
        # 1. Find source and destination nodes based on IP addresses
        src_node = self._find_node_by_ip(source_ip)
        dst_node = self._find_node_by_ip(dest_ip)

        if not src_node:
            return {
                "reachable": False,
                "path": [],
                "hops": 0,
                "error": f"Source IP {source_ip} not found in topology",
            }

        if not dst_node:
            return {
                "reachable": False,
                "path": [],
                "hops": 0,
                "error": f"Destination IP {dest_ip} not found in topology",
            }

        # Check if source and destination are the same device
        if src_node == dst_node:
            return {
                "reachable": True,
                "path": [src_node],
                "hops": 0,
                "message": "Source and destination on same device",
            }

        # 2. Use Dijkstra's algorithm for shortest path
        try:
            path = nx.shortest_path(self.graph, src_node, dst_node)
            detailed_path = []

            for i, node in enumerate(path):
                hop_info: Dict[str, Any] = {
                    "hop": i + 1,
                    "device": node,
                    "type": self.device_data[node].get("type", "unknown"),
                }

                # Add interface info for this hop
                interfaces = self.device_data[node].get("interfaces", {})
                if interfaces:
                    hop_info["interfaces"] = list(interfaces.keys())

                detailed_path.append(hop_info)

            return {
                "reachable": True,
                "path": detailed_path,
                "hops": len(path) - 1,
                "message": f"Path found with {len(path) - 1} hop(s)",
            }

        except nx.NetworkXNoPath:
            return {
                "reachable": False,
                "path": [],
                "hops": 0,
                "error": "No physical path exists between devices",
            }

        except nx.NodeNotFound as e:
            return {
                "reachable": False,
                "path": [],
                "hops": 0,
                "error": f"Node not found in graph: {str(e)}",
            }

    def _find_node_by_ip(self, ip_str: str) -> Optional[str]:
        """
        Find which device owns a given IP address.

        Args:
            ip_str: IP address string (can include /prefix notation)

        Returns:
            Device name or None if not found
        """
        try:
            # Parse IP, handling both "10.0.0.1" and "10.0.0.1/24" formats
            if "/" in ip_str:
                target_ip = ipaddress.IPv4Interface(ip_str).ip
            else:
                target_ip = ipaddress.IPv4Address(ip_str)

            # Search through all devices and their interfaces
            for node, data in self.graph.nodes(data=True):
                interfaces = data.get("interfaces", {})
                for iface_config in interfaces.values():
                    if "ip" in iface_config:
                        iface_ip_str = iface_config["ip"]
                        try:
                            # Handle both formats
                            if "/" in iface_ip_str:
                                iface_ip = ipaddress.IPv4Interface(iface_ip_str).ip
                            else:
                                iface_ip = ipaddress.IPv4Address(iface_ip_str)

                            if iface_ip == target_ip:
                                # Explicitly type node as str to avoid no-any-return
                                node_str: str = str(node)
                                return node_str
                        except (ValueError, ipaddress.AddressValueError):
                            continue

        except (ValueError, ipaddress.AddressValueError):
            pass

        return None

    def detect_loops(self) -> Dict[str, Any]:
        """
        Detect Layer 2 loops in the network topology.

        Returns:
            Dict with loop detection results
        """
        cycles = list(nx.simple_cycles(self.graph.to_directed()))

        if not cycles:
            return {
                "has_loops": False,
                "loops": [],
                "message": "No loops detected in topology",
            }

        loop_details = []
        for cycle in cycles:
            loop_details.append(
                {
                    "devices": cycle,
                    "length": len(cycle),
                }
            )

        return {
            "has_loops": True,
            "loops": loop_details,
            "message": f"Found {len(cycles)} loop(s) in topology",
        }

    def check_connectivity(self) -> Dict[str, Any]:
        """
        Check if the network topology is fully connected.

        Returns:
            Dict with connectivity analysis
        """
        is_connected = nx.is_connected(self.graph)
        num_components = nx.number_connected_components(self.graph)

        if is_connected:
            return {
                "is_connected": True,
                "components": 1,
                "message": "Network is fully connected",
            }

        # Find isolated components
        components = list(nx.connected_components(self.graph))
        component_details = [
            {"devices": list(comp), "size": len(comp)} for comp in components
        ]

        return {
            "is_connected": False,
            "components": num_components,
            "component_details": component_details,
            "message": f"Network has {num_components} isolated segment(s)",
        }

    def get_device_neighbors(self, device_name: str) -> Dict[str, Any]:
        """
        Get all directly connected neighbors of a device.

        Args:
            device_name: Name of the device

        Returns:
            Dict with neighbor information
        """
        if device_name not in self.graph:
            return {
                "device": device_name,
                "neighbors": [],
                "error": "Device not found in topology",
            }

        neighbors = list(self.graph.neighbors(device_name))

        neighbor_details = []
        for neighbor in neighbors:
            # Get edge data for connection details
            edge_data = self.graph.get_edge_data(device_name, neighbor)
            neighbor_details.append(
                {
                    "device": neighbor,
                    "type": self.device_data[neighbor].get("type", "unknown"),
                    "connection": edge_data,
                }
            )

        return {
            "device": device_name,
            "neighbors": neighbor_details,
            "neighbor_count": len(neighbors),
        }
