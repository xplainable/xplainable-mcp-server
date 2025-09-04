"""
Tool file manager for dynamically organizing MCP tools by service.

This module handles creating and updating service-specific tool files.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ToolFileManager:
    """Manages organization of MCP tools across service-specific files."""
    
    def __init__(self, tools_dir: Path):
        """
        Initialize the tool file manager.
        
        Args:
            tools_dir: Path to the tools directory
        """
        self.tools_dir = Path(tools_dir)
        self.tools_dir.mkdir(exist_ok=True)
        
    def get_service_file_path(self, service_name: str) -> Path:
        """Get the file path for a service's tools."""
        return self.tools_dir / f"{service_name}.py"
    
    def create_service_file(self, service_name: str) -> Path:
        """
        Create a new service file with boilerplate.
        
        Args:
            service_name: Name of the service (e.g., 'models', 'deployments')
            
        Returns:
            Path to the created file
        """
        file_path = self.get_service_file_path(service_name)
        
        if not file_path.exists():
            boilerplate = f'''"""
{service_name.title()} service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# {service_name.title()} Tools
# ============================================

'''
            file_path.write_text(boilerplate)
            logger.info(f"Created new service file: {file_path}")
        
        return file_path
    
    def add_tool_to_service(self, service_name: str, tool_code: str, tool_name: str, force_update: bool = False) -> str:
        """
        Add or update a tool in the appropriate service file.
        
        Args:
            service_name: Service name (e.g., 'models')
            tool_code: Generated tool implementation code
            tool_name: Name of the tool function
            force_update: If True, update existing tools even if they exist
            
        Returns:
            'added', 'updated', or 'skipped'
        """
        file_path = self.get_service_file_path(service_name)
        
        # Create file if it doesn't exist
        if not file_path.exists():
            self.create_service_file(service_name)
        
        # Read existing content
        current_content = file_path.read_text()
        
        # Check if tool already exists
        if f"def {tool_name}(" in current_content:
            if not force_update:
                # Check if the content has changed
                if self._tool_content_unchanged(current_content, tool_code, tool_name):
                    logger.info(f"Tool {tool_name} already exists and unchanged in {service_name}.py")
                    return 'skipped'
            
            # Update existing tool
            updated_content = self._replace_tool_in_content(current_content, tool_code, tool_name)
            file_path.write_text(updated_content)
            logger.info(f"Updated tool {tool_name} in {service_name}.py")
            return 'updated'
        else:
            # Add new tool
            updated_content = current_content + tool_code + "\n"
            file_path.write_text(updated_content)
            logger.info(f"Added tool {tool_name} to {service_name}.py")
            return 'added'
    
    def update_tools_init(self) -> None:
        """Update the __init__.py to import all service modules."""
        init_path = self.tools_dir / "__init__.py"
        
        # Find all service files
        service_files = [
            f.stem for f in self.tools_dir.glob("*.py") 
            if f.name != "__init__.py"
        ]
        
        if not service_files:
            return
        
        init_content = '''"""
MCP Tools for xplainable-client.

This module auto-imports all service-specific tool modules.
"""

# Import all service tools
'''
        
        for service in sorted(service_files):
            init_content += f"from . import {service}\n"
        
        init_content += "\n# All tools are automatically registered via the @mcp.tool() decorators\n"
        
        init_path.write_text(init_content)
        logger.info(f"Updated __init__.py with {len(service_files)} service imports")
    
    def get_existing_tools(self, service_name: str) -> List[str]:
        """
        Get list of existing tool names in a service file.
        
        Args:
            service_name: Service name
            
        Returns:
            List of tool function names
        """
        file_path = self.get_service_file_path(service_name)
        
        if not file_path.exists():
            return []
        
        try:
            # Parse the file to find function definitions
            content = file_path.read_text()
            tree = ast.parse(content)
            
            tools = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if it has @mcp.tool() decorator
                    for decorator in node.decorator_list:
                        if (isinstance(decorator, ast.Call) and 
                            isinstance(decorator.func, ast.Attribute) and
                            decorator.func.attr == "tool"):
                            tools.append(node.name)
                            break
            
            return tools
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []
    
    def organize_tools_by_service(self, tools_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Organize tools by their service module.
        
        Args:
            tools_data: List of tool metadata dictionaries
            
        Returns:
            Dictionary mapping service names to lists of tools
        """
        organized = {}
        
        for tool in tools_data:
            service = tool.get('module', 'misc')  # Default to 'misc' if no module
            organized.setdefault(service, []).append(tool)
        
        return organized
    
    def sync_all_tools(self, tools_data: List[Dict[str, Any]], generate_code_fn, force_update: bool = False) -> Dict[str, Dict[str, int]]:
        """
        Sync all tools to their appropriate service files.
        
        Args:
            tools_data: List of tool metadata
            generate_code_fn: Function to generate code for a tool
            force_update: If True, update existing tools even if unchanged
            
        Returns:
            Dictionary with counts of added/updated/skipped tools per service
        """
        organized_tools = self.organize_tools_by_service(tools_data)
        results = {}
        
        for service, tools in organized_tools.items():
            results[service] = {'added': 0, 'updated': 0, 'skipped': 0}
            
            for tool in tools:
                tool_name = tool['mcp_name']
                
                # Generate the tool code
                try:
                    tool_code = generate_code_fn(tool)
                    
                    # Add or update tool in service file
                    result = self.add_tool_to_service(service, tool_code, tool_name, force_update)
                    results[service][result] += 1
                        
                except Exception as e:
                    logger.error(f"Error generating code for {tool_name}: {e}")
        
        # Update the __init__.py
        self.update_tools_init()
        
        return results
    
    def get_sync_summary(self) -> Dict[str, Any]:
        """Get a summary of the current tool organization."""
        summary = {
            'services': {},
            'total_tools': 0
        }
        
        for service_file in self.tools_dir.glob("*.py"):
            if service_file.name == "__init__.py":
                continue
                
            service_name = service_file.stem
            tools = self.get_existing_tools(service_name)
            
            summary['services'][service_name] = {
                'count': len(tools),
                'tools': tools
            }
            summary['total_tools'] += len(tools)
        
        return summary
    
    def _tool_content_unchanged(self, current_content: str, new_tool_code: str, tool_name: str) -> bool:
        """
        Check if a tool's content has changed by comparing implementations.
        
        Args:
            current_content: Current file content
            new_tool_code: New tool implementation code
            tool_name: Name of the tool function
            
        Returns:
            True if content is unchanged, False if it has changed
        """
        try:
            # Extract existing tool implementation
            existing_tool = self._extract_tool_from_content(current_content, tool_name)
            if not existing_tool:
                return False
            
            # Normalize whitespace for comparison
            existing_normalized = ' '.join(existing_tool.split())
            new_normalized = ' '.join(new_tool_code.split())
            
            return existing_normalized == new_normalized
        except Exception as e:
            logger.error(f"Error comparing tool content for {tool_name}: {e}")
            # If we can't compare, assume it's changed
            return False
    
    def _extract_tool_from_content(self, content: str, tool_name: str) -> str:
        """
        Extract a specific tool's implementation from file content.
        
        Args:
            content: File content
            tool_name: Name of the tool function
            
        Returns:
            The tool's implementation code or empty string if not found
        """
        lines = content.split('\n')
        tool_lines = []
        in_tool = False
        indent_level = None
        
        for line in lines:
            # Find the start of the function
            if f"def {tool_name}(" in line:
                in_tool = True
                indent_level = len(line) - len(line.lstrip())
                tool_lines.append(line)
                continue
            
            if in_tool:
                # Check if we've reached the end of the function
                if line.strip() and (len(line) - len(line.lstrip())) <= indent_level and not line.lstrip().startswith(('@', '"""', "'''")):
                    # We've found a line at the same or lesser indentation that isn't a decorator or docstring
                    # This marks the end of the function
                    break
                tool_lines.append(line)
        
        return '\n'.join(tool_lines)
    
    def _replace_tool_in_content(self, content: str, new_tool_code: str, tool_name: str) -> str:
        """
        Replace ALL existing instances of a tool in file content with new implementation.
        
        Args:
            content: Current file content
            new_tool_code: New tool implementation
            tool_name: Name of the tool function
            
        Returns:
            Updated file content with all duplicates removed and new tool added once
        """
        lines = content.split('\n')
        new_lines = []
        in_tool = False
        indent_level = None
        tool_replaced = False
        skip_empty_lines = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for @mcp.tool() decorator followed by our function
            if line.strip() == "@mcp.tool()":
                # Look ahead for our function
                found_function = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if j < len(lines) and f"def {tool_name}(" in lines[j]:
                        found_function = True
                        # Add new tool code only for the FIRST occurrence
                        if not tool_replaced:
                            new_lines.append(new_tool_code)
                            tool_replaced = True
                        
                        # Skip the entire function (decorator + function + body)
                        func_indent = len(lines[j]) - len(lines[j].lstrip())
                        k = i  # Start from decorator
                        # Skip through the entire function
                        while k < len(lines):
                            if k > j and lines[k].strip():  # After function def line
                                current_indent = len(lines[k]) - len(lines[k].lstrip()) if lines[k].strip() else float('inf')
                                if current_indent <= func_indent and not lines[k].lstrip().startswith(('@', '"""', "'''", '#')):
                                    # Found end of function
                                    break
                            k += 1
                        i = k - 1  # Will be incremented at end of loop
                        skip_empty_lines = True
                        break
                
                if not found_function:
                    new_lines.append(line)
            
            # Check for function definition without decorator
            elif f"def {tool_name}(" in line:
                if not tool_replaced:
                    new_lines.append(new_tool_code)
                    tool_replaced = True
                
                # Skip the entire function body
                func_indent = len(line) - len(line.lstrip())
                j = i + 1
                while j < len(lines):
                    if lines[j].strip():  # Non-empty line
                        current_indent = len(lines[j]) - len(lines[j].lstrip())
                        if current_indent <= func_indent and not lines[j].lstrip().startswith(('@', '"""', "'''", '#')):
                            # Found end of function
                            break
                    j += 1
                i = j - 1  # Will be incremented at end of loop
                skip_empty_lines = True
            
            else:
                # Skip excessive empty lines after function removal
                if skip_empty_lines and not line.strip():
                    # Count consecutive empty lines
                    empty_count = 0
                    temp_i = i
                    while temp_i < len(lines) and not lines[temp_i].strip():
                        empty_count += 1
                        temp_i += 1
                    
                    # Keep max 2 empty lines
                    if empty_count > 2:
                        i += empty_count - 2 - 1  # Will be incremented at end
                    else:
                        new_lines.append(line)
                    
                    if temp_i < len(lines) and lines[temp_i].strip():
                        skip_empty_lines = False
                else:
                    new_lines.append(line)
                    if line.strip():
                        skip_empty_lines = False
            
            i += 1
        
        # If tool was never found, append it
        if not tool_replaced:
            new_lines.append(new_tool_code)
        
        return '\n'.join(new_lines)