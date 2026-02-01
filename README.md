# simplemem-mcp

A Model Context Protocol (MCP) server for [simplemem-api](https://github.com/venetanji/simplemem-api). This server exposes MCP tools that map directly to the simplemem-api endpoints.

## Features

- 🔧 **MCP Tools**: Health, dialogue ingestion, query, retrieve, stats, and clear
- 🚀 **FastMCP**: Built with FastMCP for high-performance MCP server implementation
- 📦 **uvx Ready**: Designed to run with `uvx` for easy installation and execution
- ⚙️ **Configurable**: Support for custom API endpoints via CLI arguments or environment variables
- 🏠 **Localhost Default**: Pre-configured to work with local simplemem-api instance

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) installed (for `uvx` command). Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
- A running instance of [simplemem-api](https://github.com/venetanji/simplemem-api)

## Installation

### Quick Start with uvx

The easiest way to run simplemem-mcp is using `uvx`:

```bash
# Run with default localhost endpoint (http://localhost:8000)
uvx simplemem-mcp

# Run with custom API endpoint
uvx simplemem-mcp --api-endpoint http://your-api-host:8080

# Or use environment variable
export SIMPLEMEM_API_ENDPOINT=http://your-api-host:8080
uvx simplemem-mcp
```

### Development Installation

For development or local modifications:

```bash
# Clone the repository
git clone https://github.com/venetanji/simplemem-mcp.git
cd simplemem-mcp

# Install in development mode
pip install -e .

# Run the server
simplemem-mcp
```

## Configuration

The server can be configured in three ways (in order of priority):

1. **Command-line argument**: `--api-endpoint`
2. **Environment variable**: `SIMPLEMEM_API_ENDPOINT`
3. **Default**: `http://localhost:8000`

### Examples

```bash
# Using CLI argument
uvx simplemem-mcp --api-endpoint http://192.168.1.100:8000

# Using environment variable
export SIMPLEMEM_API_ENDPOINT=http://api.example.com:8000
uvx simplemem-mcp

# Default (localhost)
uvx simplemem-mcp
```

## Transports

By default, `simplemem-mcp` runs over the standard MCP **stdio** transport (suitable for most desktop MCP clients).

FastMCP also supports HTTP-based transports, which you can enable via CLI flags:

- `--transport streamable-http`: HTTP streaming transport
- `--transport sse`: Server-Sent Events (SSE)

### Examples

```bash
# Default: stdio
uvx simplemem-mcp

# Streamable HTTP
uvx simplemem-mcp --transport streamable-http --host 127.0.0.1 --port 3333

# SSE
uvx simplemem-mcp --transport sse --host 127.0.0.1 --port 3333
```

Notes:

- `--host`, `--port`, and `--path` only apply to HTTP transports.
- If you're using `timeout` while testing, prefer `timeout -s INT 2 ...` so the server can shut down cleanly.

## Available Tools

The MCP server provides the following tools:

These map 1:1 to the upstream `simplemem-api` endpoints.

#### health
Check API health and initialization status.

#### dialogue
Add a dialogue entry.

**Parameters:**
- `speaker` (string): Speaker identifier
- `content` (string): Content to store
- `timestamp` (string, optional): Timestamp string

**Important:**

- After adding all dialogue entries for a session/batch, call `finalize` once to consolidate memories.

#### query
Ask a question and get an answer.

**Parameters:**
- `query` (string): Query text

#### retrieve
Retrieve recent entries.

**Parameters:**
- `limit` (integer, default: 100): Maximum number of entries to return

#### stats
Get memory statistics.

#### finalize
Consolidate memories after dialogue ingestion.

Recommended pattern:

1. Call `dialogue` one or more times
2. Call `finalize` once

#### clear
Clear all entries (requires explicit confirmation).

**Parameters:**
- `confirmation` (boolean, default: false): Must be true to proceed

Notes:

- `dialogue`/`query` will report a helpful message if the upstream API is not initialized (`/health` indicates `simplemem_initialized=false`).
- The upstream API does not provide a delete-by-id endpoint; use `clear` with `confirmation=true` to wipe all entries.

## Usage with MCP Clients

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "simplemem": {
      "command": "uvx",
      "args": ["simplemem-mcp"],
      "env": {
        "SIMPLEMEM_API_ENDPOINT": "http://localhost:8000"
      }
    }
  }
}
```

For custom endpoints:

```json
{
  "mcpServers": {
    "simplemem": {
      "command": "uvx",
      "args": ["simplemem-mcp", "--api-endpoint", "http://your-api-host:8080"]
    }
  }
}
```

### Other MCP Clients

Consult your MCP client's documentation for how to add custom servers. Generally, you'll need to:
1. Specify the command: `uvx`
2. Provide arguments: `["simplemem-mcp"]` or `["simplemem-mcp", "--api-endpoint", "YOUR_URL"]`

## Development

### Project Structure

```
simplemem-mcp/
├── src/
│   └── simplemem_mcp/
│       ├── __init__.py
│       ├── __main__.py      # CLI entrypoint
│       └── server.py         # MCP server implementation
├── pyproject.toml            # Project configuration
├── README.md
└── .gitignore
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests (when available)
pytest
```

### Building

```bash
# Build the package
python -m build
```

## Troubleshooting

### Connection Issues

If you get connection errors:
1. Ensure simplemem-api is running and accessible
2. Check the API endpoint URL is correct
3. Verify firewall settings allow the connection

### Port Conflicts

If the default port 8000 is in use, configure simplemem-api to use a different port and update the endpoint:

```bash
uvx simplemem-mcp --api-endpoint http://localhost:8080
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Specify your license here]

## Related Projects

- [simplemem-api](https://github.com/venetanji/simplemem-api) - The backend API server
