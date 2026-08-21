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

from fastmcp import FastMCP, Context
from fastmcp.server.elicitation import AcceptedElicitation
from mcp.types import Icon
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

# Shared icon for all xplainable tools
XP_ICON = Icon(src="https://xplainable.io/assets/xplainable-icon.png", mimeType="image/png")

# Import all modular tools - they self-register with @mcp.tool(icons=[XP_ICON]) decorator
from . import __version__, tools


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

def categorize_tool(tool_name: str, tool_func) -> str:
    """
    Automatically categorize a tool based on its name and function.
    
    Args:
        tool_name: Name of the tool
        tool_func: FunctionTool object from FastMCP registry
        
    Returns:
        Category string: 'discovery', 'read', 'write', or 'admin'
    """
    # Discovery tools
    if tool_name in ['list_tools']:
        return 'discovery'
    
    # Write operations (only enabled when config allows)
    write_patterns = [
        'generate', 'create', 'activate', 'deactivate', 'deploy', 'delete', 
        'update', 'modify', 'set', 'enable', 'disable', 'gpt_'
    ]
    if any(pattern in tool_name.lower() for pattern in write_patterns):
        return 'write' if config.enable_write_tools else 'disabled'
    
    # Admin tools (if any)
    admin_patterns = ['admin', 'config', 'manage_users']
    if any(pattern in tool_name.lower() for pattern in admin_patterns):
        return 'admin'
    
    # Default to read operations
    return 'read'


