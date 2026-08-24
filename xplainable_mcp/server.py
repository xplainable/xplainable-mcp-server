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

from . import __version__


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


# The three team-selection tools are tagged "curated" so they stay visible
# on the default (include_tags={"workflow", "curated"}) surface: INSTRUCTIONS
# direct callers to recover from 'No team selected' via these tools, so they
# must be reachable without XPLAINABLE_ADVANCED_TOOLS.
@mcp.tool(icons=[XP_ICON], tags={"admin", "curated"})
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


@mcp.tool(icons=[XP_ICON], tags={"admin", "curated"})
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


@mcp.tool(icons=[XP_ICON], tags={"admin", "curated"})
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
# CHART TOOLS (hand-written; the sync workflow owns tools/, not this file)
# ============================================================================


@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})
def workflow_get_run_charts(run_id: str, max_charts: int = 10):
    """
    Fetch the rendered charts for a training run as images.

    Call after workflow_wait_for_update shows the plots phase has
    produced charts (tool_complete events mentioning "Chart N").
    Returns each successfully rendered chart as an inline PNG image
    preceded by a caption with the analytical question it answers,
    so the host can display them directly in the conversation.

    Category: workflow
    Workflow: Run after: workflow_wait_for_update (plots phase).
    """
    import base64 as _b64
    from fastmcp.utilities.types import Image

    try:
        client = get_client()
        result = client.workflow.get_run_charts(run_id, max_charts=max_charts)
        if result.get("error"):
            return result  # coaching dict from the client
        charts = result.get("charts") or []

        content: List[Any] = []
        for chart in charts:
            try:
                image_bytes = _b64.b64decode(chart["raster"])
            except Exception:
                logger.warning(
                    f"Chart {chart.get('index')} of run {run_id} has an undecodable raster; skipping"
                )
                continue
            content.append(f"Chart {len(content) // 2 + 1}: {chart.get('question')}")
            content.append(Image(data=image_bytes, format="png"))

        if not content:
            return {
                "status": "no_charts",
                "message": (
                    "No rendered charts found for this run yet. If the plots "
                    "phase is still running, poll workflow_wait_for_update and retry."
                ),
                "total_charts": result.get("total_charts", 0),
            }

        logger.info(f"Returning {len(content) // 2} chart image(s) for run {run_id}")
        return content
    except Exception as e:
        logger.error(f"Error in workflow_get_run_charts: {e}")
        raise


# ============================================================================
# DISCOVERY/METADATA TOOLS
# ============================================================================


def _first_doc_line(text) -> str:
    if not text:
        return ""
    for line in text.strip().splitlines():
        if line.strip():
            return line.strip()
    return ""


@mcp.tool(icons=[XP_ICON])
async def list_tools() -> Dict[str, Any]:
    """
    List all registered MCP tools grouped by category with their tags.

    Introspects the live FastMCP registry (unfiltered, i.e. the full
    surface regardless of the active include_tags tier).

    Returns:
        Dictionary containing tool information organized by category
    """
    tools = await mcp.get_tools()
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for name, tool in sorted(tools.items()):
        tags = set(tool.tags or set())
        category = next(
            (t for t in ("read", "write", "workflow", "analysis", "inference", "admin")
             if t in tags),
            "other",
        )
        categories.setdefault(category, []).append({
            "name": name,
            "description": _first_doc_line(tool.description),
            "tags": sorted(tags),
        })
    logger.info(f"Listed {len(tools)} registered tools")
    return {
        "server_version": __version__,
        "total_tools": len(tools),
        "categories": categories,
        "summary": {category: len(items) for category, items in categories.items()},
    }


@mcp.tool(icons=[XP_ICON])
def get_workflows() -> Dict[str, Any]:
    """
    Get available tool workflows grouped by service with execution order.

    Use this tool first to understand which tools are available and what
    order to call them in. Tools with a 'step' are part of a sequential
    workflow. Tools listed under 'depends_on' must be called before the
    current tool.

    Returns:
        Dictionary of services, each containing ordered steps and
        standalone tools.
    """
    from .runtime_tools import derive_tool_name, iter_registry_entries

    try:
        services: Dict[str, Dict[str, Any]] = {}
        for entry in iter_registry_entries():
            tool_name = derive_tool_name(entry)
            service = tool_name.split("_", 1)[0]
            bucket = services.setdefault(service, {"steps": [], "tools": []})
            item = {
                "tool": tool_name,
                "description": _first_doc_line(entry["docstring"]),
                "category": entry["category"].value,
                "parameters": list(entry["parameters"].keys()),
            }
            if entry["step"]:
                item["step"] = entry["step"]
            if entry["depends_on"]:
                item["depends_on"] = entry["depends_on"]
            bucket["steps" if entry["step"] else "tools"].append(item)

        for service_data in services.values():
            service_data["steps"].sort(key=lambda x: x["step"])
            for key in ("steps", "tools"):
                if not service_data[key]:
                    del service_data[key]

        return {
            "total_services": len(services),
            "services": services,
            "hint": "Start by calling select_team to pick a team. "
                    "Then call tools in step order within each service. "
                    "Tools with depends_on require those tools first.",
        }
    except Exception as e:
        logger.error(f"Error building workflows: {e}")
        return {"error": str(e)}


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