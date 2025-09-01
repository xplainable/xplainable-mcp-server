"""
Enhanced tool registry for better tool discovery and introspection.

This module provides utilities to:
1. Extract tool information from FastMCP
2. Generate tool documentation
3. Provide runtime tool discovery
"""

import inspect
import sys
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum


class ToolCategory(Enum):
    """Categories for MCP tools."""
    DISCOVERY = "discovery"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class ToolParameter:
    """Represents a tool parameter."""
    name: str
    type: str
    required: bool
    default: Optional[Any] = None
    description: Optional[str] = None


@dataclass
class ToolInfo:
    """Complete information about an MCP tool."""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter]
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = asdict(self)
        result["category"] = self.category.value
        return result


class ToolRegistry:
    """Registry for MCP tools with introspection capabilities."""
    
    def __init__(self, mcp_instance=None):
        """
        Initialize the tool registry.
        
        Args:
            mcp_instance: FastMCP instance to extract tools from
        """
        self.mcp = mcp_instance
        self.tools: Dict[str, ToolInfo] = {}
        self._discover_tools()
    
    def _discover_tools(self):
        """Discover all available tools."""
        if self.mcp and hasattr(self.mcp, '_tools'):
            # Try to get tools from FastMCP instance
            self._discover_from_fastmcp()
        else:
            # Fallback to module introspection
            self._discover_from_module()
    
    def _discover_from_fastmcp(self):
        """Discover tools from FastMCP instance."""
        try:
            # This assumes FastMCP stores tools in _tools or similar
            # Actual implementation depends on FastMCP internals
            for tool_name, tool_func in self.mcp._tools.items():
                tool_info = self._extract_tool_info(tool_name, tool_func)
                if tool_info:
                    self.tools[tool_name] = tool_info
        except Exception as e:
            # Fallback to module introspection
            self._discover_from_module()
    
    def _discover_from_module(self):
        """Discover tools from the server module."""
        import xplainable_mcp.server as server_module
        
        for name, obj in inspect.getmembers(server_module):
            if self._is_tool_function(name, obj):
                tool_info = self._extract_tool_info(name, obj)
                if tool_info:
                    self.tools[name] = tool_info
    
    def _is_tool_function(self, name: str, obj: Any) -> bool:
        """Check if an object is a tool function."""
        if not callable(obj):
            return False
        if name.startswith('_'):
            return False
        if name in ['load_config', 'get_client', 'main', 'ServerConfig']:
            return False
        # Check for @mcp.tool() decorator (this is a heuristic)
        if hasattr(obj, '__doc__') and obj.__doc__:
            return True
        return False
    
    def _extract_tool_info(self, name: str, func: Callable) -> Optional[ToolInfo]:
        """Extract tool information from a function."""
        try:
            # Get docstring
            doc = inspect.getdoc(func) or "No description available"
            description = doc.strip().split('\n')[0].strip()
            
            # Get parameters
            sig = inspect.signature(func)
            parameters = []
            
            for param_name, param in sig.parameters.items():
                if param_name in ['self', 'cls']:
                    continue
                
                # Determine type
                param_type = "Any"
                if param.annotation != inspect.Parameter.empty:
                    param_type = self._format_type(param.annotation)
                
                # Extract parameter description from docstring
                param_desc = self._extract_param_description(doc, param_name)
                
                tool_param = ToolParameter(
                    name=param_name,
                    type=param_type,
                    required=param.default == inspect.Parameter.empty,
                    default=str(param.default) if param.default != inspect.Parameter.empty else None,
                    description=param_desc
                )
                parameters.append(tool_param)
            
            # Categorize the tool
            category = self._categorize_tool(name, description)
            
            # Check if enabled
            enabled = self._is_tool_enabled(name, category)
            
            return ToolInfo(
                name=name,
                description=description,
                category=category,
                parameters=parameters,
                enabled=enabled
            )
            
        except Exception as e:
            return None
    
    def _format_type(self, annotation: Any) -> str:
        """Format a type annotation as a string."""
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        
        # Handle Optional, List, Dict etc.
        type_str = str(annotation)
        type_str = type_str.replace('typing.', '')
        type_str = type_str.replace('<class ', '').replace('>', '')
        type_str = type_str.replace("'", '')
        
        return type_str
    
    def _extract_param_description(self, docstring: str, param_name: str) -> Optional[str]:
        """Extract parameter description from docstring."""
        lines = docstring.split('\n')
        in_args = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('Args:') or line.startswith('Parameters:'):
                in_args = True
                continue
            if line.startswith('Returns:') or line.startswith('Raises:'):
                in_args = False
                continue
            
            if in_args and param_name in line:
                # Try to extract description after parameter name
                parts = line.split(':', 1)
                if len(parts) > 1:
                    return parts[1].strip()
        
        return None
    
    def _categorize_tool(self, name: str, description: str) -> ToolCategory:
        """Categorize a tool based on its name and description."""
        name_lower = name.lower()
        desc_lower = description.lower()
        
        # Discovery tools
        if 'list_tools' in name_lower or 'discover' in name_lower:
            return ToolCategory.DISCOVERY
        
        # Write operations
        write_keywords = ['create', 'update', 'delete', 'deploy', 'activate', 
                         'deactivate', 'generate', 'train', 'start', 'stop',
                         'write', 'modify', 'edit']
        if any(keyword in name_lower or keyword in desc_lower for keyword in write_keywords):
            return ToolCategory.WRITE
        
        # Admin operations
        admin_keywords = ['admin', 'manage', 'config', 'setting']
        if any(keyword in name_lower for keyword in admin_keywords):
            return ToolCategory.ADMIN
        
        # Default to read
        return ToolCategory.READ
    
    def _is_tool_enabled(self, name: str, category: ToolCategory) -> bool:
        """Check if a tool is currently enabled."""
        # Write tools might be disabled by configuration
        if category == ToolCategory.WRITE:
            try:
                from xplainable_mcp.server import config
                return config.enable_write_tools
            except:
                return False
        
        return True
    
    def get_tools_by_category(self, category: ToolCategory) -> List[ToolInfo]:
        """Get all tools in a specific category."""
        return [tool for tool in self.tools.values() if tool.category == category]
    
    def get_enabled_tools(self) -> List[ToolInfo]:
        """Get all currently enabled tools."""
        return [tool for tool in self.tools.values() if tool.enabled]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary format."""
        return {
            "server_version": "0.1.0",
            "total_tools": len(self.tools),
            "enabled_tools": len(self.get_enabled_tools()),
            "categories": {
                "discovery": [t.to_dict() for t in self.get_tools_by_category(ToolCategory.DISCOVERY)],
                "read": [t.to_dict() for t in self.get_tools_by_category(ToolCategory.READ)],
                "write": [t.to_dict() for t in self.get_tools_by_category(ToolCategory.WRITE)],
                "admin": [t.to_dict() for t in self.get_tools_by_category(ToolCategory.ADMIN)]
            },
            "summary": {
                "discovery_tools": len(self.get_tools_by_category(ToolCategory.DISCOVERY)),
                "read_tools": len(self.get_tools_by_category(ToolCategory.READ)),
                "write_tools": len(self.get_tools_by_category(ToolCategory.WRITE)),
                "admin_tools": len(self.get_tools_by_category(ToolCategory.ADMIN)),
                "write_tools_enabled": self._check_write_tools_enabled()
            }
        }
    
    def _check_write_tools_enabled(self) -> bool:
        """Check if write tools are enabled."""
        try:
            from xplainable_mcp.server import config
            return config.enable_write_tools
        except:
            return False
    
    def generate_markdown_docs(self) -> str:
        """Generate markdown documentation for all tools."""
        lines = ["# MCP Tools Documentation\n"]
        
        for category in ToolCategory:
            tools = self.get_tools_by_category(category)
            if not tools:
                continue
            
            lines.append(f"\n## {category.value.title()} Tools\n")
            
            for tool in tools:
                lines.append(f"### `{tool.name}`\n")
                lines.append(f"{tool.description}\n")
                
                if tool.parameters:
                    lines.append("\n**Parameters:**\n")
                    for param in tool.parameters:
                        required = " (required)" if param.required else ""
                        default = f" = {param.default}" if param.default else ""
                        desc = f" - {param.description}" if param.description else ""
                        lines.append(f"- `{param.name}: {param.type}{default}`{required}{desc}")
                    lines.append("")
                
                if not tool.enabled:
                    lines.append("\n*Note: This tool is currently disabled.*\n")
        
        return "\n".join(lines)


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry(mcp_instance=None) -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry(mcp_instance)
    return _registry


def list_all_tools() -> Dict[str, Any]:
    """List all registered tools with their information."""
    registry = get_registry()
    return registry.to_dict()


def generate_docs() -> str:
    """Generate markdown documentation for all tools."""
    registry = get_registry()
    return registry.generate_markdown_docs()