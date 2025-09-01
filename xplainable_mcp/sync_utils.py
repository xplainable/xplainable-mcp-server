"""
Synchronization utilities to keep MCP tools aligned with xplainable-client methods.

This module provides utilities to:
1. Discover available methods in the xplainable-client
2. Generate tool definitions from client methods
3. Validate that MCP tools match client capabilities
4. Generate compatibility reports
"""

import inspect
import logging
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MethodCategory(Enum):
    """Categories for client methods."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    INTERNAL = "internal"


@dataclass
class ClientMethod:
    """Represents a discovered client method."""
    name: str
    module: str
    signature: inspect.Signature
    docstring: Optional[str]
    category: MethodCategory
    is_async: bool = False
    is_property: bool = False


@dataclass
class ToolDefinition:
    """Represents an MCP tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any]
    category: MethodCategory
    client_method: str


class ClientIntrospector:
    """Introspects the xplainable-client to discover available methods."""
    
    def __init__(self, client):
        """
        Initialize the introspector with a client instance.
        
        Args:
            client: An instance of XplainableClient
        """
        self.client = client
        self.discovered_methods: Dict[str, ClientMethod] = {}
        
    def discover_methods(self) -> Dict[str, ClientMethod]:
        """
        Discover all public methods from the client and its sub-clients.
        
        Returns:
            Dictionary mapping method names to ClientMethod objects
        """
        # Discover methods from main client
        self._discover_from_object(self.client, "client")
        
        # Discover from sub-clients
        sub_clients = [
            ("models", self.client.models),
            ("deployments", self.client.deployments),
            ("preprocessing", self.client.preprocessing),
            ("collections", self.client.collections),
            ("datasets", self.client.datasets),
            ("inference", self.client.inference),
            ("gpt", self.client.gpt),
            ("autotrain", self.client.autotrain),
            ("misc", self.client.misc),
        ]
        
        for name, sub_client in sub_clients:
            if sub_client:
                self._discover_from_object(sub_client, name)
                
        return self.discovered_methods
    
    def _discover_from_object(self, obj: Any, module_name: str):
        """
        Discover methods from a specific object.
        
        Args:
            obj: The object to introspect
            module_name: Name of the module/sub-client
        """
        for name, method in inspect.getmembers(obj):
            # Skip private/internal methods
            if name.startswith("_"):
                continue
                
            # Skip non-callable attributes
            if not callable(method):
                continue
                
            # Get method signature and docstring
            try:
                sig = inspect.signature(method)
                doc = inspect.getdoc(method)
                
                # Categorize the method
                category = self._categorize_method(name, doc)
                
                # Create method descriptor
                method_key = f"{module_name}.{name}"
                self.discovered_methods[method_key] = ClientMethod(
                    name=name,
                    module=module_name,
                    signature=sig,
                    docstring=doc,
                    category=category,
                    is_async=inspect.iscoroutinefunction(method),
                    is_property=isinstance(inspect.getattr_static(obj, name), property)
                )
                
            except Exception as e:
                logger.warning(f"Failed to introspect {module_name}.{name}: {e}")
    
    def _categorize_method(self, name: str, docstring: Optional[str]) -> MethodCategory:
        """
        Categorize a method based on its name and docstring.
        
        Args:
            name: Method name
            docstring: Method docstring
            
        Returns:
            Method category
        """
        # Check for write operations
        write_keywords = ["create", "update", "delete", "deploy", "activate", 
                         "deactivate", "generate", "train", "start", "stop"]
        if any(keyword in name.lower() for keyword in write_keywords):
            return MethodCategory.WRITE
            
        # Check for admin operations
        admin_keywords = ["admin", "manage", "config"]
        if any(keyword in name.lower() for keyword in admin_keywords):
            return MethodCategory.ADMIN
            
        # Check for internal methods
        if name.startswith("_") or "internal" in name.lower():
            return MethodCategory.INTERNAL
            
        # Default to read
        return MethodCategory.READ


