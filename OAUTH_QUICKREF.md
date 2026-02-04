# OAuth Quick Reference

## Client Management Commands

### Generate New Client
```bash
uvx simplemem-mcp oauth-generate-client --name <client_name> --description "<description>"
```

### List All Clients
```bash
uvx simplemem-mcp oauth-list-clients
```

### Revoke Client
```bash
uvx simplemem-mcp oauth-revoke-client --client-id <client_id>
```

## OAuth Server

### Start Combined OAuth + MCP Server (Single Port)

Recommended for ChatGPT connectors / single public URL:

```bash
uvx simplemem-mcp \
  --transport streamable-http \
  --host 0.0.0.0 \
  --port 3333 \
  --oauth-required
```

### Start OAuth Server (Local)
```bash
uvx simplemem-mcp oauth-server --host 127.0.0.1 --port 8080
```

### Start OAuth Server (Public)
```bash
uvx simplemem-mcp oauth-server --host 0.0.0.0 --port 8080
```

## OAuth Endpoints

- **Authorization Endpoint**: `GET/POST /oauth/authorize` (Authorization Code + PKCE)
- **Token Endpoint**: `POST /oauth/token`
- **Info Endpoint**: `GET /oauth/info`
- **Health Check**: `GET /health`

## Discovery Endpoints

- OAuth AS Metadata (RFC 8414): `GET /.well-known/oauth-authorization-server`
- OpenID Discovery (minimal): `GET /.well-known/openid-configuration`
- Protected Resource Metadata (RFC 9728): `GET /.well-known/oauth-protected-resource`

## Token Request

```bash
curl -X POST http://localhost:8080/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "<client_id>",
    "client_secret": "<client_secret>"
  }'
```

## Token Usage

```bash
curl -X GET http://localhost:8080/oauth/info \
  -H "Authorization: Bearer <access_token>"
```

## Files Location

- OAuth data: `~/.simplemem-mcp/oauth/`
- Clients file: `~/.simplemem-mcp/oauth/clients.json`
- Secret key: `~/.simplemem-mcp/oauth/secret_key.txt`

## Token Properties

- **Expires in**: 3600 seconds (1 hour) by default
- **Configure**: `SIMPLEMEM_OAUTH_TOKEN_EXPIRY_SECONDS=86400` (example: 24 hours)
- **Clock skew leeway**: `SIMPLEMEM_OAUTH_JWT_LEEWAY_SECONDS=60` (example: allow 60s drift)
- **Type**: Bearer token
- **Algorithm**: HS256 (HMAC-SHA256)

## Refresh Token Grant

```bash
curl -X POST http://localhost:8080/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "client_id=<client_id>" \
  -d "refresh_token=<refresh_token>"
```

## Security Notes

- Directory permissions: `700` (owner only)
- File permissions: `600` (owner read/write only)
- Always use HTTPS in production
- Store client secrets securely
- Revoke compromised clients immediately

## Redirect URI Policy (Authorization Code)

- Dev: `SIMPLEMEM_OAUTH_ALLOW_ANY_REDIRECT_URI=1`
- Prod: `SIMPLEMEM_OAUTH_ALLOWED_REDIRECT_URIS=https://example.com/callback,...`
- Default allowlist includes ChatGPT connector redirects
