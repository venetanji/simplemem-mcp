"""
HTTP server with OAuth authentication for simplemem-mcp

This module provides HTTP endpoints for OAuth token generation
and authenticated MCP access.
"""

import json
from typing import Optional, Dict, Any

import base64

from fastapi import FastAPI, HTTPException, Depends, Request, APIRouter
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, HTMLResponse, RedirectResponse
from starlette.types import ASGIApp
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


class OAuthRequiredMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that requires a valid OAuth access token.

    This is intended to wrap the MCP HTTP transport app, not the OAuth endpoints.
    """

    def __init__(self, app: ASGIApp, oauth_manager: OAuthManager):
        super().__init__(app)
        self._oauth_manager = oauth_manager

    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight without auth.
        if request.method == "OPTIONS":
            return await call_next(request)

        base_url = str(request.base_url).rstrip("/")
        resource_metadata = f"{base_url}/.well-known/oauth-protected-resource"

        auth = request.headers.get("authorization")
        if not auth or not auth.startswith("Bearer "):
            response = JSONResponse(
                status_code=401,
                content={
                    "error": "invalid_request",
                    "error_description": "Missing Bearer token",
                },
            )
            response.headers["WWW-Authenticate"] = (
                'Bearer realm="simplemem-mcp", error="invalid_request", '
                'error_description="Missing Bearer token", '
                f'resource_metadata="{resource_metadata}"'
            )
            return response

        payload = self._oauth_manager.verify_token(auth[7:])
        if not payload:
            response = JSONResponse(
                status_code=401,
                content={
                    "error": "invalid_token",
                    "error_description": "Token is invalid or expired",
                },
            )
            response.headers["WWW-Authenticate"] = (
                'Bearer realm="simplemem-mcp", error="invalid_token", '
                'error_description="Token is invalid or expired", '
                f'resource_metadata="{resource_metadata}"'
            )
            return response

        request.state.oauth = payload
        return await call_next(request)


def attach_oauth_routes(
    app: FastAPI,
    oauth_manager: OAuthManager,
    *,
    route_prefix: str = "",
    issuer_prefix: str = "",
) -> None:
    """Attach OAuth + discovery endpoints to an existing FastAPI app.

    This supports running OAuth endpoints on the same port as the MCP HTTP server,
    optionally under an additional path prefix (e.g., "/mcp").
    """

    route_prefix = (route_prefix or "").rstrip("/")
    issuer_prefix = (issuer_prefix or "").rstrip("/")
    router = APIRouter(prefix=route_prefix)

    def _build_base_url(request: Request) -> str:
        # request.base_url always ends with '/'
        return str(request.base_url).rstrip("/")

    def _issuer(base_url: str) -> str:
        if not issuer_prefix:
            return base_url
        return f"{base_url}{issuer_prefix}"

    def _token_endpoint(base_url: str) -> str:
        return f"{base_url}{route_prefix}/oauth/token" if route_prefix else f"{base_url}/oauth/token"

    def _authorization_endpoint(base_url: str) -> str:
        return (
            f"{base_url}{route_prefix}/oauth/authorize" if route_prefix else f"{base_url}/oauth/authorize"
        )

    def _build_oauth_metadata(request: Request, issuer_path: str = "") -> Dict[str, Any]:
        issuer_path = issuer_path.strip("/")
        base = _build_base_url(request)
        issuer = _issuer(base)
        if issuer_path:
            issuer = f"{issuer}/{issuer_path}"

        return {
            "issuer": issuer,
            "authorization_endpoint": _authorization_endpoint(base),
            "token_endpoint": _token_endpoint(base),
            # This server expects client credentials in the request body (JSON).
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "none",
            ],
            "grant_types_supported": ["client_credentials", "authorization_code"],
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
        }

    def _build_openid_configuration(request: Request, issuer_path: str = "") -> Dict[str, Any]:
        # Minimal OIDC discovery response for clients that probe this endpoint.
        base = _build_base_url(request)
        metadata = _build_oauth_metadata(request, issuer_path)
        return {
            "issuer": metadata["issuer"],
            "authorization_endpoint": metadata["authorization_endpoint"],
            "token_endpoint": metadata["token_endpoint"],
            "token_endpoint_auth_methods_supported": metadata[
                "token_endpoint_auth_methods_supported"
            ],
            "grant_types_supported": metadata["grant_types_supported"],
            # OIDC-required-ish fields (kept minimal; we don't issue ID tokens).
            "response_types_supported": metadata["response_types_supported"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["HS256"],
        }

    def _build_protected_resource_metadata(request: Request, resource_path: str = "") -> Dict[str, Any]:
        """OAuth 2.0 Protected Resource Metadata (RFC 9728)."""

        base = _build_base_url(request)
        resource_path = resource_path.strip("/")

        # Resource identifier should reflect the protected resource base.
        resource = f"{base}{issuer_prefix}" if issuer_prefix else base
        if resource_path:
            resource = f"{resource}/{resource_path}"

        # Authorization server issuer for this resource.
        issuer = _issuer(base)
        if resource_path:
            issuer = f"{issuer}/{resource_path}"

        return {
            "resource": resource,
            "authorization_servers": [issuer],
            # Clients should present access tokens in the Authorization header.
            "bearer_methods_supported": ["header"],
        }

    # OAuth 2.0 Authorization Server Metadata (RFC 8414)
    @router.get("/.well-known/oauth-authorization-server")
    async def oauth_metadata_root(request: Request):
        return _build_oauth_metadata(request)

    @router.get("/.well-known/oauth-authorization-server/{issuer_path:path}")
    async def oauth_metadata_with_path(request: Request, issuer_path: str):
        return _build_oauth_metadata(request, issuer_path)

    # OpenID Connect Discovery (some clients probe this even for pure OAuth flows)
    @router.get("/.well-known/openid-configuration")
    async def openid_config_root(request: Request):
        return _build_openid_configuration(request)

    @router.get("/.well-known/openid-configuration/{issuer_path:path}")
    async def openid_config_with_path(request: Request, issuer_path: str):
        return _build_openid_configuration(request, issuer_path)

    # OAuth 2.0 Protected Resource Metadata (RFC 9728)
    @router.get("/.well-known/oauth-protected-resource")
    async def oauth_protected_resource_root(request: Request):
        return _build_protected_resource_metadata(request)

    @router.get("/.well-known/oauth-protected-resource/{resource_path:path}")
    async def oauth_protected_resource_with_path(request: Request, resource_path: str):
        return _build_protected_resource_metadata(request, resource_path)

    @router.get("/oauth/authorize")
    async def authorize_get(
        request: Request,
        response_type: str,
        client_id: str,
        redirect_uri: str,
        state: Optional[str] = None,
        scope: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: str = "S256",
    ):
        """Authorization endpoint (Authorization Code + PKCE).

        This intentionally uses a simple consent screen (no user accounts). The user
        approves the client to obtain an authorization code.
        """

        if response_type != "code":
            raise HTTPException(status_code=400, detail="unsupported_response_type")

        client = oauth_manager.get_client(client_id)
        if not client or client.get("revoked", False):
            raise HTTPException(status_code=400, detail="invalid_client")

        if not oauth_manager.is_redirect_uri_allowed(redirect_uri):
            raise HTTPException(status_code=400, detail="invalid_redirect_uri")

        if not code_challenge:
            raise HTTPException(status_code=400, detail="missing_code_challenge")

        scope = scope or ""

        # Very small consent page.
        html = f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Authorize {client.get('name','client')}</title>
  </head>
  <body style=\"font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px;\">
    <h1>Authorize access</h1>
    <p><b>{client.get('name','client')}</b> is requesting access to SimpleMem MCP.</p>
    <p><small>Client ID: {client_id}</small></p>
    <form method=\"post\" action=\"{route_prefix}/oauth/authorize\">
      <input type=\"hidden\" name=\"response_type\" value=\"code\" />
      <input type=\"hidden\" name=\"client_id\" value=\"{client_id}\" />
      <input type=\"hidden\" name=\"redirect_uri\" value=\"{redirect_uri}\" />
      <input type=\"hidden\" name=\"state\" value=\"{state or ''}\" />
      <input type=\"hidden\" name=\"scope\" value=\"{scope}\" />
      <input type=\"hidden\" name=\"code_challenge\" value=\"{code_challenge}\" />
      <input type=\"hidden\" name=\"code_challenge_method\" value=\"{code_challenge_method}\" />

      <button name=\"decision\" value=\"approve\" type=\"submit\" style=\"padding:10px 14px;\">Approve</button>
      <button name=\"decision\" value=\"deny\" type=\"submit\" style=\"padding:10px 14px; margin-left: 8px;\">Deny</button>
    </form>
  </body>
</html>"""
        return HTMLResponse(content=html)

    @router.post("/oauth/authorize")
    async def authorize_post(request: Request):
        form = await request.form()
        response_type = form.get("response_type")
        client_id = form.get("client_id")
        redirect_uri = form.get("redirect_uri")
        state = form.get("state")
        scope = form.get("scope")
        code_challenge = form.get("code_challenge")
        code_challenge_method = form.get("code_challenge_method") or "S256"
        decision = form.get("decision")

        if response_type != "code":
            raise HTTPException(status_code=400, detail="unsupported_response_type")
        if not client_id or not redirect_uri:
            raise HTTPException(status_code=400, detail="invalid_request")
        if not oauth_manager.is_redirect_uri_allowed(str(redirect_uri)):
            raise HTTPException(status_code=400, detail="invalid_redirect_uri")

        if decision != "approve":
            # Redirect back with access_denied
            url = str(redirect_uri)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}error=access_denied"
            if state:
                url += f"&state={state}"
            return RedirectResponse(url=url, status_code=302)

        if not code_challenge:
            raise HTTPException(status_code=400, detail="missing_code_challenge")

        try:
            code = oauth_manager.generate_authorization_code(
                client_id=str(client_id),
                redirect_uri=str(redirect_uri),
                code_challenge=str(code_challenge),
                code_challenge_method=str(code_challenge_method),
                scope=str(scope or ""),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        url = str(redirect_uri)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}code={code}"
        if state:
            url += f"&state={state}"
        return RedirectResponse(url=url, status_code=302)

    def _parse_basic_auth(authorization: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not authorization:
            return None, None
        if not authorization.startswith("Basic "):
            return None, None
        try:
            decoded = base64.b64decode(authorization[6:]).decode("utf-8")
            if ":" not in decoded:
                return None, None
            client_id, client_secret = decoded.split(":", 1)
            return client_id, client_secret
        except Exception:
            return None, None

    @router.post("/oauth/token", response_model=TokenResponse)
    async def token_endpoint(request: Request):
        """OAuth token endpoint (client credentials flow).

        Supports:
        - application/x-www-form-urlencoded (recommended)
        - application/json (legacy / test)
        - client authentication via HTTP Basic (client_secret_basic) or body (client_secret_post)
        """

        content_type = (request.headers.get("content-type") or "").lower()
        body: Dict[str, Any] = {}

        if "application/json" in content_type:
            try:
                body = await request.json()
            except Exception:
                body = {}
        else:
            # Default to form parsing, which covers application/x-www-form-urlencoded
            # and multipart/form-data.
            try:
                form = await request.form()
                body = dict(form)
            except Exception:
                body = {}

        grant_type = body.get("grant_type")
        scope = body.get("scope")

        basic_id, basic_secret = _parse_basic_auth(request.headers.get("authorization"))
        client_id = basic_id or body.get("client_id")
        client_secret = basic_secret or body.get("client_secret")

        if grant_type == "client_credentials":
            if not client_id or not client_secret:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "invalid_client",
                        "error_description": "Missing client credentials",
                    },
                    headers={"WWW-Authenticate": "Basic"},
                )

            if not oauth_manager.verify_client(str(client_id), str(client_secret)):
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "invalid_client",
                        "error_description": "Invalid client credentials",
                    },
                    headers={"WWW-Authenticate": "Basic"},
                )

            try:
                access_token = oauth_manager.generate_access_token(str(client_id))
                return TokenResponse(
                    access_token=access_token,
                    token_type="Bearer",
                    expires_in=3600,
                    scope=scope,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "server_error",
                        "error_description": str(e),
                    },
                )

        if grant_type == "authorization_code":
            code = body.get("code")
            redirect_uri = body.get("redirect_uri")
            code_verifier = body.get("code_verifier")

            if not client_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_request",
                        "error_description": "Missing client_id",
                    },
                )
            if not code or not redirect_uri or not code_verifier:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_request",
                        "error_description": "Missing code, redirect_uri, or code_verifier",
                    },
                )

            # For public clients (PKCE), allow auth method 'none'. For confidential clients,
            # accept client_secret if provided.
            if client_secret is not None:
                if not oauth_manager.verify_client(str(client_id), str(client_secret)):
                    raise HTTPException(
                        status_code=401,
                        detail={
                            "error": "invalid_client",
                            "error_description": "Invalid client credentials",
                        },
                        headers={"WWW-Authenticate": "Basic"},
                    )
            else:
                # Still require that the client exists and isn't revoked.
                client = oauth_manager.get_client(str(client_id))
                if not client or client.get("revoked", False):
                    raise HTTPException(
                        status_code=401,
                        detail={
                            "error": "invalid_client",
                            "error_description": "Invalid client",
                        },
                    )

            try:
                result = oauth_manager.consume_authorization_code(
                    code=str(code),
                    client_id=str(client_id),
                    redirect_uri=str(redirect_uri),
                    code_verifier=str(code_verifier),
                )
                access_token = oauth_manager.generate_access_token(result["client_id"])
                return TokenResponse(
                    access_token=access_token,
                    token_type="Bearer",
                    expires_in=3600,
                    scope=result.get("scope") or scope,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_grant",
                        "error_description": str(e),
                    },
                )

        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_grant_type",
                "error_description": "Supported grant types: client_credentials, authorization_code",
            },
        )

    @router.get("/oauth/info")
    async def oauth_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Get information about the current OAuth token."""

        token = credentials.credentials
        payload = oauth_manager.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "error_description": "Token is invalid or expired",
                },
            )

        return {
            "client_id": payload.get("sub"),
            "client_name": payload.get("name"),
            "expires_at": payload.get("exp"),
            "issued_at": payload.get("iat"),
        }

    @router.get("/health")
    async def health():
        return {"status": "ok", "service": "simplemem-mcp-oauth"}

    app.include_router(router)


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

    attach_oauth_routes(app, oauth_manager)
    
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


def run_oauth_server(
    oauth_manager: OAuthManager,
    host: str = "127.0.0.1",
    port: int = 8080,
    access_log: bool = False,
):
    """Run the OAuth server
    
    Args:
        oauth_manager: OAuth manager instance
        host: Host to bind to
        port: Port to bind to
    """
    app = create_oauth_app(oauth_manager)
    uvicorn.run(app, host=host, port=port, access_log=access_log)
