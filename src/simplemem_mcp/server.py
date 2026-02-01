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

    async def health(self) -> dict:
        """Check API health and initialization status."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def add_dialogue(self, speaker: str, content: str, timestamp: Optional[str] = None) -> dict:
        """Add a single dialogue/memory to SimpleMem via the API."""
        payload: dict[str, Any] = {"speaker": speaker, "content": content}
        if timestamp:
            payload["timestamp"] = timestamp
        response = await self.client.post(f"{self.base_url}/dialogue", json=payload)
        response.raise_for_status()
        return response.json()

    async def finalize(self) -> dict:
        """Finalize/consolidate memories after dialogue ingestion."""
        response = await self.client.post(f"{self.base_url}/finalize")
        response.raise_for_status()
        return response.json()

    async def query(self, query: str) -> dict:
        """Query memories via semantic search; returns an answer."""
        response = await self.client.post(f"{self.base_url}/query", json={"query": query})
        response.raise_for_status()
        return response.json()

    async def retrieve(self, limit: Optional[int] = None) -> list[dict]:
        """Retrieve raw memories (all or limited)."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        response = await self.client.get(f"{self.base_url}/retrieve", params=params)
        response.raise_for_status()
        return response.json()

    async def stats(self) -> dict:
        """Retrieve memory statistics."""
        response = await self.client.get(f"{self.base_url}/stats")
        response.raise_for_status()
        return response.json()

    async def clear(self, confirmation: bool) -> dict:
        """Clear all memories (requires confirmation=true)."""
        response = await self.client.delete(f"{self.base_url}/clear", json={"confirmation": confirmation})
        response.raise_for_status()
        return response.json()


def create_server(api_endpoint: str = DEFAULT_API_ENDPOINT) -> FastMCP:
    """Create and configure the MCP server"""
    
    # Initialize the FastMCP server
    mcp = FastMCP("simplemem-mcp")
    
    # Initialize API client
    api = SimplememAPI(api_endpoint)

    @mcp.tool()
    async def health() -> str:
        """Check the health and initialization status of simplemem-api."""
        try:
            result = await api.health()
            status = result.get("status")
            version = result.get("version")
            initialized = result.get("simplemem_initialized")
            return (
                "simplemem-api health:\n"
                f"status: {status}\n"
                f"version: {version}\n"
                f"simplemem_initialized: {initialized}"
            )
        except Exception as e:
            return f"Error checking health: {str(e)}"

    @mcp.tool()
    async def dialogue(speaker: str, content: str, timestamp: Optional[str] = None) -> str:
        """Add a single dialogue entry to simplemem-api.

        Important:
            After you finish adding all dialogue entries for a session/batch, call `finalize` once
            to consolidate memories. Until `finalize` is called, queries/retrieve may not reflect
            the newly added dialogue.
        """
        try:
            health_result = await api.health()
            if not health_result.get("simplemem_initialized", False):
                return "Simplemem API storage is not initialized (health.simplemem_initialized=false). Configure the API with MODEL_NAME and API_KEY, then restart it."

            _ = await api.add_dialogue(speaker=speaker, content=content, timestamp=timestamp)
            return f"Successfully added dialogue for speaker '{speaker}'."
        except Exception as e:
            return f"Error adding dialogue: {str(e)}"

    @mcp.tool()
    async def finalize() -> str:
        """Consolidate memories after dialogue ingestion.

        Usage pattern:
            1) Call `dialogue` one or more times to add entries
            2) Call `finalize` once to consolidate memories

        Returns:
            A human-readable success/error message.
        """
        try:
            health_result = await api.health()
            if not health_result.get("simplemem_initialized", False):
                return "Simplemem API is not initialized (health.simplemem_initialized=false). Configure the API with MODEL_NAME and API_KEY, then restart it."

            _ = await api.finalize()
            return "Successfully finalized (consolidated) memories"
        except Exception as e:
            return f"Error finalizing memories: {str(e)}"

    @mcp.tool()
    async def query(query: str) -> str:
        """Ask simplemem-api a question (semantic query) and return its answer."""
        try:
            health_result = await api.health()
            if not health_result.get("simplemem_initialized", False):
                return "Simplemem API querying is not initialized (health.simplemem_initialized=false). Configure the API with MODEL_NAME and API_KEY, then restart it."

            result = await api.query(query)
            answer = result.get("answer")
            if not answer:
                return f"No answer returned for query: {query}"
            return f"Answer:\n{answer}"
        except Exception as e:
            return f"Error querying memories: {str(e)}"

    @mcp.tool()
    async def retrieve(limit: int = 100) -> str:
        """Retrieve raw entries from simplemem-api (most recent first)."""
        try:
            memories = await api.retrieve(limit=limit)
            if not memories:
                return "No entries found"

            output = f"Retrieved {len(memories)} entries:\n"
            for mem in memories:
                value_str = str(mem.get("lossless_restatement", ""))
                output += (
                    f"\n- entry_id: {mem.get('entry_id')}\n"
                    f"  lossless_restatement: {value_str[:120]}{'...' if len(value_str) > 120 else ''}\n"
                )
            return output
        except Exception as e:
            return f"Error retrieving entries: {str(e)}"

    @mcp.tool()
    async def stats() -> str:
        """Retrieve stats from simplemem-api."""
        try:
            result = await api.stats()
            return (
                "simplemem-api stats:\n"
                f"total_entries: {result.get('total_entries')}\n"
                f"memory_path: {result.get('memory_path')}\n"
                f"db_type: {result.get('db_type')}"
            )
        except Exception as e:
            return f"Error retrieving stats: {str(e)}"

    @mcp.tool()
    async def clear(confirmation: bool = False) -> str:
        """Clear all entries in simplemem-api (requires confirmation=True)."""
        if confirmation is not True:
            return "Refusing to clear all memories. Re-run with confirmation=True to proceed."

        try:
            _ = await api.clear(confirmation=True)
            return "Successfully cleared all memories"
        except Exception as e:
            return f"Error clearing memories: {str(e)}"
    
    return mcp
