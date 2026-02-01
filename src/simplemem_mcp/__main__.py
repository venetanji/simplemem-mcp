"""
Main entrypoint for simplemem-mcp server

This module provides the command-line interface for running the MCP server.
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
    
    args = parser.parse_args()
    
    # Determine API endpoint with priority: CLI arg > env var > default
    api_endpoint = (
        args.api_endpoint or 
        os.environ.get("SIMPLEMEM_API_ENDPOINT") or 
        DEFAULT_API_ENDPOINT
    )
    
    print(f"Starting SimpleMem MCP Server...", file=sys.stderr)
    print(f"API Endpoint: {api_endpoint}", file=sys.stderr)
    
    # Create and run the server
    mcp = create_server(api_endpoint)
    mcp.run()


if __name__ == "__main__":
    main()
