"""
Main entrypoint for simplemem-mcp server

This module provides the command-line interface for running the MCP server
that connects to simplemem-api, with OAuth authentication support.
"""

import os
import sys
import argparse
from .server import create_server, DEFAULT_API_ENDPOINT
from .oauth import OAuthManager
from .oauth_server import run_oauth_server


def main():
    """Main entry point for the MCP server"""
    parser = argparse.ArgumentParser(
        description="SimpleMem MCP Server - Memory management tools via MCP with OAuth support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default localhost endpoint
  uvx simplemem-mcp

    # Run over HTTP (streamable HTTP transport)
    uvx simplemem-mcp --transport streamable-http --host 127.0.0.1 --port 3333
  
  # Run with custom API endpoint
  uvx simplemem-mcp --api-endpoint http://api.example.com:8080
  
  # Use environment variable
    export SIMPLEMEM_API_ENDPOINT=http://api.example.com:8080
    # (Alias)
    export SIMPLEMEM_API_URL=http://api.example.com:8080
  uvx simplemem-mcp

  # OAuth commands
  uvx simplemem-mcp oauth-generate-client --name openai --description "OpenAI integration"
  uvx simplemem-mcp oauth-list-clients
  uvx simplemem-mcp oauth-revoke-client --client-id <client_id>
  uvx simplemem-mcp oauth-server --host 0.0.0.0 --port 8080
        """
    )
    
    # Add subparsers for OAuth commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Main server command (default)
    server_parser = subparsers.add_parser('serve', help='Run the MCP server (default)')
    _add_server_arguments(server_parser)
    
    # OAuth commands
    oauth_generate_parser = subparsers.add_parser(
        'oauth-generate-client',
        help='Generate a new OAuth client'
    )
    oauth_generate_parser.add_argument('--name', required=True, help='Client name')
    oauth_generate_parser.add_argument('--description', default='', help='Client description')
    
    oauth_list_parser = subparsers.add_parser(
        'oauth-list-clients',
        help='List all OAuth clients'
    )
    
    oauth_revoke_parser = subparsers.add_parser(
        'oauth-revoke-client',
        help='Revoke an OAuth client'
    )
    oauth_revoke_parser.add_argument('--client-id', required=True, help='Client ID to revoke')
    
    oauth_server_parser = subparsers.add_parser(
        'oauth-server',
        help='Run OAuth authentication server'
    )
    oauth_server_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    oauth_server_parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    
    # Parse arguments - if no command specified, add server arguments to main parser
    # This allows running without 'serve' subcommand for backward compatibility
    _add_server_arguments(parser)
    args = parser.parse_args()
    
    # Handle OAuth commands
    if args.command == 'oauth-generate-client':
        oauth_manager = OAuthManager()
        client = oauth_manager.generate_client(args.name, args.description)
        print("\n=== OAuth Client Generated ===")
        print(f"Client ID: {client['client_id']}")
        print(f"Client Secret: {client['client_secret']}")
        print(f"Name: {client['name']}")
        if client['description']:
            print(f"Description: {client['description']}")
        print("\nIMPORTANT: Save the client secret securely. It will not be shown again.")
        return
    
    elif args.command == 'oauth-list-clients':
        oauth_manager = OAuthManager()
        clients = oauth_manager.list_clients()
        if not clients:
            print("No OAuth clients registered.")
            return
        print("\n=== Registered OAuth Clients ===")
        for client in clients:
            status = "REVOKED" if client['revoked'] else "Active"
            print(f"\nClient ID: {client['client_id']}")
            print(f"  Name: {client['name']}")
            print(f"  Description: {client.get('description', 'N/A')}")
            print(f"  Created: {client['created_at']}")
            print(f"  Status: {status}")
        return
    
    elif args.command == 'oauth-revoke-client':
        oauth_manager = OAuthManager()
        if oauth_manager.revoke_client(args.client_id):
            print(f"Successfully revoked client: {args.client_id}")
        else:
            print(f"Client not found: {args.client_id}")
            sys.exit(1)
        return
    
    elif args.command == 'oauth-server':
        oauth_manager = OAuthManager()
        print(f"Starting OAuth server on {args.host}:{args.port}")
        print(f"\nOAuth Token Endpoint: http://{args.host}:{args.port}/oauth/token")
        print("Use client_credentials grant type to obtain access tokens")
        run_oauth_server(oauth_manager, args.host, args.port)
        return
    
    # Default: run MCP server
    _run_server(args)


def _add_server_arguments(parser):
    """Add server-related arguments to a parser"""
    parser.add_argument(
        "--api-endpoint",
        type=str,
        default=None,
        help=(
            f"SimpleMem API endpoint URL (default: {DEFAULT_API_ENDPOINT} or "
            "SIMPLEMEM_API_ENDPOINT / SIMPLEMEM_API_URL env var)"
        ),
    )

    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="Transport to use for serving MCP (default: stdio).",
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to for HTTP transports (sse/streamable-http).",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to for HTTP transports (sse/streamable-http).",
    )

    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path for HTTP transports endpoint (optional; FastMCP provides defaults).",
    )
    
    parser.add_argument(
        "--oauth-required",
        action="store_true",
        help="Require OAuth authentication for HTTP transports (default: False)",
    )


def _run_server(args):
    """Run the MCP server"""
    # Determine API endpoint with priority: CLI arg > env var > default
    api_endpoint = (
        args.api_endpoint or 
        os.environ.get("SIMPLEMEM_API_ENDPOINT") or 
        os.environ.get("SIMPLEMEM_API_URL") or 
        DEFAULT_API_ENDPOINT
    )
    
    print(f"Starting SimpleMem MCP Server...", file=sys.stderr)
    print(f"API Endpoint: {api_endpoint}", file=sys.stderr)
    print(f"Transport: {args.transport}", file=sys.stderr)
    
    # Display OAuth clients if any exist
    if args.transport in ["sse", "streamable-http"]:
        oauth_manager = OAuthManager()
        clients = oauth_manager.list_clients()
        active_clients = [c for c in clients if not c['revoked']]
        if active_clients:
            print(f"\n=== Active OAuth Clients ({len(active_clients)}) ===", file=sys.stderr)
            for client in active_clients:
                print(f"  - {client['name']} (ID: {client['client_id']})", file=sys.stderr)
            if args.oauth_required:
                print("  OAuth authentication: REQUIRED", file=sys.stderr)
            else:
                print("  OAuth authentication: Optional (use --oauth-required to enforce)", file=sys.stderr)
    
    # Create and run the server
    mcp = create_server(api_endpoint)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    transport_kwargs = {}
    if args.host is not None:
        transport_kwargs["host"] = args.host
    if args.port is not None:
        transport_kwargs["port"] = args.port
    if args.path is not None:
        transport_kwargs["path"] = args.path

    mcp.run(transport=args.transport, **transport_kwargs)


if __name__ == "__main__":
    main()
