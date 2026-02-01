"""
Main entrypoint for simplemem-mcp server

This module provides the command-line interface for running the MCP server
that connects to simplemem-api.
"""

import os
import sys
import argparse
from .server import create_server, DEFAULT_API_ENDPOINT


def main():
    """Main entry point for the MCP server"""
    parser = argparse.ArgumentParser(
        description="SimpleMem MCP Server - Memory management tools via MCP",
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
  uvx simplemem-mcp
        """
    )
    
    parser.add_argument(
        "--api-endpoint",
        type=str,
        default=None,
        help=f"SimpleMem API endpoint URL (default: {DEFAULT_API_ENDPOINT} or SIMPLEMEM_API_ENDPOINT env var)"
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
    
    args = parser.parse_args()
    
    # Determine API endpoint with priority: CLI arg > env var > default
    api_endpoint = (
        args.api_endpoint or 
        os.environ.get("SIMPLEMEM_API_ENDPOINT") or 
        DEFAULT_API_ENDPOINT
    )
    
    print(f"Starting SimpleMem MCP Server...", file=sys.stderr)
    print(f"API Endpoint: {api_endpoint}", file=sys.stderr)
    print(f"Transport: {args.transport}", file=sys.stderr)
    
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
