"""Tests for the network world model using graph theory."""

from __future__ import annotations


from subnet_calculator_mcp.world_model import NetworkGraph


def test_network_graph_initialization() -> None:
    """NetworkGraph should initialize with valid topology data."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "10.0.1.1/24"}},
                "static_routes": [],
            },
            {
                "name": "Router2",
                "type": "router",
                "interfaces": {"Gig0/1": {"ip": "10.0.2.1/24"}},
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
            }
        ],
    }

    net = NetworkGraph(topology)
    assert net.graph.number_of_nodes() == 2
    assert net.graph.number_of_edges() == 1


def test_find_l3_path_simple() -> None:
    """Should find simple path between two connected devices."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "10.0.1.1/24"}},
                "static_routes": [],
            },
            {
                "name": "Router2",
                "type": "router",
                "interfaces": {"Gig0/1": {"ip": "10.0.2.1/24"}},
                "static_routes": [],
            },
        ],
        "links": [
            {
                "source_device": "Router1",
                "source_port": "Gig0/1",
                "target_device": "Router2",
                "target_port": "Gig0/0",
                "attributes": {},
            }
        ],
    }

    net = NetworkGraph(topology)
    result = net.find_l3_path("10.0.1.1", "10.0.2.1")

    assert result["reachable"] is True
    assert result["hops"] == 1
    assert len(result["path"]) == 2
    assert result["path"][0]["device"] == "Router1"
    assert result["path"][1]["device"] == "Router2"


def test_find_l3_path_same_device() -> None:
    """Should handle source and destination on same device."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {
                    "Gig0/0": {"ip": "10.0.1.1/24"},
                    "Gig0/1": {"ip": "10.0.2.1/24"},
                },
                "static_routes": [],
            }
        ],
        "links": [],
    }

    net = NetworkGraph(topology)
    result = net.find_l3_path("10.0.1.1", "10.0.2.1")

    assert result["reachable"] is True
    assert result["hops"] == 0
    assert len(result["path"]) == 1


def test_find_l3_path_not_found() -> None:
    """Should report unreachable when no path exists."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "10.0.1.1/24"}},
                "static_routes": [],
            },
            {
                "name": "Router2",
                "type": "router",
                "interfaces": {"Gig0/1": {"ip": "10.0.2.1/24"}},
                "static_routes": [],
            },
        ],
        "links": [],  # No links = isolated devices
    }

    net = NetworkGraph(topology)
    result = net.find_l3_path("10.0.1.1", "10.0.2.1")

    assert result["reachable"] is False
    assert "No physical path" in result["error"]


def test_find_l3_path_ip_not_found() -> None:
    """Should report error when IP not found in topology."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "10.0.1.1/24"}},
                "static_routes": [],
            }
        ],
        "links": [],
    }

    net = NetworkGraph(topology)
    result = net.find_l3_path("10.0.1.1", "192.168.1.1")

    assert result["reachable"] is False
    assert "not found in topology" in result["error"]


def test_find_l3_path_multi_hop() -> None:
    """Should find path through multiple hops."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {"Gig0/0": {"ip": "10.0.1.1/24"}},
                "static_routes": [],
            },
            {
                "name": "Router2",
                "type": "router",
                "interfaces": {"Gig0/1": {"ip": "10.0.2.1/24"}},
                "static_routes": [],
            },
            {
                "name": "Router3",
                "type": "router",
                "interfaces": {"Gig0/2": {"ip": "10.0.3.1/24"}},
                "static_routes": [],
            },
        ],
        "links": [
            {
                "source_device": "Router1",
                "source_port": "Gig0/1",
                "target_device": "Router2",
                "target_port": "Gig0/0",
                "attributes": {},
            },
            {
                "source_device": "Router2",
                "source_port": "Gig0/2",
                "target_device": "Router3",
                "target_port": "Gig0/0",
                "attributes": {},
            },
        ],
    }

    net = NetworkGraph(topology)
    result = net.find_l3_path("10.0.1.1", "10.0.3.1")

    assert result["reachable"] is True
    assert result["hops"] == 2
    assert len(result["path"]) == 3


def test_check_connectivity_connected() -> None:
    """Should detect fully connected network."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {},
                "static_routes": [],
            },
            {
                "name": "Router2",
                "type": "router",
                "interfaces": {},
                "static_routes": [],
            },
        ],
        "links": [
            {
                "source_device": "Router1",
                "source_port": "Gig0/0",
                "target_device": "Router2",
                "target_port": "Gig0/0",
                "attributes": {},
            }
        ],
    }

    net = NetworkGraph(topology)
    result = net.check_connectivity()

    assert result["is_connected"] is True
    assert result["components"] == 1


def test_check_connectivity_disconnected() -> None:
    """Should detect isolated network segments."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {},
                "static_routes": [],
            },
            {
                "name": "Router2",
                "type": "router",
                "interfaces": {},
                "static_routes": [],
            },
        ],
        "links": [],  # No links
    }

    net = NetworkGraph(topology)
    result = net.check_connectivity()

    assert result["is_connected"] is False
    assert result["components"] == 2


def test_get_device_neighbors() -> None:
    """Should list all directly connected neighbors."""
    topology = {
        "devices": [
            {
                "name": "Router1",
                "type": "router",
                "interfaces": {},
                "static_routes": [],
            },
            {
                "name": "Switch1",
                "type": "switch",
                "interfaces": {},
                "static_routes": [],
            },
            {
                "name": "Switch2",
                "type": "switch",
                "interfaces": {},
                "static_routes": [],
            },
        ],
        "links": [
            {
                "source_device": "Router1",
                "source_port": "Gig0/0",
                "target_device": "Switch1",
                "target_port": "Gig0/1",
                "attributes": {},
            },
            {
                "source_device": "Router1",
                "source_port": "Gig0/1",
                "target_device": "Switch2",
                "target_port": "Gig0/1",
                "attributes": {},
            },
        ],
    }

    net = NetworkGraph(topology)
    result = net.get_device_neighbors("Router1")

    assert result["neighbor_count"] == 2
    assert len(result["neighbors"]) == 2
    neighbor_names = {n["device"] for n in result["neighbors"]}
    assert neighbor_names == {"Switch1", "Switch2"}


def test_get_device_neighbors_not_found() -> None:
    """Should handle device not in topology."""
    topology = {"devices": [], "links": []}

    net = NetworkGraph(topology)
    result = net.get_device_neighbors("NonExistent")

    assert "error" in result
    assert "not found" in result["error"]