class ToolGenerator:
    """Generates MCP tool definitions from client methods."""
    
    def __init__(self, introspector: ClientIntrospector):
        """
        Initialize the generator with an introspector.
        
        Args:
            introspector: A ClientIntrospector instance
        """
        self.introspector = introspector
        
    def generate_tool_definition(self, method: ClientMethod) -> Optional[ToolDefinition]:
        """
        Generate an MCP tool definition from a client method.
        
        Args:
            method: ClientMethod to convert
            
        Returns:
            ToolDefinition or None if method should be skipped
        """
        # Skip internal methods
        if method.category == MethodCategory.INTERNAL:
            return None
            
        # Skip properties
        if method.is_property:
            return None
            
        # Generate tool name
        tool_name = f"{method.module}_{method.name}".replace(".", "_")
        
        # Generate description
        description = method.docstring or f"Call {method.module}.{method.name}"
        if "\n" in description:
            description = description.split("\n")[0]  # Use first line only
            
        # Generate parameters from signature
        parameters = self._generate_parameters(method.signature)
        
        return ToolDefinition(
            name=tool_name,
            description=description,
            parameters=parameters,
            category=method.category,
            client_method=f"{method.module}.{method.name}"
        )
    
    def _generate_parameters(self, signature: inspect.Signature) -> Dict[str, Any]:
        """
        Generate parameter schema from method signature.
        
        Args:
            signature: Method signature
            
        Returns:
            Parameter schema dictionary
        """
        params = {}
        
        for name, param in signature.parameters.items():
            # Skip self/cls parameters
            if name in ["self", "cls"]:
                continue
                
            # Determine parameter type
            param_type = "string"  # Default
            if param.annotation != inspect.Parameter.empty:
                if param.annotation in [int, float]:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif hasattr(param.annotation, "__origin__"):
                    # Handle generic types like List, Dict, Optional
                    origin = param.annotation.__origin__
                    if origin == list:
                        param_type = "array"
                    elif origin == dict:
                        param_type = "object"
                        
            # Build parameter definition
            param_def = {
                "type": param_type,
                "description": f"Parameter {name}"
            }
            
            # Add default value if present
            if param.default != inspect.Parameter.empty:
                param_def["default"] = param.default
                
            params[name] = param_def
            
        return params


class SyncValidator:
    """Validates synchronization between MCP tools and client methods."""
    
    def __init__(self, client):
        """
        Initialize validator with client instance.
        
        Args:
            client: XplainableClient instance
        """
        self.introspector = ClientIntrospector(client)
        self.generator = ToolGenerator(self.introspector)
        
    def validate_tools(self, existing_tools: List[str]) -> Dict[str, Any]:
        """
        Validate existing MCP tools against available client methods.
        
        Args:
            existing_tools: List of existing tool names
            
        Returns:
            Validation report dictionary
        """
        # Discover all client methods
        methods = self.introspector.discover_methods()
        
        # Generate tool definitions
        potential_tools = {}
        for method in methods.values():
            tool_def = self.generator.generate_tool_definition(method)
            if tool_def:
                potential_tools[tool_def.name] = tool_def
                
        # Compare with existing tools
        existing_set = set(existing_tools)
        potential_set = set(potential_tools.keys())
        
        return {
            "existing_tools": len(existing_tools),
            "potential_tools": len(potential_tools),
            "implemented": list(existing_set),
            "missing": list(potential_set - existing_set),
            "extra": list(existing_set - potential_set),
            "coverage_percentage": (len(existing_set & potential_set) / len(potential_set) * 100) 
                                  if potential_set else 0
        }
    
    def generate_compatibility_matrix(self) -> Dict[str, Any]:
        """
        Generate a compatibility matrix for documentation.
        
        Returns:
            Compatibility information dictionary
        """
        methods = self.introspector.discover_methods()
        
        # Group by category
        by_category = {
            MethodCategory.READ: [],
            MethodCategory.WRITE: [],
            MethodCategory.ADMIN: [],
        }
        
        for method in methods.values():
            if method.category != MethodCategory.INTERNAL:
                by_category[method.category].append(f"{method.module}.{method.name}")
                
        return {
            "total_methods": len(methods),
            "read_methods": len(by_category[MethodCategory.READ]),
            "write_methods": len(by_category[MethodCategory.WRITE]),
            "admin_methods": len(by_category[MethodCategory.ADMIN]),
            "methods_by_category": {
                cat.value: methods for cat, methods in by_category.items()
            }
        }


def generate_tool_code(tool_def: ToolDefinition) -> str:
    """
    Generate Python code for an MCP tool from a tool definition.
    
    Args:
        tool_def: ToolDefinition to generate code for
        
    Returns:
        Python code string
    """
    # Build parameter list
    params = []
    for param_name, param_def in tool_def.parameters.items():
        if "default" in param_def:
            params.append(f"{param_name}={repr(param_def['default'])}")
        else:
            params.append(param_name)
            
    param_str = ", ".join(params)
    
    # Generate function code
    code = f'''
@mcp.tool()
def {tool_def.name}({param_str}):
    """
    {tool_def.description}
    """
    try:
        client = get_client()
        result = client.{tool_def.client_method}({", ".join(tool_def.parameters.keys())})
        logger.info(f"Executed {tool_def.client_method}")
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        logger.error(f"Error in {tool_def.name}: {{e}}")
        raise
'''
    return code


def main():
    """Example usage of sync utilities."""
    try:
        # This would be run as a utility script
        from xplainable_client.client.client import XplainableClient
        
        # Initialize client
        client = XplainableClient(
            api_key="dummy",  # Would use real key in practice
            hostname="https://platform.xplainable.io"
        )
        
        # Create validator
        validator = SyncValidator(client)
        
        # Generate compatibility matrix
        matrix = validator.generate_compatibility_matrix()
        print("Compatibility Matrix:")
        print(f"  Total methods: {matrix['total_methods']}")
        print(f"  Read methods: {matrix['read_methods']}")
        print(f"  Write methods: {matrix['write_methods']}")
        print(f"  Admin methods: {matrix['admin_methods']}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()