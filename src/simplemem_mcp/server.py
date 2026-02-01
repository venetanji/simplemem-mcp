"""
SimpleMem MCP Server Implementation

This module implements the MCP server using FastMCP to provide
memory management tools that interface with simplemem-api.
"""

import httpx
from typing import Optional, Any
from fastmcp import FastMCP

# Default API endpoint - localhost
DEFAULT_API_ENDPOINT = "http://localhost:8000"


class SimplememAPI:
    """Client for interacting with simplemem-api"""
    
    def __init__(self, base_url: str = DEFAULT_API_ENDPOINT):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def store_memory(self, key: str, value: Any, metadata: Optional[dict] = None) -> dict:
        """Store a memory item"""
        payload = {
            "key": key,
            "value": value,
        }
        if metadata:
            payload["metadata"] = metadata
        
        response = await self.client.post(f"{self.base_url}/memories", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def retrieve_memory(self, key: str) -> Optional[dict]:
        """Retrieve a memory item by key"""
        try:
            response = await self.client.get(f"{self.base_url}/memories/{key}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def list_memories(self, limit: int = 100, offset: int = 0) -> dict:
        """List all memory items"""
        params = {"limit": limit, "offset": offset}
        response = await self.client.get(f"{self.base_url}/memories", params=params)
        response.raise_for_status()
        return response.json()
    
    async def delete_memory(self, key: str) -> bool:
        """Delete a memory item"""
        try:
            response = await self.client.delete(f"{self.base_url}/memories/{key}")
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise
    
    async def search_memories(self, query: str, limit: int = 10) -> dict:
        """Search memories by query"""
        params = {"q": query, "limit": limit}
        response = await self.client.get(f"{self.base_url}/memories/search", params=params)
        response.raise_for_status()
        return response.json()


def create_server(api_endpoint: str = DEFAULT_API_ENDPOINT) -> FastMCP:
    """Create and configure the MCP server"""
    
    # Initialize the FastMCP server
    mcp = FastMCP("simplemem-mcp")
    
    # Initialize API client
    api = SimplememAPI(api_endpoint)
    
    @mcp.tool()
    async def store_memory(key: str, value: str, metadata: Optional[dict] = None) -> str:
        """
        Store a memory item in simplemem.
        
        Args:
            key: Unique identifier for the memory
            value: The content to store
            metadata: Optional metadata dictionary
        
        Returns:
            Success message with stored key
        """
        try:
            result = await api.store_memory(key, value, metadata)
            return f"Successfully stored memory with key: {key}"
        except Exception as e:
            return f"Error storing memory: {str(e)}"
    
    @mcp.tool()
    async def retrieve_memory(key: str) -> str:
        """
        Retrieve a memory item by its key.
        
        Args:
            key: The unique identifier of the memory to retrieve
        
        Returns:
            The memory content or error message
        """
        try:
            result = await api.retrieve_memory(key)
            if result is None:
                return f"Memory with key '{key}' not found"
            return f"Memory found:\nKey: {result.get('key')}\nValue: {result.get('value')}\nMetadata: {result.get('metadata', {})}"
        except Exception as e:
            return f"Error retrieving memory: {str(e)}"
    
    @mcp.tool()
    async def list_memories(limit: int = 100, offset: int = 0) -> str:
        """
        List all stored memories.
        
        Args:
            limit: Maximum number of memories to return (default: 100)
            offset: Number of memories to skip (default: 0)
        
        Returns:
            List of memories or error message
        """
        try:
            result = await api.list_memories(limit, offset)
            memories = result.get('memories', [])
            if not memories:
                return "No memories found"
            
            output = f"Found {len(memories)} memories:\n"
            for mem in memories:
                value_str = str(mem.get('value', ''))
                output += f"\n- Key: {mem.get('key')}\n  Value: {value_str[:100]}{'...' if len(value_str) > 100 else ''}\n"
            return output
        except Exception as e:
            return f"Error listing memories: {str(e)}"
    
    @mcp.tool()
    async def delete_memory(key: str) -> str:
        """
        Delete a memory item by its key.
        
        Args:
            key: The unique identifier of the memory to delete
        
        Returns:
            Success or error message
        """
        try:
            success = await api.delete_memory(key)
            if success:
                return f"Successfully deleted memory with key: {key}"
            else:
                return f"Memory with key '{key}' not found"
        except Exception as e:
            return f"Error deleting memory: {str(e)}"
    
    @mcp.tool()
    async def search_memories(query: str, limit: int = 10) -> str:
        """
        Search memories by query string.
        
        Args:
            query: Search query string
            limit: Maximum number of results (default: 10)
        
        Returns:
            Search results or error message
        """
        try:
            result = await api.search_memories(query, limit)
            memories = result.get('results', [])
            if not memories:
                return f"No memories found matching query: {query}"
            
            output = f"Found {len(memories)} memories matching '{query}':\n"
            for mem in memories:
                value_str = str(mem.get('value', ''))
                output += f"\n- Key: {mem.get('key')}\n  Value: {value_str[:100]}{'...' if len(value_str) > 100 else ''}\n"
            return output
        except Exception as e:
            return f"Error searching memories: {str(e)}"
    
    return mcp
