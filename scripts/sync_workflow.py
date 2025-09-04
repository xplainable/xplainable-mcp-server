#!/usr/bin/env python
"""
Enhanced sync workflow that detects MCP-decorated methods in xplainable-client.
"""

import os
import sys
import json
import inspect
import subprocess
import importlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse


def get_current_version() -> str:
    """Get current xplainable-client version."""
    try:
        result = subprocess.run(
            ["pip", "show", "xplainable-client"],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                return line.split(':', 1)[1].strip()
    except subprocess.CalledProcessError:
        pass
    return "unknown"


def discover_mcp_decorated_methods(verbose: bool = False) -> Dict[str, Any]:
    """Discover methods decorated with @mcp_tool in xplainable-client."""
    decorated_methods = []
    
    try:
        # Dynamically discover all client modules
        import xplainable_client.client as client_package
        import pkgutil
        
        modules_to_scan = []
        
        # Iterate through all modules in xplainable_client.client
        for importer, modname, ispkg in pkgutil.iter_modules(client_package.__path__):
            # Skip private modules, base modules, and the main client module
            if modname.startswith('_') or modname in ['base', 'client', 'session', 'utils', 'exceptions', 'py_models']:
                continue
                
            try:
                # Import the module
                module = importlib.import_module(f'xplainable_client.client.{modname}')
                
                # Check if it has a service-specific Client class
                client_classes = [
                    name for name, obj in inspect.getmembers(module, inspect.isclass)
                    if name.endswith('Client') and name != 'BaseClient'
                ]
                
                if client_classes:
                    modules_to_scan.append((modname, module))
                    if verbose:
                        print(f"   Found service module: {modname}")
            except Exception as e:
                # Skip modules that can't be imported or don't have clients
                pass
        
        for module_name, module in modules_to_scan:
            # Find client classes
            for class_name, class_obj in inspect.getmembers(module, inspect.isclass):
                if class_name.endswith('Client'):
                    # Scan methods in the client class
                    for method_name, method in inspect.getmembers(class_obj):
                        # Check if method has the MCP marker
                        if hasattr(method, '_is_mcp_tool'):
                            method_info = {
                                'module': module_name,
                                'class': class_name,
                                'method': method_name,
                                'mcp_name': f"{module_name}_{method_name}",
                                'category': method._mcp_category.value if hasattr(method, '_mcp_category') else 'read',
                                'signature': str(inspect.signature(method)) if callable(method) else '',
                                'docstring': inspect.getdoc(method) or ''
                            }
                            decorated_methods.append(method_info)
        
        # Sort by module and method name
        decorated_methods.sort(key=lambda x: (x['module'], x['method']))
        
    except Exception as e:
        print(f"Error scanning for MCP decorated methods: {e}")
        import traceback
        traceback.print_exc()
    
    return {
        'decorated_methods': decorated_methods,
        'total_count': len(decorated_methods)
    }


def discover_current_mcp_tools() -> List[str]:
    """Discover currently implemented MCP tools in the server."""
    try:
        import xplainable_mcp.server as server_module
        tools = []
        
        for name, obj in inspect.getmembers(server_module):
            if callable(obj) and hasattr(obj, '__doc__') and not name.startswith('_'):
                # Skip utility functions
                if name in ['load_config', 'get_client', 'main', 'ServerConfig', 'safe_model_dump', 
                           'safe_list_response', 'safe_client_call', 'handle_none_as_empty_list']:
                    continue
                tools.append(name)
        
        return tools
    except Exception as e:
        print(f"Error discovering current tools: {e}")
        return []


def generate_tool_implementation(method_info: Dict[str, Any]) -> str:
    """Generate MCP tool implementation code for a decorated method."""
    
    # Use the MCP registry to get proper parameter information
    try:
        from xplainable_client.client.mcp_markers import get_mcp_registry
        registry = get_mcp_registry()
        
        # Find the method in the registry to get proper parameter info
        method_key = None
        for key, metadata in registry.items():
            if metadata['name'] == method_info['method'] and method_info['module'] in key:
                method_key = key
                break
        
        if method_key and method_key in registry:
            # Use registry parameter info
            registry_metadata = registry[method_key]
            params = registry_metadata['parameters']
            
            # Build parameter strings
            param_strings = []
            arg_strings = []
            
            for param_name, param_info in params.items():
                # Build parameter with type hint and default
                param_str = param_name
                
                # Add type hint if available
                if param_info.get('type'):
                    type_hint = _format_type_hint_for_tool(param_info['type'])
                    param_str = f"{param_name}: {type_hint}"
                
                # Add default value if present
                if not param_info['required']:
                    default_repr = repr(param_info['default'])
                    param_str = f"{param_str} = {default_repr}"
                
                param_strings.append(param_str)
                arg_strings.append(param_name)
            
            param_str = ', '.join(param_strings)
            arg_str = ', '.join(arg_strings)
        else:
            raise Exception("Method not found in registry")
    
    except Exception as e:
        # Fallback to signature parsing if registry lookup fails
        print(f"Warning: Using fallback parameter parsing for {method_info.get('method', 'unknown')}: {e}")
        
        # Parse the signature to extract parameters (fallback)
        sig_str = method_info.get('signature', '()')
        params_list = []
        
        # Remove 'self' and parse remaining parameters
        if '(' in sig_str and ')' in sig_str:
            params_part = sig_str[sig_str.index('(')+1:sig_str.index(')')]
            if params_part:
                # Smart split that respects brackets and parentheses
                params = []
                current_param = ""
                bracket_depth = 0
                paren_depth = 0
                
                for char in params_part:
                    if char in '[':
                        bracket_depth += 1
                    elif char in ']':
                        bracket_depth -= 1
                    elif char in '(':
                        paren_depth += 1
                    elif char in ')':
                        paren_depth -= 1
                    elif char == ',' and bracket_depth == 0 and paren_depth == 0:
                        # Found a parameter separator at top level
                        if current_param.strip():
                            params.append(current_param.strip())
                        current_param = ""
                        continue
                    
                    current_param += char
                
                # Don't forget the last parameter
                if current_param.strip():
                    params.append(current_param.strip())
                
                # Filter out 'self'
                params = [p for p in params if not p.startswith('self')]
                params_list = params
        
        # Build parameter string for function signature
        param_str = ', '.join(params_list) if params_list else ''
        
        # Build argument string for method call (just parameter names)
        arg_names = []
        for param in params_list:
            # Extract parameter name (before ':' or '=', but handle complex type hints)
            param = param.strip()
            if ':' in param:
                # For type hints like "goal: Dict[str, Any]", find the first ':' not inside brackets
                bracket_depth = 0
                colon_pos = -1
                for i, char in enumerate(param):
                    if char in '[(':
                        bracket_depth += 1
                    elif char in '])':
                        bracket_depth -= 1
                    elif char == ':' and bracket_depth == 0:
                        colon_pos = i
                        break
                
                if colon_pos != -1:
                    param_name = param[:colon_pos].strip()
                else:
                    param_name = param.split('=')[0].strip()
            else:
                param_name = param.split('=')[0].strip()
            arg_names.append(param_name)
        arg_str = ', '.join(arg_names) if arg_names else ''
    
    # Use full docstring, properly indented
    docstring = method_info.get('docstring', f"Execute {method_info['method']}")
    if docstring:
        # Clean and indent docstring
        docstring_lines = docstring.strip().split('\n')
        formatted_docstring = '\n    '.join(docstring_lines)
    else:
        formatted_docstring = f"Execute {method_info['method']}"
    
    template = f'''
@mcp.tool()
def {method_info['mcp_name']}({param_str}):
    """
    {formatted_docstring}
    
    Category: {method_info['category']}
    """
    try:
        client = get_client()
        result = client.{method_info['module']}.{method_info['method']}({arg_str})
        logger.info(f"Executed {method_info['module']}.{method_info['method']}")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in {method_info['mcp_name']}: {{e}}")
        raise
'''
    
    return template


def _format_type_hint_for_tool(type_hint) -> str:
    """Format a type hint for MCP tool code generation."""
    if hasattr(type_hint, '__name__'):
        return type_hint.__name__
    else:
        # Handle complex type hints
        type_str = str(type_hint)
        # Clean up typing module references
        type_str = type_str.replace('typing.', '')
        return type_str


def generate_sync_report(decorated_methods: Dict[str, Any], current_tools: List[str]) -> Dict[str, Any]:
    """Generate a comprehensive sync report."""
    current_version = get_current_version()
    
    # Extract MCP names from decorated methods
    mcp_tool_names = [m['mcp_name'] for m in decorated_methods['decorated_methods']]
    
    # Calculate coverage
    mcp_set = set(mcp_tool_names)
    current_set = set(current_tools)
    
    missing_tools = list(mcp_set - current_set)
    extra_tools = list(current_set - mcp_set)
    implemented_tools = list(mcp_set & current_set)
    
    coverage = (len(implemented_tools) / len(mcp_set) * 100) if mcp_set else 100
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": current_version,
        "analysis": {
            "decorated_methods": decorated_methods['total_count'],
            "current_tools": len(current_tools),
            "implemented": len(implemented_tools),
            "missing": len(missing_tools),
            "extra": len(extra_tools),
            "coverage_percentage": coverage
        },
        "missing_tools": missing_tools,
        "extra_tools": extra_tools,
        "implemented_tools": implemented_tools,
        "sync_required": len(missing_tools) > 0,
        "decorated_method_details": decorated_methods['decorated_methods']
    }
    
    return report


