# simplemem-mcp

A Model Context Protocol (MCP) server for memory management, using [simplemem-api](https://github.com/venetanji/simplemem-api) as the backend. This server provides tools for storing, retrieving, listing, searching, and deleting memories through the MCP interface.

## Features

- 🔧 **MCP Tools**: Store, retrieve, list, search, and delete memories
- 🚀 **FastMCP**: Built with FastMCP for high-performance MCP server implementation
- 📦 **uvx Ready**: Designed to run with `uvx` for easy installation and execution
- ⚙️ **Configurable**: Support for custom API endpoints via CLI arguments or environment variables
- 🏠 **Localhost Default**: Pre-configured to work with local simplemem-api instance

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) installed (for `uvx` command)
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

## Available Tools

The MCP server provides the following tools:

### store_memory
Store a memory item with a unique key.

**Parameters:**
- `key` (string): Unique identifier for the memory
- `value` (string): The content to store
- `metadata` (object, optional): Additional metadata

### retrieve_memory
Retrieve a memory item by its key.

**Parameters:**
- `key` (string): The unique identifier of the memory

### list_memories
List all stored memories with pagination support.

**Parameters:**
- `limit` (integer, default: 100): Maximum number of memories to return
- `offset` (integer, default: 0): Number of memories to skip

### search_memories
Search memories by query string.

**Parameters:**
- `query` (string): Search query
- `limit` (integer, default: 10): Maximum number of results

### delete_memory
Delete a memory item by its key.

**Parameters:**
- `key` (string): The unique identifier of the memory to delete

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
