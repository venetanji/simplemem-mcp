# OAuth Integration Guide for External AI Clients

This guide explains how to integrate simplemem-mcp OAuth authentication with external AI clients like OpenAI, Claude, and custom AI agents.

## Overview

simplemem-mcp implements OAuth 2.0 client credentials flow for secure authentication. This allows external AI services and agents to:
- Obtain time-limited access tokens
- Make authenticated requests to the MCP server
- Have their access controlled and revokable

## Quick Start

### 1. Generate OAuth Credentials

```bash
# For OpenAI
uvx simplemem-mcp oauth-generate-client --name openai --description "OpenAI integration"

# For Claude
uvx simplemem-mcp oauth-generate-client --name claude --description "Claude AI integration"

# For custom AI agent
uvx simplemem-mcp oauth-generate-client --name my-agent --description "My custom AI agent"
```

Save the generated `client_id` and `client_secret` securely.

### 2. Start the OAuth Server

```bash
# For local testing
uvx simplemem-mcp oauth-server --host 127.0.0.1 --port 8080

# For production (accessible externally)
uvx simplemem-mcp oauth-server --host 0.0.0.0 --port 8080
```

### 3. Obtain Access Token

Make a POST request to the token endpoint:

```bash
curl -X POST http://your-server:8080/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
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

### 4. Use Access Token

Include the token in requests:

```bash
curl -X GET http://your-server:8080/oauth/info \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Integration Examples

### Python Client

```python
import httpx
import asyncio

class SimplememMCPClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.client = httpx.AsyncClient()
    
    async def authenticate(self):
        """Obtain access token"""
        response = await self.client.post(
            f"{self.base_url}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        return self.access_token
    
    async def get_headers(self):
        """Get authorization headers"""
        if not self.access_token:
            await self.authenticate()
        return {"Authorization": f"Bearer {self.access_token}"}
    
    async def make_request(self, method: str, endpoint: str, **kwargs):
        """Make authenticated request"""
        headers = await self.get_headers()
        response = await self.client.request(
            method,
            f"{self.base_url}{endpoint}",
            headers=headers,
            **kwargs
        )
        
        # Handle token expiry
        if response.status_code == 401:
            await self.authenticate()
            headers = await self.get_headers()
            response = await self.client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                **kwargs
            )
        
        response.raise_for_status()
        return response.json()

# Usage
async def main():
    client = SimplememMCPClient(
        base_url="http://localhost:8080",
        client_id="smc_...",
        client_secret="..."
    )
    
    # Authenticate
    await client.authenticate()
    
    # Make requests
    info = await client.make_request("GET", "/oauth/info")
    print(f"Authenticated as: {info['client_name']}")

asyncio.run(main())
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

class SimplememMCPClient {
  constructor(baseURL, clientId, clientSecret) {
    this.baseURL = baseURL;
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this.accessToken = null;
  }

  async authenticate() {
    const response = await axios.post(`${this.baseURL}/oauth/token`, {
      grant_type: 'client_credentials',
      client_id: this.clientId,
      client_secret: this.clientSecret
    });
    
    this.accessToken = response.data.access_token;
    return this.accessToken;
  }

  async getHeaders() {
    if (!this.accessToken) {
      await this.authenticate();
    }
    return {
      'Authorization': `Bearer ${this.accessToken}`
    };
  }

  async makeRequest(method, endpoint, data = null) {
    const headers = await this.getHeaders();
    
    try {
      const response = await axios({
        method,
        url: `${this.baseURL}${endpoint}`,
        headers,
        data
      });
      return response.data;
    } catch (error) {
      // Handle token expiry
      if (error.response && error.response.status === 401) {
        await this.authenticate();
        const newHeaders = await this.getHeaders();
        const response = await axios({
          method,
          url: `${this.baseURL}${endpoint}`,
          headers: newHeaders,
          data
        });
        return response.data;
      }
      throw error;
    }
  }
}

// Usage
(async () => {
  const client = new SimplememMCPClient(
    'http://localhost:8080',
    'smc_...',
    '...'
  );

  await client.authenticate();
  
  const info = await client.makeRequest('GET', '/oauth/info');
  console.log(`Authenticated as: ${info.client_name}`);
})();
```

### Go Client

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
)

type SimplememMCPClient struct {
    BaseURL      string
    ClientID     string
    ClientSecret string
    AccessToken  string
    Client       *http.Client
}

type TokenResponse struct {
    AccessToken string `json:"access_token"`
    TokenType   string `json:"token_type"`
    ExpiresIn   int    `json:"expires_in"`
}

