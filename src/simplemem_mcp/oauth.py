"""
OAuth authentication module for simplemem-mcp

This module provides OAuth authentication support for external AI clients
using client credentials and authorization code grant flows.
"""

import os
import json
import secrets
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any
import jwt
from passlib.context import CryptContext
from passlib.exc import MissingBackendError


_CLIENT_SECRET_CONTEXT = CryptContext(
    schemes=[
        # Prefer bcrypt when available, but fall back to pure-Python pbkdf2_sha256.
        "bcrypt",
        "pbkdf2_sha256",
    ],
    deprecated="auto",
)


def _hash_client_secret(client_secret: str) -> str:
    """Hash a client secret for storage.

    Uses bcrypt if a backend is available; otherwise falls back to pbkdf2_sha256.
    """

    try:
        return _CLIENT_SECRET_CONTEXT.hash(client_secret)
    except MissingBackendError:
        return CryptContext(schemes=["pbkdf2_sha256"]).hash(client_secret)


def _verify_client_secret(client_secret: str, secret_hash: str) -> bool:
    """Verify a client secret against the stored hash."""

    try:
        return _CLIENT_SECRET_CONTEXT.verify(client_secret, secret_hash)
    except MissingBackendError:
        # Most commonly: trying to verify a bcrypt hash without a bcrypt backend.
        return False


# Constants
DEFAULT_OAUTH_DIR = Path.home() / ".simplemem-mcp" / "oauth"
TOKEN_EXPIRY_SECONDS = 3600  # 1 hour
REFRESH_TOKEN_EXPIRY_DAYS = 30
AUTH_CODE_EXPIRY_SECONDS = 600  # 10 minutes

# ChatGPT connector uses a fixed OAuth redirect URI. Allow it by default so
# OAuth sign-in works out-of-the-box, while still supporting strict allowlists.
DEFAULT_ALLOWED_REDIRECT_URIS: set[str] = {
    "https://chatgpt.com/connector_platform_oauth_redirect",
    "https://chat.openai.com/connector_platform_oauth_redirect",
}


def _base64url_nopad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _pkce_s256(verifier: str) -> str:
    return _base64url_nopad(hashlib.sha256(verifier.encode("utf-8")).digest())


