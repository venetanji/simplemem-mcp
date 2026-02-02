# GitHub Copilot Instructions for simplemem-mcp

## Project Overview

simplemem-mcp is a Model Context Protocol (MCP) server that provides memory management tools by interfacing with simplemem-api. The project uses FastMCP and is designed to run with `uvx` for easy execution.

## Tooling

- This project uses `uv` for dependency management and running commands.
- Prefer `uv run ...` for Python commands (tests, scripts, linters).
- Prefer `uvx simplemem-mcp ...` for running the installed CLI.

## Architecture

- **MCP Server**: Built with FastMCP framework
- **Backend**: Connects to simplemem-api (default: localhost:8000)
- **Language**: Python 3.10+
- **Package Manager**: Uses `uv` and `uvx` for execution

## Key Components

### Server Implementation (`src/simplemem_mcp/server.py`)
- `SimplememAPI`: HTTP client for simplemem-api
- `create_server()`: Factory function that creates and configures the FastMCP server
- MCP Tools: store_memory, retrieve_memory, list_memories, search_memories, delete_memory

### Entry Point (`src/simplemem_mcp/__main__.py`)
- CLI argument parsing
- Environment variable configuration
- Server initialization and startup

## Configuration

The server supports three configuration methods (in priority order):
1. `--api-endpoint` CLI argument
2. `SIMPLEMEM_API_ENDPOINT` environment variable
3. Default: `http://localhost:8000`

## Coding Standards

### Python Style
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return types
- Include docstrings for all public functions and classes
- Keep functions focused and single-purpose

### Error Handling
- Catch specific exceptions rather than broad catches
- Provide meaningful error messages to users
- Log errors appropriately for debugging

### MCP Tools
- Each tool should have clear docstrings
- Parameters should be well-documented with types
- Return human-readable messages, not raw JSON
- Handle API errors gracefully

### Dependencies
- Keep dependencies minimal
- Use httpx for HTTP requests (async-compatible)
- FastMCP is the core framework

## Development Workflow

### Adding New Tools
1. Add method to `SimplememAPI` class for API interaction
2. Create corresponding MCP tool in `create_server()`
3. Add comprehensive docstring with parameter descriptions
4. Handle errors and return user-friendly messages
5. Update README with tool documentation

### Testing
- Test with local simplemem-api instance
- Verify default localhost configuration
- Test custom endpoint configuration
- Validate error handling for API failures

Run tests via `uv`:

`uv run pytest`

### Common Patterns

#### API Client Method
```python
async def api_method(self, param: str) -> dict:
    """Brief description"""
    response = self.client.get(f"{self.base_url}/endpoint")
    response.raise_for_status()
    return response.json()
```

#### MCP Tool
```python
@mcp.tool()
async def tool_name(param: str) -> str:
    """
    Tool description.
    
    Args:
        param: Parameter description
    
    Returns:
        Human-readable result message
    """
    try:
        result = await api.method(param)
        return f"Success message"
    except Exception as e:
        return f"Error message: {str(e)}"
```

## File Organization

```
simplemem-mcp/
├── src/simplemem_mcp/
│   ├── __init__.py       # Package metadata
│   ├── __main__.py       # CLI entry point
│   └── server.py         # MCP server and API client
├── pyproject.toml        # Project configuration
├── README.md             # User documentation
└── .gitignore           # Git ignore rules
```

## Important Notes

- Always use async/await for API operations
- Default to localhost unless configured otherwise
- Keep error messages user-friendly
- FastMCP handles the MCP protocol details
- The server runs via `mcp.run()` which starts the stdio transport

## When Making Changes

1. **Preserve Compatibility**: Don't break existing tool interfaces
2. **Test Configuration**: Verify all three configuration methods work
3. **Update Documentation**: Keep README in sync with code changes
4. **Handle Errors**: Gracefully handle API unavailability
5. **Follow Patterns**: Match existing code style and structure

## Common Tasks

### Adding a New Memory Operation
1. Check if simplemem-api supports the operation
2. Add method to `SimplememAPI` class
3. Add corresponding tool decorator in `create_server()`
4. Document in README under "Available Tools"

### Changing Configuration
1. Update `DEFAULT_API_ENDPOINT` if needed
2. Modify argument parser in `__main__.py`
3. Update README configuration section
4. Test all configuration methods

### Debugging
- Server logs to stderr
- Check API endpoint is accessible
- Verify simplemem-api is running
- Test with `uvx simplemem-mcp --api-endpoint http://localhost:8000`
