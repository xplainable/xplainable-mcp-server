"""
Shared MCP instance for the Xplainable MCP Server.

This module provides a single FastMCP instance that is shared across
all tool modules to ensure proper registration.
"""

from fastmcp import FastMCP

# Initialize the shared FastMCP server instance
mcp = FastMCP(
    name="xplainable-mcp",
    version="0.1.0"
)