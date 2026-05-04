"""
Shared MCP instance for the Xplainable MCP Server.

This module provides a single FastMCP instance that is shared across
all tool modules to ensure proper registration.
"""

import os
from fastmcp import FastMCP
from mcp.types import Icon
from . import __version__

# Auth is only configured when running in HTTP transport mode.
# In stdio mode (local dev), no auth is applied.
auth_provider = None

if os.getenv("MCP_TRANSPORT") == "streamable-http":
    auth0_domain = os.getenv("AUTH0_DOMAIN")
    auth0_client_id = os.getenv("AUTH0_CLIENT_ID")
    auth0_client_secret = os.getenv("AUTH0_CLIENT_SECRET")
    auth0_audience = os.getenv("AUTH0_AUDIENCE", "")
    mcp_server_url = os.getenv("MCP_SERVER_URL", "https://mcp.xplainable.io")

    if auth0_domain and auth0_client_id and auth0_client_secret:
        from fastmcp.server.auth.providers.auth0 import Auth0Provider

        auth_provider = Auth0Provider(
            config_url=f"https://{auth0_domain}/.well-known/openid-configuration",
            client_id=auth0_client_id,
            client_secret=auth0_client_secret,
            audience=auth0_audience,
            base_url=mcp_server_url,
            redirect_path="/auth/callback",
            require_authorization_consent="external",
        )

# Initialize the shared FastMCP server instance
mcp = FastMCP(
    name="Xplainable",
    version=__version__,
    auth=auth_provider,
    website_url="https://xplainable.io",
    icons=[
        Icon(
            src="https://xplainable.io/assets/xplainable-icon.png",
            mimeType="image/png",
        ),
    ],
    instructions=(
        "IMPORTANT: You MUST call select_team (or list_user_teams then "
        "set_active_team) as your very first action before calling any "
        "other tool. All tools require an active team to be set. "
        "If a tool returns 'No team selected', call select_team first."
    ),
)
