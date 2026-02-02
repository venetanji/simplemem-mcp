# simplemem-mcp

A Model Context Protocol (MCP) server that provides a seamless interface to [simplemem-api](https://github.com/venetanji/simplemem-api). This MCP server exposes tools that map directly to the simplemem-api endpoints, enabling AI assistants to store and query conversational memories through the MCP protocol.

## Features

- 🔧 **MCP Tools**: Health, dialogue ingestion, query, retrieve, delete_memory, stats, and clear
- 🚀 **FastMCP**: Built with FastMCP for high-performance MCP server implementation
- 🔐 **OAuth Authentication**: Secure OAuth 2.0 authentication for external AI clients (OpenAI, Claude, etc.)
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

## OAuth Authentication

simplemem-mcp includes built-in OAuth 2.0 authentication support for external AI clients. This allows secure integration with AI platforms like OpenAI, Claude, and other services that support OAuth authentication.

This project supports two common patterns:

- **Interactive “Sign in”** (Authorization Code + PKCE): used by ChatGPT Connectors and similar platforms.
- **Service-to-service** (Client Credentials): useful for scripts/agents that can store a `client_secret`.

### OAuth Client Management

#### Generate a New OAuth Client

Create OAuth credentials for an AI service or external client:

```bash
uvx simplemem-mcp oauth-generate-client --name openai --description "OpenAI integration"
```

This will output:
```
=== OAuth Client Generated ===
Client ID: smc_PI-Q2wGQCy8M3kiV3q_y_Q
Client Secret: Fz3ekjJ8sZf9iih6DKSqNjYCfPt9UpcxuQ5LpCwY79PZhKAa0LMmkRsRQT0I4Oi7
Name: openai
Description: OpenAI integration

IMPORTANT: Save the client secret securely. It will not be shown again.
```

**Important:** Save both the Client ID and Client Secret securely. The secret will not be shown again.

#### List Registered OAuth Clients

View all registered OAuth clients:

```bash
uvx simplemem-mcp oauth-list-clients
```

#### Revoke an OAuth Client

Revoke access for a specific client:

```bash
uvx simplemem-mcp oauth-revoke-client --client-id <client_id>
```

### Running the OAuth Server

There are two ways to serve OAuth endpoints:

1) **Recommended for ChatGPT / single public URL**: run the **combined** server so OAuth + MCP share one port.

2) Run a **dedicated OAuth server** (separate port) alongside your MCP server.

#### Option A: Combined OAuth + MCP server (single port)

This is the easiest way to deploy behind a single tunnel / one public URL.

```bash
# Combined server: OAuth endpoints + MCP endpoint on the same port
uvx simplemem-mcp \
  --transport streamable-http \
  --host 0.0.0.0 \
  --port 3333 \
  --oauth-required \
  --access-log
```

What you get:

- MCP endpoint: `http://<host>:3333/mcp`
- OAuth issuer + discovery: `http://<host>:3333/.well-known/oauth-authorization-server`
- Protected resource metadata: `http://<host>:3333/.well-known/oauth-protected-resource`
- Authorization endpoint (Sign in): `http://<host>:3333/oauth/authorize`
- Token endpoint: `http://<host>:3333/oauth/token`

Notes:

- The server also serves discovery endpoints under `/mcp/.well-known/*` because some clients probe those paths.
- `/mcp` (no trailing slash) is handled without redirects (important for some clients).

#### Option B: Dedicated OAuth server (separate port)

To enable OAuth authentication on a separate port, run the dedicated OAuth server alongside your MCP server:

```bash
# Run OAuth server (default: localhost:8080)
uvx simplemem-mcp oauth-server

# Run on a specific host and port (for public access)
uvx simplemem-mcp oauth-server --host 0.0.0.0 --port 8080
```

The OAuth server provides:
- **Authorization Endpoint**: `GET/POST /oauth/authorize` - Sign in via Authorization Code + PKCE
- **Token Endpoint**: `POST /oauth/token` - Obtain access tokens (client credentials and authorization code flows)
- **Info Endpoint**: `GET /oauth/info` - Get information about the current token
- **Health Check**: `GET /health` - Check server status

