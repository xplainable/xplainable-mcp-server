"""
Xplainable MCP Server implementation using FastMCP.

This server provides secure access to Xplainable AI platform capabilities
through standardized MCP tools.
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastmcp import Context
from fastmcp.server.elicitation import AcceptedElicitation
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from .response_handlers import (
    handle_none_as_empty_list,
    safe_model_dump_list,
    safe_model_dump,
    safe_list_response,
    safe_client_call
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServerConfig(BaseModel):
    """Server configuration model."""
    api_key: str = Field(default="", description="Xplainable API key (optional if using OAuth)")
    hostname: str = Field(
        default="https://platform.xplainable.io",
        description="Xplainable API hostname"
    )
    org_id: Optional[str] = Field(None, description="Organization ID")
    team_id: Optional[str] = Field(None, description="Team ID")
    enable_write_tools: bool = Field(
        default=True,
        description="Enable write operations (deploy, activate, etc.)"
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )


def load_config() -> ServerConfig:
    """Load configuration from environment variables."""
    api_key = os.environ.get("XPLAINABLE_API_KEY", "")
    if not api_key and not os.environ.get("AUTH0_DOMAIN"):
        logger.error("Either XPLAINABLE_API_KEY or AUTH0_DOMAIN must be set")
        sys.exit(1)

    return ServerConfig(
        api_key=api_key,
        hostname=os.getenv("XPLAINABLE_HOST", "https://platform.xplainable.io"),
        org_id=os.getenv("XPLAINABLE_ORG_ID"),
        team_id=os.getenv("XPLAINABLE_TEAM_ID"),
        enable_write_tools=os.getenv("ENABLE_WRITE_TOOLS", "true").lower() == "true",
        rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
    )


# Initialize configuration
config = load_config()

# Import the shared MCP instance
from .mcp_instance import mcp

# Import get_client from client_manager
from .client_manager import get_client

# Shared icon for all xplainable tools + runtime tool generation
from .runtime_tools import XP_ICON, register_client_tools


# ============================================================================
# SESSION TOOLS (team selection)
# ============================================================================


def _fetch_user_teams() -> List[Dict[str, Any]]:
    """Fetch the authenticated user's teams from the API."""
    client = get_client()
    response = client.session._session.get(
        url=f"{client.session.hostname}/v1/teams",
    )
    return client.session.get_response_content(response)


# The three team-selection tools carry an informational "admin" tag.
# INSTRUCTIONS direct callers to recover from 'No team selected' via these.
@mcp.tool(icons=[XP_ICON], tags={"admin"})
def list_user_teams() -> List[Dict[str, Any]]:
    """
    List all teams the authenticated user belongs to.

    Call this first to see which teams are available, then use
    select_team to pick one before calling other tools.

    Returns:
        List of teams with team_id, team_name, organisation_id,
        and organisation_name.
    """
    try:
        result = _fetch_user_teams()
        logger.info(f"Listed {len(result)} teams for user")
        return result
    except Exception as e:
        logger.error(f"Error listing user teams: {e}")
        raise


@mcp.tool(icons=[XP_ICON], tags={"admin"})
def set_active_team(team_id: str) -> Dict[str, str]:
    """
    Set the active team for this session.

    All subsequent tool calls will be scoped to this team.
    Call list_user_teams first to see available teams.

    Args:
        team_id: The team ID to switch to (from list_user_teams).

    Returns:
        Confirmation with the active team_id.
    """
    try:
        from .client_manager import set_active_team as _set_active_team
        _set_active_team(team_id)
        logger.info(f"Active team set to {team_id}")
        return {"status": "ok", "active_team_id": team_id}
    except Exception as e:
        logger.error(f"Error setting active team: {e}")
        raise


@mcp.tool(icons=[XP_ICON], tags={"admin"})
async def select_team(ctx: Context) -> Dict[str, str]:
    """
    Interactively select the active team for this session.

    Presents a dropdown UI to the user with their available teams.
    All subsequent tool calls will be scoped to the selected team.
    Call this before using any other tools.

    Returns:
        Confirmation with the active team_id and team_name.
    """
    from typing import Literal
    from .client_manager import set_active_team as _set_active_team

    try:
        teams = _fetch_user_teams()

        if not teams:
            return {"error": "No teams found for this user"}

        if len(teams) == 1:
            # Only one team — auto-select it
            _set_active_team(teams[0]["team_id"])
            logger.info(f"Auto-selected only team: {teams[0]['team_name']}")
            return {
                "status": "ok",
                "active_team_id": teams[0]["team_id"],
                "active_team_name": teams[0]["team_name"],
            }

        # Build team name → id mapping
        team_map = {t["team_name"]: t["team_id"] for t in teams}
        team_names = list(team_map.keys())

        # Present dropdown to user via elicitation
        TeamChoice = Literal[tuple(team_names)]  # type: ignore[valid-type]
        result = await ctx.elicit(
            message="Select your team to continue:",
            response_type=TeamChoice,
        )

        if not isinstance(result, AcceptedElicitation):
            return {"error": "Team selection was cancelled"}

        selected_name = result.data
        selected_id = team_map[selected_name]
        _set_active_team(selected_id)
        logger.info(f"User selected team: {selected_name} ({selected_id})")

        return {
            "status": "ok",
            "active_team_id": selected_id,
            "active_team_name": selected_name,
        }

    except Exception as e:
        logger.error(f"Error in select_team: {e}")
        raise


# ============================================================================
# RUNTIME TOOL REGISTRATION
# ============================================================================

# Register all client @mcp_tool methods as MCP tools (runtime generation from
# the installed xplainable-client's registry — no checked-in codegen).
register_client_tools(mcp)

# Hand-written docs tools (self-register on import)
from . import docs_tools  # noqa: E402,F401



def main():
    """Main entry point for the server."""
    try:
        # Log startup information
        logger.info("Starting Xplainable MCP Server")
        logger.info(f"Write tools enabled: {config.enable_write_tools}")
        logger.info(f"Rate limiting enabled: {config.rate_limit_enabled}")

        transport = os.getenv("MCP_TRANSPORT", "stdio")
        logger.info(f"Transport: {transport}")

        if transport == "streamable-http":
            host = os.getenv("MCP_HOST", "0.0.0.0")
            port = int(os.getenv("MCP_PORT", "8000"))
            mcp.run(
                transport="streamable-http",
                host=host,
                port=port,
            )
        else:
            mcp.run()

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()