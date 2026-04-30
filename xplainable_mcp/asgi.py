"""
ASGI entrypoint for the Xplainable MCP Server.

Run with: uvicorn xplainable_mcp.asgi:app --host 0.0.0.0 --port 8000
"""

import os
import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

from .mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import server module to register tools and load config
import xplainable_mcp.server  # noqa: F401


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "xplainable-mcp",
        "version": "0.1.0",
        "transport": os.getenv("MCP_TRANSPORT", "stdio"),
    })


# Create the ASGI app for production deployment
app = mcp.http_app(
    transport="streamable-http",
    stateless_http=True,
)

logger.info("ASGI app created with Streamable HTTP transport (stateless)")