### OAuth Flow (Authorization Code + PKCE)

This is the flow ChatGPT Connectors typically use:

1. Client calls the MCP endpoint (e.g. `/mcp`) and receives `401` with `WWW-Authenticate: Bearer ... resource_metadata=...`
2. Client fetches `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server`
3. Client redirects the user to `/oauth/authorize` (consent screen)
4. Server redirects back to the client’s `redirect_uri` with `code`
5. Client exchanges `code` + `code_verifier` at `/oauth/token`
6. Client calls MCP endpoints with `Authorization: Bearer <access_token>`

Redirect URI policy:

- For local testing you can set `SIMPLEMEM_OAUTH_ALLOW_ANY_REDIRECT_URI=1`.
- For production set `SIMPLEMEM_OAUTH_ALLOWED_REDIRECT_URIS` to a comma-separated allowlist.
- If neither is set, a small default allowlist is used that includes the ChatGPT connector redirect endpoints.

### OAuth Flow (Client Credentials)

1. **Generate OAuth Client**: Create client credentials using `oauth-generate-client`
2. **Request Access Token**: External clients POST to `/oauth/token` with credentials
3. **Use Access Token**: Include the token in requests as `Authorization: Bearer <token>`

#### Example: Obtaining an Access Token

```bash
curl -X POST http://localhost:8080/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "smc_PI-Q2wGQCy8M3kiV3q_y_Q",
    "client_secret": "Fz3ekjJ8sZf9iih6DKSqNjYCfPt9UpcxuQ5LpCwY79PZhKAa0LMmkRsRQT0I4Oi7"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### Example: Using the Access Token

```bash
curl -X GET http://localhost:8080/oauth/info \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Integrating with External AI Clients

#### OpenAI

Configure your OpenAI application to use OAuth authentication:
1. Generate client credentials for OpenAI: `uvx simplemem-mcp oauth-generate-client --name openai`
2. Configure your OpenAI application with the client ID and secret
3. Use the token endpoint to obtain access tokens before making requests

#### Claude

Configure Claude to use OAuth authentication:
1. Generate client credentials for Claude: `uvx simplemem-mcp oauth-generate-client --name claude`
2. Configure Claude's API settings with your OAuth endpoint
3. Claude will automatically handle token acquisition and renewal

#### Custom AI Agents

Any client that supports OAuth 2.0 client credentials flow can authenticate:
1. Generate credentials: `uvx simplemem-mcp oauth-generate-client --name custom-agent`
2. Implement the client credentials flow in your application
3. Include the Bearer token in all API requests

### Security Considerations

- **Secure Storage**: OAuth client credentials and secrets are stored in `~/.simplemem-mcp/oauth/` with restrictive permissions (700 for directory, 600 for files)
- **Token Expiry**: Access tokens expire after 1 hour by default
- **Secret Key**: A random secret key is automatically generated for JWT signing
- **HTTPS Recommended**: For production deployments, use HTTPS to protect tokens in transit
- **Revocation**: Revoke compromised clients immediately using `oauth-revoke-client`

### OAuth Server Display on Startup

When running the MCP server with HTTP transports, active OAuth clients are displayed:

```bash
uvx simplemem-mcp --transport streamable-http --host 0.0.0.0 --port 3333
```

Output:
```
Starting SimpleMem MCP Server...
API Endpoint: http://localhost:8000
Transport: streamable-http

=== Active OAuth Clients (2) ===
  - openai (ID: smc_PI-Q2wGQCy8M3kiV3q_y_Q)
  - claude (ID: smc_MG4epJ6DR1A34fiNhCnA4Q)
  OAuth authentication: Optional (use --oauth-required to enforce)
```

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
- `query` (string, optional): Query string for semantic search. When provided, performs vector similarity search to return the most relevant memories. When omitted, returns all memories (most recent first).

**Examples:**
- `retrieve(limit=50)` - Get 50 most recent memories
- `retrieve(query="meeting location", limit=10)` - Get 10 most relevant memories about meeting locations

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