func NewClient(baseURL, clientID, clientSecret string) *SimplememMCPClient {
    return &SimplememMCPClient{
        BaseURL:      baseURL,
        ClientID:     clientID,
        ClientSecret: clientSecret,
        Client:       &http.Client{},
    }
}

func (c *SimplememMCPClient) Authenticate() error {
    payload := map[string]string{
        "grant_type":    "client_credentials",
        "client_id":     c.ClientID,
        "client_secret": c.ClientSecret,
    }
    
    jsonData, _ := json.Marshal(payload)
    
    resp, err := c.Client.Post(
        c.BaseURL+"/oauth/token",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != 200 {
        return fmt.Errorf("authentication failed: %d", resp.StatusCode)
    }
    
    var tokenResp TokenResponse
    if err := json.NewDecoder(resp.Body).Decode(&tokenResp); err != nil {
        return err
    }
    
    c.AccessToken = tokenResp.AccessToken
    return nil
}

func (c *SimplememMCPClient) MakeRequest(method, endpoint string, body io.Reader) ([]byte, error) {
    if c.AccessToken == "" {
        if err := c.Authenticate(); err != nil {
            return nil, err
        }
    }
    
    req, err := http.NewRequest(method, c.BaseURL+endpoint, body)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+c.AccessToken)
    req.Header.Set("Content-Type", "application/json")
    
    resp, err := c.Client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    // Handle token expiry
    if resp.StatusCode == 401 {
        if err := c.Authenticate(); err != nil {
            return nil, err
        }
        
        req.Header.Set("Authorization", "Bearer "+c.AccessToken)
        resp, err = c.Client.Do(req)
        if err != nil {
            return nil, err
        }
        defer resp.Body.Close()
    }
    
    return io.ReadAll(resp.Body)
}

func main() {
    client := NewClient(
        "http://localhost:8080",
        "smc_...",
        "...",
    )
    
    if err := client.Authenticate(); err != nil {
        panic(err)
    }
    
    data, err := client.MakeRequest("GET", "/oauth/info", nil)
    if err != nil {
        panic(err)
    }
    
    fmt.Println(string(data))
}
```

## Integration with Specific Platforms

### OpenAI Custom Actions

If you're building a custom GPT with actions that need to access simplemem-mcp:

1. Generate OpenAI OAuth client:
   ```bash
   uvx simplemem-mcp oauth-generate-client --name openai-gpt --description "OpenAI GPT integration"
   ```

2. In your GPT configuration, set up authentication:
   - Authentication Type: OAuth
   - Client ID: `<your_client_id>`
   - Client Secret: `<your_client_secret>`
   - Authorization URL: `http://your-server:8080/oauth/token`
   - Token URL: `http://your-server:8080/oauth/token`
   - Scope: (leave empty)

### Claude API

To integrate with Claude API:

1. Generate Claude OAuth client:
   ```bash
   uvx simplemem-mcp oauth-generate-client --name claude --description "Claude integration"
   ```

2. In your application, implement OAuth flow as shown in the Python/JavaScript examples above.

## Security Best Practices

1. **Use HTTPS in Production**: Always use HTTPS for production deployments to protect tokens in transit
2. **Secure Storage**: Store client secrets in environment variables or secure vaults, never in code
3. **Token Rotation**: Tokens expire after 1 hour; implement automatic renewal
4. **Monitor Access**: Regularly review active clients using `oauth-list-clients`
5. **Revoke Compromised Clients**: Immediately revoke any compromised credentials:
   ```bash
   uvx simplemem-mcp oauth-revoke-client --client-id <client_id>
   ```
6. **Restrict Network Access**: Use firewall rules to limit who can access the OAuth server
7. **Audit Logs**: Monitor server logs for suspicious authentication attempts

## Troubleshooting

### "Invalid client credentials" Error

- Verify client_id and client_secret are correct
- Check if client has been revoked using `oauth-list-clients`
- Ensure you're using the correct OAuth server URL

### Token Expired Error

- Tokens expire after 1 hour
- Implement automatic token renewal in your client
- Request a new token when receiving 401 responses

### Connection Refused

- Verify OAuth server is running
- Check host and port configuration
- Ensure firewall allows connections

## Advanced Usage

### Multiple Environments

Maintain separate OAuth clients for different environments:

```bash
# Development
uvx simplemem-mcp oauth-generate-client --name myapp-dev

# Staging
uvx simplemem-mcp oauth-generate-client --name myapp-staging

# Production
uvx simplemem-mcp oauth-generate-client --name myapp-prod
```

### Monitoring

Check which clients are authenticating by monitoring server logs or using the info endpoint after authentication.

## Support

For issues or questions:
- Check the main README.md
- Review test files in `tests/` for more examples
- Open an issue on GitHub
