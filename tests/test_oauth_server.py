"""
Tests for OAuth server endpoints
"""

import pytest
import tempfile
import base64
import hashlib
from pathlib import Path
from fastapi.testclient import TestClient
from simplemem_mcp.oauth import OAuthManager
from simplemem_mcp.oauth_server import create_oauth_app


@pytest.fixture
def oauth_manager():
    """Create OAuth manager with temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield OAuthManager(oauth_dir=Path(tmpdir))


@pytest.fixture
def client(oauth_manager):
    """Create test client for OAuth app"""
    app = create_oauth_app(oauth_manager)
    return TestClient(app), oauth_manager


def _pkce_challenge_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def test_health_endpoint(client):
    """Test health endpoint"""
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "simplemem-mcp-oauth"


def test_oauth_discovery_endpoint(client):
    """OAuth Authorization Server Metadata (RFC 8414) is available."""
    test_client, _ = client

    response = test_client.get("/.well-known/oauth-authorization-server")
    assert response.status_code == 200
    data = response.json()
    assert data["token_endpoint"].endswith("/oauth/token")
    assert "client_secret_post" in data["token_endpoint_auth_methods_supported"]
    assert "client_credentials" in data["grant_types_supported"]


def test_oauth_discovery_endpoint_with_issuer_path(client):
    """Some clients probe /.well-known/oauth-authorization-server/<path>."""
    test_client, _ = client

    response = test_client.get("/.well-known/oauth-authorization-server/mcp")
    assert response.status_code == 200
    data = response.json()
    assert data["issuer"].endswith("/mcp")


def test_openid_configuration_endpoint(client):
    """Some clients probe OIDC discovery even when using OAuth tokens."""
    test_client, _ = client

    response = test_client.get("/.well-known/openid-configuration")
    assert response.status_code == 200
    data = response.json()
    assert data["token_endpoint"].endswith("/oauth/token")


def test_oauth_protected_resource_metadata(client):
    """Protected Resource Metadata (RFC 9728) is available."""
    test_client, _ = client

    response = test_client.get("/.well-known/oauth-protected-resource")
    assert response.status_code == 200
    data = response.json()
    assert "resource" in data
    assert "authorization_servers" in data
    assert isinstance(data["authorization_servers"], list)


def test_oauth_protected_resource_metadata_with_path(client):
    """Some clients probe /.well-known/oauth-protected-resource/<path>."""
    test_client, _ = client

    response = test_client.get("/.well-known/oauth-protected-resource/mcp")
    assert response.status_code == 200
    data = response.json()
    assert data["resource"].endswith("/mcp")


def test_authorization_code_pkce_flow(client, monkeypatch):
    """Authorization Code + PKCE flow produces an access token."""

    test_client, oauth_manager = client

    # Allow redirects in test environment.
    monkeypatch.setenv("SIMPLEMEM_OAUTH_ALLOW_ANY_REDIRECT_URI", "1")

    oauth_client = oauth_manager.generate_client("test-client", "Test client")

    redirect_uri = "https://example.com/callback"
    state = "xyz"
    verifier = "verifier-1234567890"
    challenge = _pkce_challenge_s256(verifier)

    # Step 1: GET authorize returns consent page
    resp = test_client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": oauth_client["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "mcp",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    assert resp.status_code == 200
    assert "Authorize" in resp.text

    # Step 2: POST approve redirects back with code
    resp2 = test_client.post(
        "/oauth/authorize",
        data={
            "response_type": "code",
            "client_id": oauth_client["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "mcp",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "decision": "approve",
        },
        follow_redirects=False,
    )
    assert resp2.status_code in (301, 302, 303, 307)
    location = resp2.headers.get("location")
    assert location is not None
    assert location.startswith(redirect_uri)
    assert "code=" in location
    assert f"state={state}" in location

    code = location.split("code=", 1)[1].split("&", 1)[0]

    # Step 3: exchange code for token
    token_resp = test_client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": oauth_client["client_id"],
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200
    data = token_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert "refresh_token" in data

    # Step 4: cannot reuse code
    token_resp2 = test_client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": oauth_client["client_id"],
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp2.status_code == 400

    # Step 5: refresh token grant works
    refresh_resp = test_client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": oauth_client["client_id"],
            "refresh_token": data["refresh_token"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    assert "access_token" in refresh_data
    assert refresh_data["token_type"] == "Bearer"
    assert "refresh_token" in refresh_data


def test_token_endpoint_client_credentials(client):
    """Test OAuth token endpoint with client credentials flow"""
    test_client, oauth_manager = client
    
    # Generate a client
    oauth_client = oauth_manager.generate_client("test-client", "Test client")
    
    # Request token with valid credentials
    response = test_client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == oauth_manager.token_expiry_seconds()
    
    # Verify the token is valid
    token = data["access_token"]
    payload = oauth_manager.verify_token(token)
    assert payload is not None
    assert payload["sub"] == oauth_client["client_id"]


def test_token_endpoint_invalid_credentials(client):
    """Test token endpoint with invalid credentials"""
    test_client, oauth_manager = client
    
    # Request token with invalid credentials
    response = test_client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "invalid-id",
            "client_secret": "invalid-secret",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"]["error"] == "invalid_client"


def test_token_endpoint_unsupported_grant_type(client):
    """Test token endpoint with unsupported grant type"""
    test_client, oauth_manager = client
    
    oauth_client = oauth_manager.generate_client("test-client", "Test client")
    
    response = test_client.post(
        "/oauth/token",
        data={
            "grant_type": "password",
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"]["error"] == "unsupported_grant_type"


def test_token_endpoint_revoked_client(client):
    """Test token endpoint with revoked client"""
    test_client, oauth_manager = client
    
    # Generate and revoke a client
    oauth_client = oauth_manager.generate_client("test-client", "Test client")
    oauth_manager.revoke_client(oauth_client["client_id"])
    
    # Try to get token
    response = test_client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == 401


def test_oauth_info_endpoint(client):
    """Test OAuth info endpoint"""
    test_client, oauth_manager = client
    
    # Generate client and token
    oauth_client = oauth_manager.generate_client("test-client", "Test client")
    token = oauth_manager.generate_access_token(oauth_client["client_id"])
    
    # Get token info
    response = test_client.get(
        "/oauth/info",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == oauth_client["client_id"]
    assert data["client_name"] == "test-client"
    assert "expires_at" in data
    assert "issued_at" in data


def test_oauth_info_endpoint_invalid_token(client):
    """Test OAuth info endpoint with invalid token"""
    test_client, _ = client
    
    response = test_client.get(
        "/oauth/info",
        headers={"Authorization": "Bearer invalid-token"}
    )
    
    assert response.status_code == 401


def test_oauth_info_endpoint_no_token(client):
    """Test OAuth info endpoint without token"""
    test_client, _ = client
    
    response = test_client.get("/oauth/info")
    
    assert response.status_code == 401  # FastAPI returns 401 for missing credentials


def test_token_endpoint_with_scope(client):
    """Test token endpoint with scope parameter"""
    test_client, oauth_manager = client
    
    oauth_client = oauth_manager.generate_client("test-client", "Test client")
    
    response = test_client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"],
            "scope": "read write",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "read write"
