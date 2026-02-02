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

### Start OAuth Server (Local)
```bash
uvx simplemem-mcp oauth-server --host 127.0.0.1 --port 8080
```

### Start OAuth Server (Public)
```bash
uvx simplemem-mcp oauth-server --host 0.0.0.0 --port 8080
```

## OAuth Endpoints

- **Token Endpoint**: `POST /oauth/token`
- **Info Endpoint**: `GET /oauth/info`
- **Health Check**: `GET /health`

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

- **Expires in**: 3600 seconds (1 hour)
- **Type**: Bearer token
- **Algorithm**: HS256 (HMAC-SHA256)

## Security Notes

- Directory permissions: `700` (owner only)
- File permissions: `600` (owner read/write only)
- Always use HTTPS in production
- Store client secrets securely
- Revoke compromised clients immediately