def sync_to_service_files(report: Dict[str, Any], force_update: bool = False) -> Dict[str, Any]:
    """
    Sync tools directly to service-specific files.
    
    Args:
        report: Sync report with missing tools
        force_update: If True, update existing tools even if unchanged
        
    Returns:
        Dictionary with sync results
    """
    from xplainable_mcp.tool_manager import ToolFileManager
    from pathlib import Path
    
    # Initialize tool manager
    tools_dir = Path("xplainable_mcp/tools")
    tool_manager = ToolFileManager(tools_dir)
    
    # If force_update is True, sync ALL decorated methods, not just missing ones
    if force_update:
        tools_to_sync = report['decorated_method_details']
    else:
        # Get missing tools that need implementation
        missing_tools = report['missing_tools']
        method_details = {m['mcp_name']: m for m in report['decorated_method_details']}
        
        # Convert to list for the tool manager
        tools_to_sync = []
        for tool_name in missing_tools:
            if tool_name in method_details:
                tools_to_sync.append(method_details[tool_name])
    
    # Sync all tools to service files
    results = tool_manager.sync_all_tools(tools_to_sync, generate_tool_implementation, force_update)
    
    # Get summary
    sync_summary = tool_manager.get_sync_summary()
    
    # Calculate totals from the new format
    totals = {'added': 0, 'updated': 0, 'skipped': 0}
    for service_results in results.values():
        for action, count in service_results.items():
            totals[action] += count
    
    return {
        'results': results,
        'summary': sync_summary,
        'totals': totals
    }


