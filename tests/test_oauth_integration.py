"""
Integration tests for OAuth authentication flow

These tests demonstrate a complete OAuth flow including:
- Client generation
- Token acquisition
- Token usage
"""

import pytest
import tempfile
import httpx
import asyncio
import multiprocessing
import time
from pathlib import Path
from simplemem_mcp.oauth import OAuthManager
from simplemem_mcp.oauth_server import run_oauth_server


def run_server_process(oauth_dir: str, port: int):
    """Run OAuth server in a separate process"""
    oauth_manager = OAuthManager(oauth_dir=Path(oauth_dir))
    run_oauth_server(oauth_manager, host="127.0.0.1", port=port)


@pytest.fixture
def oauth_server():
    """Start OAuth server in a separate process"""
    with tempfile.TemporaryDirectory() as tmpdir:
        port = 8089  # Use a different port to avoid conflicts
        
        # Start server process
        process = multiprocessing.Process(
            target=run_server_process,
            args=(tmpdir, port)
        )
        process.start()
        
        # Wait for server to start
        time.sleep(2)
        
        # Return manager and URL
        oauth_manager = OAuthManager(oauth_dir=Path(tmpdir))
        base_url = f"http://127.0.0.1:{port}"
        
        yield oauth_manager, base_url
        
        # Clean up
        process.terminate()
        process.join(timeout=5)
        if process.is_alive():
            process.kill()


@pytest.mark.asyncio
async def test_complete_oauth_flow(oauth_server):
    """Test complete OAuth authentication flow"""
    oauth_manager, base_url = oauth_server
    
    # Step 1: Generate OAuth client
    client = oauth_manager.generate_client(
        name="test-integration-client",
        description="Integration test client"
    )
    
    assert "client_id" in client
    assert "client_secret" in client
    
    # Step 2: Request access token
    async with httpx.AsyncClient() as http_client:
        token_response = await http_client.post(
            f"{base_url}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": client["client_id"],
                "client_secret": client["client_secret"]
            }
        )
        
        assert token_response.status_code == 200
        token_data = token_response.json()
        
        assert "access_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["expires_in"] == oauth_manager.token_expiry_seconds()
        
        access_token = token_data["access_token"]
        
        # Step 3: Use access token to get info
        info_response = await http_client.get(
            f"{base_url}/oauth/info",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert info_response.status_code == 200
        info_data = info_response.json()
        
        assert info_data["client_id"] == client["client_id"]
        assert info_data["client_name"] == "test-integration-client"


@pytest.mark.asyncio
async def test_revoked_client_cannot_get_token(oauth_server):
    """Test that revoked clients cannot obtain tokens"""
    oauth_manager, base_url = oauth_server
    
    # Generate and revoke client
    client = oauth_manager.generate_client("revoked-client", "Test")
    oauth_manager.revoke_client(client["client_id"])
    
    # Try to get token
    async with httpx.AsyncClient() as http_client:
        token_response = await http_client.post(
            f"{base_url}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": client["client_id"],
                "client_secret": client["client_secret"]
            }
        )
        
        assert token_response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(oauth_server):
    """Test that invalid tokens are rejected"""
    _, base_url = oauth_server
    
    async with httpx.AsyncClient() as http_client:
        info_response = await http_client.get(
            f"{base_url}/oauth/info",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert info_response.status_code == 401


@pytest.mark.asyncio
async def test_openai_claude_scenario(oauth_server):
    """Simulate OpenAI and Claude both authenticating"""
    oauth_manager, base_url = oauth_server
    
    # Generate clients for OpenAI and Claude
    openai_client = oauth_manager.generate_client("openai", "OpenAI integration")
    claude_client = oauth_manager.generate_client("claude", "Claude integration")
    
    async with httpx.AsyncClient() as http_client:
        # OpenAI gets token
        openai_token_response = await http_client.post(
            f"{base_url}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": openai_client["client_id"],
                "client_secret": openai_client["client_secret"]
            }
        )
        assert openai_token_response.status_code == 200
        openai_token = openai_token_response.json()["access_token"]
        
        # Claude gets token
        claude_token_response = await http_client.post(
            f"{base_url}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": claude_client["client_id"],
                "client_secret": claude_client["client_secret"]
            }
        )
        assert claude_token_response.status_code == 200
        claude_token = claude_token_response.json()["access_token"]
        
        # Both tokens work independently
        openai_info = await http_client.get(
            f"{base_url}/oauth/info",
            headers={"Authorization": f"Bearer {openai_token}"}
        )
        assert openai_info.json()["client_name"] == "openai"
        
        claude_info = await http_client.get(
            f"{base_url}/oauth/info",
            headers={"Authorization": f"Bearer {claude_token}"}
        )
        assert claude_info.json()["client_name"] == "claude"


@pytest.mark.asyncio
async def test_authorization_code_refresh_flow(oauth_server, monkeypatch):
    """Authorization Code + PKCE flow returns refresh token and refresh grant works."""
    oauth_manager, base_url = oauth_server

    client = oauth_manager.generate_client("refresh-client", "Refresh flow")

    # Use a default-allowed redirect URI (server runs in a separate process).
    redirect_uri = "https://chatgpt.com/connector_platform_oauth_redirect"
    verifier = "verifier-1234567890"
    challenge = ""
    # simple PKCE helper inline
    import hashlib
    import base64

    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    async with httpx.AsyncClient(follow_redirects=False) as http_client:
        # GET authorize
        resp = await http_client.get(
            f"{base_url}/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": client["client_id"],
                "redirect_uri": redirect_uri,
                "state": "state1",
                "scope": "mcp offline_access",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
        )
        assert resp.status_code == 200

        # POST approve
        resp2 = await http_client.post(
            f"{base_url}/oauth/authorize",
            data={
                "response_type": "code",
                "client_id": client["client_id"],
                "redirect_uri": redirect_uri,
                "state": "state1",
                "scope": "mcp offline_access",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "decision": "approve",
            },
        )
        assert resp2.status_code in (301, 302, 303, 307)
        location = resp2.headers.get("location")
        assert location
        code = location.split("code=", 1)[1].split("&", 1)[0]

        # Exchange code for tokens
        token_resp = await http_client.post(
            f"{base_url}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client["client_id"],
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert token_resp.status_code == 200
        token_data = token_resp.json()
        assert "refresh_token" in token_data

        # Refresh token grant
        refresh_resp = await http_client.post(
            f"{base_url}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client["client_id"],
                "refresh_token": token_data["refresh_token"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert refresh_resp.status_code == 200
        refresh_data = refresh_resp.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
