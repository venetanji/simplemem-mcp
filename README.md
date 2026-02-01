# simplemem-mcp

A Model Context Protocol (MCP) server that provides a seamless interface to [simplemem-api](https://github.com/venetanji/simplemem-api). This MCP server exposes tools that map directly to the simplemem-api endpoints, enabling AI assistants to store and query conversational memories through the MCP protocol.

## Features

- 🔧 **MCP Tools**: Health, dialogue ingestion, query, retrieve, delete_memory, stats, and clear
- 🚀 **FastMCP**: Built with FastMCP for high-performance MCP server implementation
- 📦 **uvx Ready**: Designed to run with `uvx` for easy installation and execution
- ⚙️ **Configurable**: Support for custom API endpoints via CLI arguments or environment variables
- 🏠 **Localhost Default**: Pre-configured to work with local simplemem-api instance at `http://localhost:8000`

## API Backend

This MCP server is a client that connects to [simplemem-api](https://github.com/venetanji/simplemem-api), which provides the actual memory storage and retrieval functionality. The simplemem-mcp server acts as a bridge, exposing simplemem-api capabilities through the Model Context Protocol.

**Important:** You must have a running instance of simplemem-api before using this MCP server. By default, simplemem-mcp expects the API to be available at `http://localhost:8000`, but this can be configured to point to any simplemem-api instance.

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) installed (for `uvx` command). Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
- **Required:** A running instance of [simplemem-api](https://github.com/venetanji/simplemem-api) (see [simplemem-api documentation](https://github.com/venetanji/simplemem-api) for setup instructions)

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
# Alias supported (matches simplemem-api docs)
export SIMPLEMEM_API_URL=http://your-api-host:8080
uvx simplemem-mcp
```

### Install as a uv tool (recommended for servers)

If you want an installed `simplemem-mcp` executable on your PATH (instead of running via `uvx` each time), use `uv tool install`:

```bash
uv tool install git+https://github.com/venetanji/simplemem-mcp.git

# Ensure uv's tool bin dir is on PATH
uv tool update-shell

# Now run it like a normal CLI
simplemem-mcp --api-endpoint http://localhost:8000

# Or use HTTP transports
simplemem-mcp --api-endpoint http://localhost:8000 --transport streamable-http --host 127.0.0.1 --port 3333
```

To upgrade later:

```bash
uv tool upgrade simplemem-mcp
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

The simplemem-api endpoint can be configured in three ways (in order of priority):

1. **Command-line argument**: `--api-endpoint`
2. **Environment variable**: `SIMPLEMEM_API_ENDPOINT` (or `SIMPLEMEM_API_URL`)
3. **Default**: `http://localhost:8000` (assumes simplemem-api is running locally on the default port)


### Examples

```bash
# Using CLI argument
uvx simplemem-mcp --api-endpoint http://192.168.1.100:8000

# Using environment variable
export SIMPLEMEM_API_ENDPOINT=http://api.example.com:8000
# Alias supported
export SIMPLEMEM_API_URL=http://api.example.com:8000
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

The MCP server provides the following tools, which map 1:1 to the [simplemem-api](https://github.com/venetanji/simplemem-api) endpoints:

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

#### delete_memory
Delete a specific memory entry by its ID.

**Parameters:**
- `entry_id` (string): The unique identifier of the memory entry to delete

**Returns:**
A success message if the entry was deleted, or an error message if something went wrong.

#### clear
Clear all entries (requires explicit confirmation).

**Parameters:**
- `confirmation` (boolean, default: false): Must be true to proceed

**Notes:**

- `dialogue`/`query` will report a helpful message if the upstream API is not initialized (`/health` indicates `simplemem_initialized=false`).
- Use `delete_memory` to remove individual memories by their `entry_id`.
- Use `clear` with `confirmation=true` to wipe all entries.

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
1. **Ensure simplemem-api is running**: The default configuration expects simplemem-api at `http://localhost:8000`. See the [simplemem-api repository](https://github.com/venetanji/simplemem-api) for setup and running instructions.
2. **Check the API endpoint URL is correct**: Verify your endpoint configuration matches where simplemem-api is actually running.
3. **Verify firewall settings allow the connection**: Ensure network access between simplemem-mcp and simplemem-api is not blocked.

### Port Conflicts

If the default port 8000 is in use by another service:
1. Configure simplemem-api to run on a different port (see [simplemem-api documentation](https://github.com/venetanji/simplemem-api))
2. Update the endpoint when starting simplemem-mcp:

```bash
# If simplemem-api is running on port 8080
uvx simplemem-mcp --api-endpoint http://localhost:8080
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Specify your license here]

## Related Projects

- **[simplemem-api](https://github.com/venetanji/simplemem-api)** - The backend API server that provides the memory storage and retrieval functionality. Required for simplemem-mcp to function.