class OAuthManager:
    """Manages OAuth clients and tokens"""
    
    def __init__(self, oauth_dir: Optional[Path] = None):
        """Initialize OAuth manager
        
        Args:
            oauth_dir: Directory to store OAuth data. Defaults to ~/.simplemem-mcp/oauth
        """
        self.oauth_dir = oauth_dir or DEFAULT_OAUTH_DIR
        self.clients_file = self.oauth_dir / "clients.json"
        self.auth_codes_file = self.oauth_dir / "auth_codes.json"
        self.secret_key_file = self.oauth_dir / "secret_key.txt"
        self._ensure_oauth_dir()
        self._ensure_secret_key()
    
    def _ensure_oauth_dir(self):
        """Create OAuth directory if it doesn't exist"""
        self.oauth_dir.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions (owner only)
        os.chmod(self.oauth_dir, 0o700)
    
    def _ensure_secret_key(self):
        """Create secret key for JWT signing if it doesn't exist"""
        if not self.secret_key_file.exists():
            secret_key = secrets.token_urlsafe(64)
            self.secret_key_file.write_text(secret_key)
            os.chmod(self.secret_key_file, 0o600)
    
    def _get_secret_key(self) -> str:
        """Get the JWT secret key"""
        return self.secret_key_file.read_text().strip()
    
    def _load_clients(self) -> Dict[str, dict]:
        """Load OAuth clients from file"""
        if not self.clients_file.exists():
            return {}
        try:
            with open(self.clients_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_clients(self, clients: Dict[str, dict]):
        """Save OAuth clients to file"""
        with open(self.clients_file, 'w') as f:
            json.dump(clients, f, indent=2)
        os.chmod(self.clients_file, 0o600)

    def _load_auth_codes(self) -> Dict[str, dict]:
        if not self.auth_codes_file.exists():
            return {}
        try:
            with open(self.auth_codes_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_auth_codes(self, auth_codes: Dict[str, dict]) -> None:
        with open(self.auth_codes_file, "w") as f:
            json.dump(auth_codes, f, indent=2)
        os.chmod(self.auth_codes_file, 0o600)

    def is_redirect_uri_allowed(self, redirect_uri: str) -> bool:
        """Check whether a redirect URI is allowed.

        For development, you can set SIMPLEMEM_OAUTH_ALLOW_ANY_REDIRECT_URI=1.
        For production, set SIMPLEMEM_OAUTH_ALLOWED_REDIRECT_URIS to a comma-separated
        list of allowed redirect URIs.

        If no env vars are set, a small default allowlist is used for well-known
        connector redirect endpoints.
        """

        if os.environ.get("SIMPLEMEM_OAUTH_ALLOW_ANY_REDIRECT_URI") in {"1", "true", "TRUE", "yes", "YES"}:
            return True

        allowed = os.environ.get("SIMPLEMEM_OAUTH_ALLOWED_REDIRECT_URIS", "").strip()
        if allowed:
            allowed_set = {u.strip() for u in allowed.split(",") if u.strip()}
            return redirect_uri in allowed_set

        return redirect_uri in DEFAULT_ALLOWED_REDIRECT_URIS

    def generate_authorization_code(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str = "S256",
        scope: str = "",
    ) -> str:
        """Generate an OAuth 2.0 authorization code (for Authorization Code + PKCE)."""

        client = self.get_client(client_id)
        if not client or client.get("revoked", False):
            raise ValueError("Invalid client_id")
        if not self.is_redirect_uri_allowed(redirect_uri):
            raise ValueError("redirect_uri is not allowed")

        method = (code_challenge_method or "S256").upper()
        if method not in {"S256", "PLAIN"}:
            raise ValueError("Unsupported code_challenge_method")

        code = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        auth_codes = self._load_auth_codes()
        auth_codes[code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "code_challenge": code_challenge,
            "code_challenge_method": method,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=AUTH_CODE_EXPIRY_SECONDS)).isoformat(),
            "used": False,
        }
        self._save_auth_codes(auth_codes)
        return code

    def consume_authorization_code(
        self,
        *,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> Dict[str, Any]:
        """Validate and consume an authorization code.

        Returns:
            Dict with client_id and scope.
        """

        auth_codes = self._load_auth_codes()
        record = auth_codes.get(code)
        if not record:
            raise ValueError("Invalid authorization code")

        if record.get("used"):
            raise ValueError("Authorization code already used")

        if record.get("client_id") != client_id:
            raise ValueError("Invalid client_id")

        if record.get("redirect_uri") != redirect_uri:
            raise ValueError("Invalid redirect_uri")

        try:
            expires_at = datetime.fromisoformat(record["expires_at"])
        except Exception:
            raise ValueError("Invalid authorization code")
        if datetime.now(timezone.utc) >= expires_at:
            raise ValueError("Authorization code expired")

        method = (record.get("code_challenge_method") or "S256").upper()
        expected = record.get("code_challenge") or ""
        if method == "S256":
            actual = _pkce_s256(code_verifier)
        elif method == "PLAIN":
            actual = code_verifier
        else:
            raise ValueError("Unsupported code_challenge_method")

        if not secrets.compare_digest(expected, actual):
            raise ValueError("Invalid code_verifier")

        record["used"] = True
        record["used_at"] = datetime.now(timezone.utc).isoformat()
        auth_codes[code] = record
        self._save_auth_codes(auth_codes)

        return {"client_id": client_id, "scope": record.get("scope", "")}
    
    def generate_client(self, name: str, description: str = "") -> Dict[str, str]:
        """Generate a new OAuth client
        
        Args:
            name: Client name (e.g., 'openai', 'claude', 'custom-ai-agent')
            description: Optional client description
            
        Returns:
            Dict with client_id and client_secret
        """
        clients = self._load_clients()
        
        # Generate client credentials
        client_id = f"smc_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(48)
        
        # Hash the secret for storage
        secret_hash = _hash_client_secret(client_secret)
        
        # Store client info
        clients[client_id] = {
            "name": name,
            "description": description,
            "secret_hash": secret_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "revoked": False
        }
        
        self._save_clients(clients)
        
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "name": name,
            "description": description
        }
    
    def list_clients(self) -> List[Dict[str, str]]:
        """List all registered OAuth clients
        
        Returns:
            List of client info (without secrets)
        """
        clients = self._load_clients()
        return [
            {
                "client_id": client_id,
                "name": info["name"],
                "description": info.get("description", ""),
                "created_at": info["created_at"],
                "revoked": info.get("revoked", False)
            }
            for client_id, info in clients.items()
        ]
    
    def revoke_client(self, client_id: str) -> bool:
        """Revoke an OAuth client
        
        Args:
            client_id: The client ID to revoke
            
        Returns:
            True if client was revoked, False if not found
        """
        clients = self._load_clients()
        if client_id not in clients:
            return False
        
        clients[client_id]["revoked"] = True
        clients[client_id]["revoked_at"] = datetime.now(timezone.utc).isoformat()
        self._save_clients(clients)
        return True
    
    def verify_client(self, client_id: str, client_secret: str) -> bool:
        """Verify client credentials
        
        Args:
            client_id: The client ID
            client_secret: The client secret
            
        Returns:
            True if credentials are valid and not revoked
        """
        clients = self._load_clients()
        if client_id not in clients:
            return False
        
        client = clients[client_id]
        if client.get("revoked", False):
            return False
        
        return _verify_client_secret(client_secret, client["secret_hash"])
    
    def get_client(self, client_id: str) -> Optional[dict]:
        """Get client info by ID
        
        Args:
            client_id: The client ID
            
        Returns:
            Client info dict or None if not found
        """
        clients = self._load_clients()
        if client_id not in clients:
            return None
        
        client = clients[client_id]
        return {
            "client_id": client_id,
            "name": client["name"],
            "description": client.get("description", ""),
            "created_at": client["created_at"],
            "revoked": client.get("revoked", False)
        }
    
    def generate_access_token(self, client_id: str) -> str:
        """Generate an access token for a client
        
        Args:
            client_id: The client ID
            
        Returns:
            JWT access token
        """
        client = self.get_client(client_id)
        if not client:
            raise ValueError("Invalid client_id")
        
        payload = {
            "sub": client_id,
            "name": client["name"],
            "type": "access_token",
            "exp": datetime.now(timezone.utc) + timedelta(seconds=TOKEN_EXPIRY_SECONDS),
            "iat": datetime.now(timezone.utc)
        }
        
        return jwt.encode(payload, self._get_secret_key(), algorithm="HS256")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode an access token
        
        Args:
            token: JWT access token
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self._get_secret_key(),
                algorithms=["HS256"]
            )
            
            # Check if client is still valid
            client_id = payload.get("sub")
            if not client_id:
                return None
            
            client = self.get_client(client_id)
            if not client or client.get("revoked", False):
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
