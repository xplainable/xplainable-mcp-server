"""
Tool discovery for the new modular MCP tools system.

This module provides utilities to discover and introspect tools from 
the xplainable_mcp/tools/ directory structure.
"""

import inspect
import ast
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Information about a discovered MCP tool."""
    name: str
    description: str
    category: str
    module: str
    parameters: List[Dict[str, Any]]
    enabled: bool = True


class ModularToolDiscovery:
    """Discovers tools from the modular tools directory structure."""
    
    def __init__(self, tools_dir: Optional[Path] = None):
        """
        Initialize tool discovery.
        
        Args:
            tools_dir: Path to tools directory (defaults to xplainable_mcp/tools)
        """
        if tools_dir is None:
            current_dir = Path(__file__).parent
            tools_dir = current_dir / "tools"
        
        self.tools_dir = Path(tools_dir)
        self.discovered_tools: Dict[str, ToolInfo] = {}
    
    def discover_all_tools(self) -> Dict[str, ToolInfo]:
        """
        Discover all tools from the tools directory.
        
        Returns:
            Dictionary mapping tool names to ToolInfo objects
        """
        self.discovered_tools.clear()
        
        if not self.tools_dir.exists():
            logger.warning(f"Tools directory {self.tools_dir} does not exist")
            return {}
        
        # Scan all Python files in tools directory
        for py_file in self.tools_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            service_name = py_file.stem
            self._discover_tools_in_file(py_file, service_name)
        
        return self.discovered_tools
    
    def _discover_tools_in_file(self, file_path: Path, service_name: str):
        """
        Discover tools in a specific service file.
        
        Args:
            file_path: Path to the service file
            service_name: Name of the service (e.g., 'models', 'inference')
        """
        try:
            # Parse the file to find @mcp.tool() decorated functions
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse AST to find decorated functions
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function has @mcp.tool() decorator
                    has_mcp_decorator = False
                    
                    for decorator in node.decorator_list:
                        if self._is_mcp_tool_decorator(decorator):
                            has_mcp_decorator = True
                            break
                    
                    if has_mcp_decorator:
                        tool_info = self._extract_tool_info(node, service_name, content)
                        if tool_info:
                            self.discovered_tools[tool_info.name] = tool_info
                            
        except Exception as e:
            logger.error(f"Error discovering tools in {file_path}: {e}")
    
    def _is_mcp_tool_decorator(self, decorator) -> bool:
        """Check if a decorator is @mcp.tool()."""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return (decorator.func.attr == "tool" and 
                       isinstance(decorator.func.value, ast.Name) and 
                       decorator.func.value.id == "mcp")
        return False
    
    def _extract_tool_info(self, func_node: ast.FunctionDef, service_name: str, file_content: str) -> Optional[ToolInfo]:
        """
        Extract tool information from a function AST node.
        
        Args:
            func_node: AST node for the function
            service_name: Name of the service module
            file_content: Full file content for extracting docstrings
            
        Returns:
            ToolInfo object or None if extraction fails
        """
        try:
            # Extract function name
            func_name = func_node.name
            
            # Extract docstring
            docstring = ""
            if (func_node.body and 
                isinstance(func_node.body[0], ast.Expr) and 
                isinstance(func_node.body[0].value, ast.Constant)):
                docstring = func_node.body[0].value.value
            
            # Parse docstring for description and category
            description = "No description available"
            category = "read"  # default
            
            if docstring:
                lines = docstring.strip().split('\n')
                if lines:
                    description = lines[0].strip()
                
                # Look for category in docstring
                for line in lines:
                    if line.strip().startswith("Category:"):
                        category = line.split(":", 1)[1].strip()
                        break
            
            # Extract parameters
            parameters = []
            for arg in func_node.args.args:
                param_info = {
                    "name": arg.arg,
                    "type": "string",  # Default type
                    "required": True   # Will be updated if there's a default
                }
                
                # Check for type annotations
                if arg.annotation:
                    param_info["type"] = self._ast_to_type_string(arg.annotation)
                
                parameters.append(param_info)
            
            # Handle default values
            if func_node.args.defaults:
                num_defaults = len(func_node.args.defaults)
                for i, default in enumerate(func_node.args.defaults):
                    param_index = len(parameters) - num_defaults + i
                    if param_index >= 0:
                        parameters[param_index]["required"] = False
                        parameters[param_index]["default"] = self._ast_to_value(default)
            
            return ToolInfo(
                name=func_name,
                description=description,
                category=category,
                module=service_name,
                parameters=parameters
            )
            
        except Exception as e:
            logger.error(f"Error extracting tool info for {func_node.name}: {e}")
            return None
    
    def _ast_to_type_string(self, annotation) -> str:
        """Convert AST type annotation to string."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        else:
            return "any"
    
    def _ast_to_value(self, node) -> Any:
        """Convert AST node to Python value."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
            return node.s
        elif isinstance(node, ast.Num):  # Python < 3.8 compatibility
            return node.n
        else:
            return None
    
    def get_tools_by_category(self) -> Dict[str, List[ToolInfo]]:
        """Group tools by category."""
        by_category = {}
        
        for tool in self.discovered_tools.values():
            category = tool.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(tool)
        
        return by_category
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of discovered tools."""
        tools_by_category = self.get_tools_by_category()
        
        return {
            "total_tools": len(self.discovered_tools),
            "enabled_tools": len([t for t in self.discovered_tools.values() if t.enabled]),
            "categories": {cat: len(tools) for cat, tools in tools_by_category.items()},
            "services": list(set(tool.module for tool in self.discovered_tools.values()))
        }
    
    def generate_markdown_docs(self) -> str:
        """Generate markdown documentation for all tools."""
        tools_by_category = self.get_tools_by_category()
        summary = self.get_summary()
        
        lines = [
            "# Xplainable MCP Server - Tool Documentation",
            "",
            f"**Total Tools:** {summary['total_tools']}",
            f"**Services:** {', '.join(summary['services'])}",
            "",
        ]
        
        for category, tools in sorted(tools_by_category.items()):
            lines.extend([
                f"## {category.title()} Tools ({len(tools)})",
                ""
            ])
            
            for tool in sorted(tools, key=lambda t: t.name):
                lines.extend([
                    f"### `{tool.name}`",
                    f"**Service:** {tool.module}",
                    f"**Description:** {tool.description}",
                    ""
                ])
                
                if tool.parameters:
                    lines.append("**Parameters:**")
                    for param in tool.parameters:
                        required = "required" if param["required"] else "optional"
                        param_type = param.get("type", "string")
                        lines.append(f"- `{param['name']}` ({param_type}, {required})")
                    lines.append("")
        
        return "\n".join(lines)


def get_modular_tools_registry() -> ModularToolDiscovery:
    """Get a configured tool discovery instance."""
    discovery = ModularToolDiscovery()
    discovery.discover_all_tools()
    return discovery