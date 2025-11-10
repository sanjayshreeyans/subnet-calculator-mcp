# Subnet Calculator MCP Server

[![CI](https://github.com/sanjayshreeyans/subnet-calculator-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjayshreeyans/subnet-calculator-mcp/actions/workflows/ci.yml)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/subnet-calculator-mcp?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/subnet-calculator-mcp)
`subnet-calculator-mcp` is a production-ready [Model Context Protocol](https://modelcontextprotocol.io/) server that delivers reliable IPv4 subnet planning utilities to LLM-powered assistants. It eliminates tedious manual math by exposing fast, well-tested tools for subnet sizing, wildcard mask generation, gateway selection, and host validation.

## Why Use This Server?

**Basic Subnet Calculations:**
- 🔢 Convert host requirements into accurate subnet masks and CIDR prefixes
- 🌐 Produce Cisco-friendly OSPF wildcard masks and network statements
- ✅ Verify whether an IP belongs to a subnet, including gateway hints and address position
- 🔄 Reverse-calculations from dotted masks or find the Nth usable address instantly

**Advanced Network Analysis (NEW):**
- 🔍 Detect IP conflicts and subnet violations across network configurations
- 🛣️ Validate Layer 3 routing reachability with graph-based path simulation
- 🔀 Calculate VLAN trunk/access port assignments from topology
- 🚪 Validate gateway configurations and Layer 2 reachability
- 📋 Build and analyze routing tables from connected and static routes
- 📊 Determine optimal configuration order based on task dependencies

**Architecture:**
- ⚙️ Built on the official Python MCP SDK with thorough type hints, validation, and tests
- 🧮 Uses `networkx` for graph-based topology analysis and shortest-path routing simulation
- 🎯 Perfect for network configuration and troubleshooting scenarios

## Install & Run

The package is published on PyPI: <https://pypi.org/project/subnet-calculator-mcp/>

### Install with pip

```bash
pip install subnet-calculator-mcp
python -m subnet_calculator_mcp.server
```

### Run instantly (no install)

```bash
uvx subnet-calculator-mcp
```

### Install as a reusable CLI

```bash
uv tool install subnet-calculator-mcp
# later
subnet-calculator-mcp
```

## Client Configuration

### Claude Desktop / Claude for Windows

Add the server to `claude_desktop_config.json`.

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "subnet-calculator": {
      "command": "uvx",
      "args": ["subnet-calculator-mcp"]
    }
  }
}
```

If you installed via `uv tool install` or `pip`, change the command to `"subnet-calculator-mcp"` and omit `args`.

### Generic `mcp.json`

Many editors (Cursor, Windsurf, etc.) use an `mcp.json` file. Add the following entry:

```json
{
  "subnet-calculator": {
    "command": "uvx",
    "args": ["subnet-calculator-mcp"],
    "env": {}
  }
}
```

Set `command` to `"subnet-calculator-mcp"` if the binary is installed globally.

## Tool Reference

### `calculate_subnet`

- **Inputs**: `network_base` (IPv4 address), `hosts_needed` (int), optional `return_format` (`"detailed"` or `"simple"`).
- **Returns**: CIDR prefix, dotted mask, wildcard mask, usable range, broadcast, binary representations, total/usable host counts.
- **Use it for**: deriving the smallest subnet that can host the requested number of usable addresses.

### `calculate_wildcard_mask`

- **Inputs**: `ip_address` (any IP in the subnet), `cidr_prefix` (0–32), optional `include_ospf_command` (bool).
- **Returns**: network address, mask, wildcard mask, binary wildcard string, and optional `network ... area 0` statement.
- **Use it for**: creating OSPF configurations or ACLs that rely on wildcard masks.

### `validate_ip_in_subnet`

- **Inputs**: `ip_address`, `network` (CIDR string), optional `return_gateway` (bool).
- **Returns**: membership flag, mask, prefix, network/broadcast flags, usability, likely gateway, position index, and remaining usable addresses.
- **Use it for**: quickly verifying assignments and identifying first-hop router addresses.

### `calculate_subnet_from_mask`

- **Inputs**: `ip_address`, `subnet_mask` (dotted decimal).
- **Returns**: network boundary, prefix, wildcard mask, usable range, broadcast, and host counts.
- **Use it for**: analysing legacy configurations that provide dotted masks instead of CIDR notation.

### `get_nth_usable_ip`

- **Inputs**: `network` (CIDR string), `position` (1-based index).
- **Returns**: IP address at that position, whether it is last usable, total usable hosts, and associated network address.
- **Use it for**: allocating deterministic host positions (first server, second router, etc.).

### `detect_ip_conflicts`

- **Inputs**: `ip_assignments` (list of dicts with `device`, `interface`, `ip`, `mask`).
- **Returns**: list of IP conflicts (duplicate assignments) and subnet violations (network/broadcast address usage).
- **Use it for**: validating network configurations to prevent IP addressing conflicts in network deployments.

### `validate_routing_reachability`

- **Inputs**: `topology` (complete network topology with devices and links), `source_ip`, `destination_ip`.
- **Returns**: reachability status, hop-by-hop path trace, and connectivity analysis using graph-based routing simulation.
- **Use it for**: determining if Layer 3 connectivity exists between endpoints, simulating OSPF-style shortest path routing.

### `calculate_vlan_assignments`

- **Inputs**: `topology` (network devices and connections), `vlan_policy` (VLAN configuration rules).
- **Returns**: port assignments with trunk/access mode recommendations and VLAN propagation analysis.
- **Use it for**: designing VLAN configurations for switches based on network topology.

### `validate_gateway_logic`

- **Inputs**: `device` (device name), `ip` (device IP with mask), `gateway` (gateway IP), `topology`.
- **Returns**: gateway validity and reachability status on the same Layer 2 segment.
- **Use it for**: verifying default gateway configurations are in the correct subnet and accessible.

### `calculate_route_table`

- **Inputs**: `directly_connected` (list of connected networks), `static_routes` (list of static route configs).
- **Returns**: complete routing table with coverage analysis and next-hop validation.
- **Use it for**: building and validating router routing tables from connected and static routes.

### `calculate_configuration_order`

- **Inputs**: `topology`, `requirements` (list of configuration task names).
- **Returns**: dependency-sorted list of configuration steps with priorities.
- **Use it for**: determining the correct order to configure network devices (VLANs before IPs, IPs before routing, etc.).

Example invocation:

```json
{
  "tool": "calculate_subnet",
  "arguments": {
    "network_base": "172.16.0.16",
    "hosts_needed": 14
  }
}
```

```json
{
  "tool": "validate_routing_reachability",
  "arguments": {
    "topology": {
      "devices": [
        {"name": "R1", "type": "router", "interfaces": {"Gig0/0": {"ip": "10.1.1.1/24"}}, "static_routes": []},
        {"name": "R2", "type": "router", "interfaces": {"Gig0/0": {"ip": "10.2.2.1/24"}}, "static_routes": []}
      ],
      "links": [
        {"source_device": "R1", "source_port": "Gig0/1", "target_device": "R2", "target_port": "Gig0/1", "attributes": {}}
      ]
    },
    "source_ip": "10.1.1.1",
    "destination_ip": "10.2.2.1"
  }
}
```

## Development Workflow

```bash
git clone https://github.com/sanjayshreeyans/subnet-calculator-mcp.git
cd subnet-calculator-mcp

# Install dependencies (dev group includes pytest, mypy, ruff, black)
uv sync --group dev

# Run the automated test suite
uv run pytest

# Type-check, lint, and format
uv run mypy src
uv run ruff check src tests
uv run black --check src tests

# Build distribution artifacts
uv build
```

## License

MIT License – see `LICENSE` for details.