def extract_tool_info(tool_name: str, tool_func) -> Dict[str, Any]:
    """
    Extract tool information from the function signature and docstring.
    
    Args:
        tool_name: Name of the tool
        tool_func: FunctionTool object from FastMCP registry
        
    Returns:
        Dictionary with tool information
    """
    import inspect
    
    # Handle FastMCP FunctionTool objects
    actual_func = tool_func
    if hasattr(tool_func, 'func'):
        actual_func = tool_func.func
    elif hasattr(tool_func, '_func'):
        actual_func = tool_func._func
    elif hasattr(tool_func, '__call__') and not inspect.isfunction(tool_func):
        # Try to get the underlying function from callable objects
        if hasattr(tool_func, '__func__'):
            actual_func = tool_func.__func__
    
    try:
        # Get function signature
        sig = inspect.signature(actual_func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            param_info = {
                "name": param_name,
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                "required": param.default == inspect.Parameter.empty,
                "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                "description": f"Parameter {param_name}"
            }
            parameters.append(param_info)
        
        # Extract description from docstring
        doc = inspect.getdoc(actual_func) or f"Tool: {tool_name}"
        description = doc.split('\n')[0].strip() if doc else f"Tool: {tool_name}"
    except Exception as e:
        logger.warning(f"Could not extract signature for {tool_name}: {e}")
        parameters = []
        description = f"Tool: {tool_name}"
    
    return {
        "name": tool_name,
        "description": description,
        "parameters": parameters
    }


def _discover_available_tools() -> List[Dict[str, Any]]:
    """
    Truly dynamically discover available tools by introspecting xplainable-client classes.
    
    This directly introspects client class methods and extracts their signatures and docstrings.
    
    Returns:
        List of tool dictionaries with name, description, category, parameters
    """
    try:
        import inspect
        logger.info("Starting true dynamic tool discovery via class introspection")
        
        # Import client classes directly (no instantiation needed)
        from xplainable_client.client.models import ModelsClient
        from xplainable_client.client.deployments import DeploymentsClient  
        from xplainable_client.client.preprocessing import PreprocessingClient
        # TODO: Add other clients like GPTClient, CollectionsClient when needed
        
        available_tools = []
        
        # Add utility tools that don't correspond to client methods
        available_tools.extend([
            {
                "name": "list_tools",
                "description": "List all available MCP tools and their descriptions",
                "category": "discovery",
                "parameters": []
            },
            {
                "name": "get_connection_info", 
                "description": "Return connection and user info for diagnostics",
                "category": "read",
                "parameters": []
            },
            {
                "name": "misc_get_version_info",
                "description": "Return client/server version info", 
                "category": "read",
                "parameters": []
            }
        ])
        
        # Map client classes to their module names  
        client_modules = [
            ("models", ModelsClient),
            ("deployments", DeploymentsClient),
            ("preprocessing", PreprocessingClient)
        ]
        
        # Introspect each client class
        for module_name, client_class in client_modules:
            logger.info(f"Introspecting {module_name} client...")
            
            for name, method in inspect.getmembers(client_class, predicate=inspect.isfunction):
                # Skip private methods and HTTP convenience methods
                if name.startswith('_') or name.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                    continue
                    
                # Skip methods that require complex objects (DataFrames, pipelines, etc.)
                sig = inspect.signature(method)
                skip_method = False
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    # Skip methods that take complex types as parameters
                    if param.annotation and hasattr(param.annotation, '__module__'):
                        param_module = getattr(param.annotation, '__module__', '')
                        if any(mod in param_module for mod in ['pandas', 'xplainable.preprocessing']):
                            skip_method = True
                            break
                
                if skip_method:
                    logger.debug(f"Skipping {name} - requires complex parameters")
                    continue
                
                try:
                    # Extract method info
                    doc = inspect.getdoc(method) or ''
                    description = doc.split('\n')[0] if doc else f"{name.replace('_', ' ').title()}"
                    
                    # Determine category based on method name
                    write_keywords = ["create", "add", "update", "delete", "deploy", "activate", "deactivate", "generate", "revoke"]
                    is_write = any(keyword in name.lower() for keyword in write_keywords)
                    category = "write" if is_write else "read"
                    
                    # Extract parameters
                    parameters = []
                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                            
                        # Convert type annotation to string
                        param_type = "str"  # default
                        if param.annotation != param.empty:
                            type_str = str(param.annotation)
                            if 'int' in type_str.lower():
                                param_type = "int"
                            elif 'bool' in type_str.lower():
                                param_type = "bool"
                            elif 'optional' in type_str.lower() or 'union' in type_str.lower():
                                param_type = "Optional[str]"
                        
                        param_info = {
                            "name": param_name,
                            "type": param_type,
                            "required": param.default == param.empty,
                            "description": f"Parameter {param_name}"
                        }
                        
                        if param.default != param.empty:
                            param_info["default"] = param.default
                            
                        parameters.append(param_info)
                    
                    # Create tool definition
                    tool = {
                        "name": name,  # Use actual method name
                        "description": description,
                        "category": category,
                        "parameters": parameters
                    }
                    
                    available_tools.append(tool)
                    logger.debug(f"Added tool: {name} ({category})")
                    
                except Exception as e:
                    logger.warning(f"Error processing method {module_name}.{name}: {e}")
                    continue
        
        logger.info(f"Dynamic tool discovery completed: found {len(available_tools)} tools")
        return available_tools
        
    except Exception as e:
        logger.error(f"Dynamic tool discovery failed: {e}")
        
        # Clean fallback - just return the basic tools we know work
        logger.info("Using minimal fallback tool list")
        return [
            {"name": "list_tools", "description": "List all available MCP tools", "category": "discovery", "parameters": []},
            {"name": "get_connection_info", "description": "Get connection information", "category": "read", "parameters": []},
            {"name": "list_team_models", "description": "List team models", "category": "read", "parameters": []},
            {"name": "get_model", "description": "Get model details", "category": "read", "parameters": [{"name": "model_id", "type": "str", "required": True}]},
            {"name": "list_deployments", "description": "List deployments", "category": "read", "parameters": []},
            {"name": "misc_get_version_info", "description": "Get version info", "category": "read", "parameters": []}
        ]


@mcp.tool(icons=[XP_ICON])
def list_tools() -> Dict[str, Any]:
    """
    List all available MCP tools and their descriptions.
    
    Returns:
        Dictionary containing tool information organized by category
    """
    try:
        # Use modular tool discovery system
        from .tool_discovery import get_modular_tools_registry
        discovery = get_modular_tools_registry()
        available_tools = discovery.get_tools_by_category()
        
        # Filter tools based on configuration
        tools_dict = {"discovery": [], "read": [], "write": [], "admin": [], "inference": [], "analysis": []}
        
        for category, tools in available_tools.items():
            for tool in tools:
                # Skip write tools if not enabled
                if category == "write" and not config.enable_write_tools:
                    continue
                
                # Convert ToolInfo to dict format expected by rest of function
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "module": tool.module,
                    "parameters": tool.parameters,
                    "enabled": tool.enabled
                }
                
                if category not in tools_dict:
                    tools_dict[category] = []
                tools_dict[category].append(tool_dict)
        
        # Remove empty categories
        tools_dict = {k: v for k, v in tools_dict.items() if v}
        
        # Calculate summary
        summary = {
            "discovery_tools": len(tools_dict.get("discovery", [])),
            "read_tools": len(tools_dict.get("read", [])),
            "write_tools": len(tools_dict.get("write", [])),
            "admin_tools": len(tools_dict.get("admin", [])),
            "inference_tools": len(tools_dict.get("inference", [])),
            "analysis_tools": len(tools_dict.get("analysis", [])),
            "write_tools_enabled": config.enable_write_tools
        }
        
        total_tools = sum(summary[k] for k in summary if k != 'write_tools_enabled')
        
        result = {
            "server_version": __version__,
            "total_tools": total_tools,
            "enabled_tools": total_tools,
            "categories": tools_dict,
            "summary": summary
        }
        
        logger.info(f"Listed {total_tools} available tools")
        return result
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        # Fallback to basic info if introspection fails
        return {
            "server_version": __version__,
            "total_tools": 0,
            "enabled_tools": 0,
            "categories": {"error": [{"name": "list_tools", "description": f"Error: {str(e)}", "category": "error"}]},
            "summary": {"error": str(e)}
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
    try:
        from .tool_discovery import ModularToolDiscovery
        discovery = ModularToolDiscovery()
        all_tools = discovery.discover_all_tools()

        # Group tools by service module
        services: Dict[str, Dict[str, Any]] = {}
        for tool_name, tool_info in all_tools.items():
            service = tool_info.module
            if service not in services:
                services[service] = {"steps": [], "tools": []}

            # Parse workflow metadata from docstring
            step_num = 0
            depends_on_list = []
            if tool_info.description:
                for line in (tool_info.description + "\n").splitlines():
                    pass  # description is first line only

            # Parse full docstring from the tool file for Workflow: line
            doc_lines = _get_tool_docstring(service, tool_name)
            for line in doc_lines:
                stripped = line.strip()
                if stripped.startswith("Workflow:"):
                    workflow_text = stripped[len("Workflow:"):].strip()
                    # Parse "Step N of service"
                    import re
                    step_match = re.search(r'Step (\d+)', workflow_text)
                    if step_match:
                        step_num = int(step_match.group(1))
                    # Parse "Run after: tool1, tool2"
                    after_match = re.search(r'Run after: (.+?)\.', workflow_text)
                    if after_match:
                        depends_on_list = [
                            t.strip() for t in after_match.group(1).split(',')
                        ]

            entry = {
                "tool": tool_name,
                "description": tool_info.description,
                "category": tool_info.category,
                "parameters": [p["name"] for p in tool_info.parameters],
            }

            if step_num:
                entry["step"] = step_num
            if depends_on_list:
                entry["depends_on"] = depends_on_list

            if step_num:
                services[service]["steps"].append(entry)
            else:
                services[service]["tools"].append(entry)

        # Sort steps within each service
        for service_data in services.values():
            service_data["steps"].sort(key=lambda x: x.get("step", 0))
            # Remove empty sections
            if not service_data["steps"]:
                del service_data["steps"]
            if not service_data["tools"]:
                del service_data["tools"]

        # Filter disabled write tools
        if not config.enable_write_tools:
            for service_data in services.values():
                for section in ["steps", "tools"]:
                    if section in service_data:
                        service_data[section] = [
                            t for t in service_data[section]
                            if t["category"] != "write"
                        ]
                        if not service_data[section]:
                            del service_data[section]

        # Remove empty services
        services = {k: v for k, v in services.items() if v}

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


def _get_tool_docstring(service: str, tool_name: str) -> List[str]:
    """Read the full docstring of a tool from its service file."""
    import ast
    from pathlib import Path

    tools_dir = Path(__file__).parent / "tools"
    file_path = tools_dir / f"{service}.py"
    if not file_path.exists():
        return []

    try:
        tree = ast.parse(file_path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == tool_name:
                if (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)):
                    return node.body[0].value.value.splitlines()
    except Exception:
        pass
    return []


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