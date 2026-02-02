"""
Tests for OAuth authentication functionality
"""

import pytest
import tempfile
import time
from pathlib import Path
from simplemem_mcp.oauth import OAuthManager


@pytest.fixture
def oauth_manager():
    """Create OAuth manager with temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield OAuthManager(oauth_dir=Path(tmpdir))


def test_generate_client(oauth_manager):
    """Test OAuth client generation"""
    client = oauth_manager.generate_client("test-client", "Test client description")
    
    assert "client_id" in client
    assert "client_secret" in client
    assert client["name"] == "test-client"
    assert client["description"] == "Test client description"
    assert client["client_id"].startswith("smc_")
    assert len(client["client_secret"]) > 32


def test_list_clients(oauth_manager):
    """Test listing OAuth clients"""
    # Initially empty
    clients = oauth_manager.list_clients()
    assert len(clients) == 0
    
    # Add some clients
    oauth_manager.generate_client("client1", "First client")
    oauth_manager.generate_client("client2", "Second client")
    
    clients = oauth_manager.list_clients()
    assert len(clients) == 2
    assert any(c["name"] == "client1" for c in clients)
    assert any(c["name"] == "client2" for c in clients)


def test_verify_client(oauth_manager):
    """Test client credential verification"""
    client = oauth_manager.generate_client("test-client", "Test client")
    
    # Valid credentials
    assert oauth_manager.verify_client(client["client_id"], client["client_secret"]) is True
    
    # Invalid secret
    assert oauth_manager.verify_client(client["client_id"], "wrong-secret") is False
    
    # Invalid client ID
    assert oauth_manager.verify_client("invalid-id", client["client_secret"]) is False


def test_revoke_client(oauth_manager):
    """Test client revocation"""
    client = oauth_manager.generate_client("test-client", "Test client")
    
    # Client should work initially
    assert oauth_manager.verify_client(client["client_id"], client["client_secret"]) is True
    
    # Revoke client
    assert oauth_manager.revoke_client(client["client_id"]) is True
    
    # Should no longer verify
    assert oauth_manager.verify_client(client["client_id"], client["client_secret"]) is False
    
    # Check in list
    clients = oauth_manager.list_clients()
    assert len(clients) == 1
    assert clients[0]["revoked"] is True


def test_generate_access_token(oauth_manager):
    """Test access token generation"""
    client = oauth_manager.generate_client("test-client", "Test client")
    
    token = oauth_manager.generate_access_token(client["client_id"])
    assert token is not None
    assert len(token) > 50  # JWT tokens are long
    
    # Verify the token
    payload = oauth_manager.verify_token(token)
    assert payload is not None
    assert payload["sub"] == client["client_id"]
    assert payload["name"] == "test-client"
    assert payload["type"] == "access_token"


def test_verify_token(oauth_manager):
    """Test token verification"""
    client = oauth_manager.generate_client("test-client", "Test client")
    token = oauth_manager.generate_access_token(client["client_id"])
    
    # Valid token
    payload = oauth_manager.verify_token(token)
    assert payload is not None
    assert payload["sub"] == client["client_id"]
    
    # Invalid token
    assert oauth_manager.verify_token("invalid-token") is None
    
    # Token for revoked client
    oauth_manager.revoke_client(client["client_id"])
    assert oauth_manager.verify_token(token) is None


def test_token_expiry(oauth_manager):
    """Test token expiration handling"""
    # This test would need to mock time or wait for actual expiry
    # For now, we just ensure tokens have expiry set
    client = oauth_manager.generate_client("test-client", "Test client")
    token = oauth_manager.generate_access_token(client["client_id"])
    
    payload = oauth_manager.verify_token(token)
    assert "exp" in payload
    assert "iat" in payload
    assert payload["exp"] > payload["iat"]


def test_get_client(oauth_manager):
    """Test getting client information"""
    client = oauth_manager.generate_client("test-client", "Test description")
    
    # Get existing client
    client_info = oauth_manager.get_client(client["client_id"])
    assert client_info is not None
    assert client_info["name"] == "test-client"
    assert client_info["description"] == "Test description"
    assert "secret_hash" not in client_info  # Should not expose hash
    
    # Get non-existent client
    assert oauth_manager.get_client("non-existent") is None


def test_multiple_clients_isolation(oauth_manager):
    """Test that multiple clients work independently"""
    client1 = oauth_manager.generate_client("client1", "First")
    client2 = oauth_manager.generate_client("client2", "Second")
    
    # Each should verify with their own credentials
    assert oauth_manager.verify_client(client1["client_id"], client1["client_secret"]) is True
    assert oauth_manager.verify_client(client2["client_id"], client2["client_secret"]) is True
    
    # Cross-verification should fail
    assert oauth_manager.verify_client(client1["client_id"], client2["client_secret"]) is False
    assert oauth_manager.verify_client(client2["client_id"], client1["client_secret"]) is False
    
    # Tokens should be independent
    token1 = oauth_manager.generate_access_token(client1["client_id"])
    token2 = oauth_manager.generate_access_token(client2["client_id"])
    
    payload1 = oauth_manager.verify_token(token1)
    payload2 = oauth_manager.verify_token(token2)
    
    assert payload1["sub"] == client1["client_id"]
    assert payload2["sub"] == client2["client_id"]


def test_oauth_dir_permissions(oauth_manager):
    """Test that OAuth directory has correct permissions"""
    import stat
    
    # Check directory permissions (should be 0o700)
    dir_stat = oauth_manager.oauth_dir.stat()
    dir_mode = stat.S_IMODE(dir_stat.st_mode)
    assert dir_mode == 0o700


def test_clients_file_permissions(oauth_manager):
    """Test that clients file has correct permissions"""
    import stat
    
    # Generate a client to create the file
    oauth_manager.generate_client("test", "test")
    
    # Check file permissions (should be 0o600)
    file_stat = oauth_manager.clients_file.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600


def test_default_redirect_uri_allowlist(oauth_manager, monkeypatch):
    """By default we allow the ChatGPT connector redirect URI."""

    # Ensure env vars don't override defaults
    monkeypatch.delenv("SIMPLEMEM_OAUTH_ALLOW_ANY_REDIRECT_URI", raising=False)
    monkeypatch.delenv("SIMPLEMEM_OAUTH_ALLOWED_REDIRECT_URIS", raising=False)

    assert oauth_manager.is_redirect_uri_allowed(
        "https://chatgpt.com/connector_platform_oauth_redirect"
    )
    assert oauth_manager.is_redirect_uri_allowed(
        "https://chat.openai.com/connector_platform_oauth_redirect"
    )
    assert oauth_manager.is_redirect_uri_allowed("https://example.com/callback") is False


def test_redirect_uri_env_allowlist_overrides_defaults(oauth_manager, monkeypatch):
    """If SIMPLEMEM_OAUTH_ALLOWED_REDIRECT_URIS is set, only those URIs are allowed."""

    monkeypatch.delenv("SIMPLEMEM_OAUTH_ALLOW_ANY_REDIRECT_URI", raising=False)
    monkeypatch.setenv(
        "SIMPLEMEM_OAUTH_ALLOWED_REDIRECT_URIS",
        "https://example.com/callback",
    )

    assert oauth_manager.is_redirect_uri_allowed("https://example.com/callback") is True
    assert (
        oauth_manager.is_redirect_uri_allowed(
            "https://chatgpt.com/connector_platform_oauth_redirect"
        )
        is False
    )