def generate_implementation_file(report: Dict[str, Any], output_path: str):
    """Generate a Python file with missing tool implementations (legacy mode)."""
    
    missing_tools = report['missing_tools']
    method_details = {m['mcp_name']: m for m in report['decorated_method_details']}
    
    lines = [
        "# Auto-generated MCP tool implementations",
        f"# Generated: {datetime.now().isoformat()}",
        f"# Missing tools: {len(missing_tools)}",
        "",
        "# NOTE: This is legacy format. Tools are now organized in xplainable_mcp/tools/ directory",
        "# This file is for reference only - actual tools are added to service-specific files",
        "",
        "from fastmcp import FastMCP",
        "import logging",
        "",
        "logger = logging.getLogger(__name__)",
        "",
        "# === MISSING TOOL IMPLEMENTATIONS ===",
        ""
    ]
    
    # Group by category
    by_category = {}
    for tool_name in missing_tools:
        if tool_name in method_details:
            category = method_details[tool_name].get('category', 'read')
            by_category.setdefault(category, []).append(tool_name)
    
    # Generate implementations grouped by category
    for category in sorted(by_category.keys()):
        lines.append(f"# Category: {category}")
        for tool_name in sorted(by_category[category]):
            method_info = method_details[tool_name]
            implementation = generate_tool_implementation(method_info)
            lines.append(implementation)
        lines.append("")
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    return output_path


