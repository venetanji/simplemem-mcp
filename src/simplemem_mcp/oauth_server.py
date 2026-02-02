"""
HTTP server with OAuth authentication for simplemem-mcp

This module provides HTTP endpoints for OAuth token generation
and authenticated MCP access.
"""

import json
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

from .oauth import OAuthManager


# Request/Response models
class TokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str
    scope: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: Optional[str] = None


# Security scheme
security = HTTPBearer()


def create_oauth_app(oauth_manager: OAuthManager) -> FastAPI:
    """Create FastAPI app with OAuth endpoints
    
    Args:
        oauth_manager: OAuth manager instance
        
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="SimpleMem MCP OAuth Server",
        description="OAuth authentication server for SimpleMem MCP",
        version="0.1.0"
    )
    
    @app.post("/oauth/token", response_model=TokenResponse)
    async def token_endpoint(request: TokenRequest):
        """OAuth token endpoint (client credentials flow)
        
        This endpoint implements the OAuth 2.0 client credentials grant type.
        AI clients can use this to obtain access tokens.
        """
        # Only support client_credentials grant type for now
        if request.grant_type != "client_credentials":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported_grant_type",
                    "error_description": "Only client_credentials grant type is supported"
                }
            )
        
        # Verify client credentials
        if not oauth_manager.verify_client(request.client_id, request.client_secret):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_client",
                    "error_description": "Invalid client credentials"
                }
            )
        
        # Generate access token
        try:
            access_token = oauth_manager.generate_access_token(request.client_id)
            return TokenResponse(
                access_token=access_token,
                token_type="Bearer",
                expires_in=3600,  # 1 hour
                scope=request.scope
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "server_error",
                    "error_description": str(e)
                }
            )
    
    @app.get("/oauth/info")
    async def oauth_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Get information about the current OAuth token"""
        token = credentials.credentials
        payload = oauth_manager.verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "error_description": "Token is invalid or expired"
                }
            )
        
        return {
            "client_id": payload.get("sub"),
            "client_name": payload.get("name"),
            "expires_at": payload.get("exp"),
            "issued_at": payload.get("iat")
        }
    
    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "ok", "service": "simplemem-mcp-oauth"}
    
    return app


def verify_oauth_token(oauth_manager: OAuthManager, authorization: Optional[str] = None) -> Optional[Dict]:
    """Verify OAuth token from Authorization header
    
    Args:
        oauth_manager: OAuth manager instance
        authorization: Authorization header value
        
    Returns:
        Token payload if valid, None otherwise
    """
    if not authorization:
        return None
    
    # Extract Bearer token
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]  # Remove "Bearer " prefix
    return oauth_manager.verify_token(token)


def run_oauth_server(oauth_manager: OAuthManager, host: str = "127.0.0.1", port: int = 8080):
    """Run the OAuth server
    
    Args:
        oauth_manager: OAuth manager instance
        host: Host to bind to
        port: Port to bind to
    """
    app = create_oauth_app(oauth_manager)
    uvicorn.run(app, host=host, port=port)
