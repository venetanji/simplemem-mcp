"""
Tests for OAuth server endpoints
"""

import pytest
import tempfile
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


def test_health_endpoint(client):
    """Test health endpoint"""
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "simplemem-mcp-oauth"


def test_token_endpoint_client_credentials(client):
    """Test OAuth token endpoint with client credentials flow"""
    test_client, oauth_manager = client
    
    # Generate a client
    oauth_client = oauth_manager.generate_client("test-client", "Test client")
    
    # Request token with valid credentials
    response = test_client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 3600
    
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
        json={
            "grant_type": "client_credentials",
            "client_id": "invalid-id",
            "client_secret": "invalid-secret"
        }
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
        json={
            "grant_type": "authorization_code",  # Not supported yet
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"]
        }
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
        json={
            "grant_type": "client_credentials",
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"]
        }
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
        json={
            "grant_type": "client_credentials",
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"],
            "scope": "read write"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "read write"