def generate_markdown_report(report: Dict[str, Any]) -> str:
    """Generate a markdown report."""
    md_lines = [
        f"# MCP Sync Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"## Client Version: {report['version']}",
        "",
        "## Summary",
        f"- **Decorated Methods**: {report['analysis']['decorated_methods']}",
        f"- **Current Tools**: {report['analysis']['current_tools']}",
        f"- **Implemented**: {report['analysis']['implemented']}",
        f"- **Missing**: {report['analysis']['missing']}",
        f"- **Coverage**: {report['analysis']['coverage_percentage']:.1f}%",
        ""
    ]
    
    if report['sync_required']:
        md_lines.extend([
            "## ⚠️ Sync Required",
            "",
            f"There are {len(report['missing_tools'])} missing tool implementations.",
            ""
        ])
    else:
        md_lines.extend([
            "## ✅ Fully Synced",
            "",
            "All MCP-decorated methods are implemented.",
            ""
        ])
    
    # Missing tools section
    if report['missing_tools']:
        md_lines.extend([
            "## Missing Tools",
            "",
            "The following MCP-decorated methods need implementation:",
            ""
        ])
        
        # Group by category
        by_category = {}
        method_details = {m['mcp_name']: m for m in report['decorated_method_details']}
        
        for tool_name in report['missing_tools']:
            if tool_name in method_details:
                category = method_details[tool_name].get('category', 'read')
                by_category.setdefault(category, []).append(tool_name)
        
        for category in sorted(by_category.keys()):
            md_lines.append(f"### Category: {category}")
            md_lines.append("")
            for tool_name in sorted(by_category[category]):
                method = method_details[tool_name]
                md_lines.append(f"- `{tool_name}` - {method['docstring'].split('\\n')[0] if method['docstring'] else 'No description'}")
            md_lines.append("")
    
    # Implemented tools section
    if report['implemented_tools']:
        md_lines.extend([
            "## Implemented Tools",
            "",
            "The following tools are already implemented:",
            ""
        ])
        for tool in sorted(report['implemented_tools']):
            md_lines.append(f"- `{tool}`")
        md_lines.append("")
    
    # Extra tools section
    if report['extra_tools']:
        md_lines.extend([
            "## Extra Tools",
            "",
            "The following tools exist but have no corresponding MCP decorator:",
            ""
        ])
        for tool in sorted(report['extra_tools']):
            md_lines.append(f"- `{tool}`")
        md_lines.append("")
    
    return '\n'.join(md_lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync MCP server with MCP-decorated methods in xplainable-client"
    )
    parser.add_argument(
        "--output",
        help="Output file for JSON report (default: auto-generated filename)"
    )
    parser.add_argument(
        "--markdown",
        help="Generate markdown report at this path"
    )
    parser.add_argument(
        "--generate-code",
        help="Generate implementation code file at this path (legacy mode)"
    )
    parser.add_argument(
        "--sync-files",
        action="store_true",
        help="Sync tools directly to service-specific files (recommended)"
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update existing tools even if unchanged"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output"
    )
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("🔍 Scanning for MCP-decorated methods...")
    
    # Discover decorated methods (verbose mode if not quiet)
    decorated_methods = discover_mcp_decorated_methods(verbose=not args.quiet)
    
    if not args.quiet:
        print(f"   Found {decorated_methods['total_count']} decorated methods")
    
    # Discover current tools
    current_tools = discover_current_mcp_tools()
    
    if not args.quiet:
        print(f"   Found {len(current_tools)} current MCP tools")
    
    # Generate report
    report = generate_sync_report(decorated_methods, current_tools)
    
    # Save JSON report
    output_file = args.output or f"mcp_sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    if not args.quiet:
        print(f"📄 JSON report saved to: {output_file}")
    
    # Generate markdown report if requested
    if args.markdown:
        md_content = generate_markdown_report(report)
        with open(args.markdown, 'w') as f:
            f.write(md_content)
        if not args.quiet:
            print(f"📝 Markdown report saved to: {args.markdown}")
    
    # Sync to service files if requested
    if args.sync_files and (report['missing_tools'] or args.force_update):
        if not args.quiet:
            action = "Updating" if args.force_update else "Syncing"
            print(f"📁 {action} tools to service files...")
        
        sync_results = sync_to_service_files(report, args.force_update)
        
        if not args.quiet:
            totals = sync_results['totals']
            total_changes = totals['added'] + totals['updated']
            
            if total_changes > 0:
                print(f"   {total_changes} tools processed:")
                if totals['added'] > 0:
                    print(f"   • Added: {totals['added']}")
                if totals['updated'] > 0:
                    print(f"   • Updated: {totals['updated']}")
                if totals['skipped'] > 0:
                    print(f"   • Skipped: {totals['skipped']}")
                
                # Show breakdown by service
                for service, results in sync_results['results'].items():
                    service_total = results['added'] + results['updated']
                    if service_total > 0:
                        breakdown = []
                        if results['added']: breakdown.append(f"{results['added']} added")
                        if results['updated']: breakdown.append(f"{results['updated']} updated")
                        print(f"   • {service}: {', '.join(breakdown)}")
            else:
                print("   No changes needed - all tools up to date")
    
    # Generate implementation code if requested (legacy mode)
    if args.generate_code and report['missing_tools']:
        code_file = generate_implementation_file(report, args.generate_code)
        if not args.quiet:
            print(f"💻 Implementation code saved to: {code_file}")
    
    # Print summary
    if not args.quiet:
        print("\n" + "="*60)
        print("SYNC ANALYSIS SUMMARY")
        print("="*60)
        print(f"Version: {report['version']}")
        print(f"Coverage: {report['analysis']['coverage_percentage']:.1f}%")
        print(f"Missing: {report['analysis']['missing']}")
        print(f"Implemented: {report['analysis']['implemented']}")
        
        if report['sync_required']:
            print("\n⚠️  SYNC REQUIRED")
            print(f"   {len(report['missing_tools'])} tools need implementation")
            if args.sync_files:
                print("   🎉 Tools have been automatically synced to service files!")
        else:
            print("\n✅ FULLY SYNCED")
    
    sys.exit(1 if report['sync_required'] else 0)


if __name__ == "__main__":
    main()