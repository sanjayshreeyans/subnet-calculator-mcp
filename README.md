# Subnet Calculator MCP Server

[![CI](https://github.com/sanjayshreeyans/subnet-calculator-mcp/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sanjayshreeyans/subnet-calculator-mcp/actions/workflows/ci.yml)
`subnet-calculator-mcp` is a production-ready [Model Context Protocol](https://modelcontextprotocol.io/) server that delivers reliable IPv4 subnet planning utilities to LLM-powered assistants. It eliminates tedious manual math by exposing fast, well-tested tools for subnet sizing, wildcard mask generation, gateway selection, and host validation.

## Why Use This Server?

- 🔢 Convert host requirements into accurate subnet masks and CIDR prefixes
- 🌐 Produce Cisco-friendly OSPF wildcard masks and network statements
- ✅ Verify whether an IP belongs to a subnet, including gateway hints and address position
- 🔄 Reverse-calculations from dotted masks or find the Nth usable address instantly
- ⚙️ Built on the official Python MCP SDK with thorough type hints, validation, and tests

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
