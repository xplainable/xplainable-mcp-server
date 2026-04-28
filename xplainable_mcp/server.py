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

from fastmcp import FastMCP
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
    api_key: str = Field(..., description="Xplainable API key")
    hostname: str = Field(
        default="https://platform.xplainable.io",
        description="Xplainable API hostname"
    )
    org_id: Optional[str] = Field(None, description="Organization ID")
    team_id: Optional[str] = Field(None, description="Team ID")
    enable_write_tools: bool = Field(
        default=False,
        description="Enable write operations (deploy, activate, etc.)"
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )


def load_config() -> ServerConfig:
    """Load configuration from environment variables."""
    api_key = os.environ.get("XPLAINABLE_API_KEY")
    if not api_key:
        logger.error("XPLAINABLE_API_KEY environment variable not set")
        sys.exit(1)
    
    return ServerConfig(
        api_key=api_key,
        hostname=os.getenv("XPLAINABLE_HOST", "https://platform.xplainable.io"),
        org_id=os.getenv("XPLAINABLE_ORG_ID"),
        team_id=os.getenv("XPLAINABLE_TEAM_ID"),
        enable_write_tools=os.getenv("ENABLE_WRITE_TOOLS", "false").lower() == "true",
        rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
    )


# Initialize configuration
config = load_config()

# Import the shared MCP instance
from .mcp_instance import mcp

# Import get_client from client_manager
from .client_manager import get_client

# Import all modular tools - they self-register with @mcp.tool() decorator
from . import tools


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


@mcp.tool()
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
            "server_version": "0.1.0",
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
            "server_version": "0.1.0",
            "total_tools": 0,
            "enabled_tools": 0,
            "categories": {"error": [{"name": "list_tools", "description": f"Error: {str(e)}", "category": "error"}]},
            "summary": {"error": str(e)}
        }

@mcp.tool()
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
            "hint": "Call tools in step order within each service. "
                    "Tools with depends_on require those tools to be called first.",
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
        
        # Don't initialize client at startup - let it happen lazily when tools are called
        # This prevents the server from crashing if API key is invalid
        
        # Run the MCP server
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()