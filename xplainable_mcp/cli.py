#!/usr/bin/env python
"""
CLI utilities for the Xplainable MCP Server.

Provides commands for:
- Generating tool documentation
- Validating configuration
- Testing connectivity
"""

import argparse
import json
import sys
import os
from pathlib import Path


def cmd_list_tools(args):
    """List all available tools."""
    try:
        from xplainable_mcp.tool_discovery import get_modular_tools_registry
        
        discovery = get_modular_tools_registry()
        tools = discovery.discovered_tools
        
        if args.format == "json":
            # Create JSON-serializable data
            tools_data = {
                "summary": discovery.get_summary(),
                "tools": {name: {
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "module": tool.module,
                    "parameters": tool.parameters,
                    "enabled": tool.enabled
                } for name, tool in tools.items()}
            }
            print(json.dumps(tools_data, indent=2))
        elif args.format == "markdown":
            print(discovery.generate_markdown_docs())
        else:  # table format
            summary = discovery.get_summary()
            tools_by_category = discovery.get_tools_by_category()
            
            print(f"\nXplainable MCP Server - Available Tools")
            print(f"=" * 60)
            print(f"Total Tools: {summary['total_tools']}")
            print(f"Enabled Tools: {summary['enabled_tools']}")
            print(f"Services: {', '.join(summary['services'])}")
            print(f"\nTools by Category:")
            print(f"-" * 60)
            
            for category, category_tools in tools_by_category.items():
                print(f"\n{category.upper()} ({len(category_tools)} tools):")
                for tool in sorted(category_tools, key=lambda t: t.name):
                    enabled = "✓" if tool.enabled else "✗"
                    print(f"  [{enabled}] {tool.name} ({tool.module}): {tool.description}")
            
            print(f"\n" + "=" * 60)
            print(f"Category Summary:")
            for category, count in summary['categories'].items():
                print(f"  {category.title()}: {count}")
            
    except Exception as e:
        print(f"Error listing tools: {e}", file=sys.stderr)
        return 1
    
    return 0


def cmd_validate_config(args):
    """Validate configuration."""
    try:
        from dotenv import load_dotenv
        from xplainable_mcp.server import ServerConfig
        
        # Load environment
        if args.env_file:
            load_dotenv(args.env_file)
        else:
            load_dotenv()
        
        # Check required variables
        issues = []
        
        api_key = os.getenv("XPLAINABLE_API_KEY")
        if not api_key:
            issues.append("XPLAINABLE_API_KEY is not set")
        elif api_key == "your-api-key-here":
            issues.append("XPLAINABLE_API_KEY has not been configured (still using example value)")
        
        # Try to create config
        try:
            config = ServerConfig(
                api_key=api_key or "dummy",
                hostname=os.getenv("XPLAINABLE_HOST", "https://platform.xplainable.io"),
                org_id=os.getenv("XPLAINABLE_ORG_ID"),
                team_id=os.getenv("XPLAINABLE_TEAM_ID"),
                enable_write_tools=os.getenv("ENABLE_WRITE_TOOLS", "false").lower() == "true",
                rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
            )
            
            print("Configuration Summary:")
            print(f"  Hostname: {config.hostname}")
            print(f"  Organization ID: {config.org_id or 'Not set'}")
            print(f"  Team ID: {config.team_id or 'Not set'}")
            print(f"  Write Tools: {'Enabled' if config.enable_write_tools else 'Disabled'}")
            print(f"  Rate Limiting: {'Enabled' if config.rate_limit_enabled else 'Disabled'}")
            
        except Exception as e:
            issues.append(f"Failed to create configuration: {e}")
        
        if issues:
            print("\nConfiguration Issues Found:")
            for issue in issues:
                print(f"  ❌ {issue}")
            return 1
        else:
            print("\n✅ Configuration is valid")
            return 0
            
    except Exception as e:
        print(f"Error validating configuration: {e}", file=sys.stderr)
        return 1


def cmd_test_connection(args):
    """Test connection to Xplainable API."""
    try:
        from dotenv import load_dotenv
        
        # Load environment
        if args.env_file:
            load_dotenv(args.env_file)
        else:
            load_dotenv()
        
        api_key = os.getenv("XPLAINABLE_API_KEY")
        if not api_key:
            print("Error: XPLAINABLE_API_KEY not set", file=sys.stderr)
            return 1
        
        print("Testing connection to Xplainable API...")
        
        try:
            from xplainable_client.client.client import XplainableClient
            
            client = XplainableClient(
                api_key=api_key,
                hostname=os.getenv("XPLAINABLE_HOST", "https://platform.xplainable.io"),
                org_id=os.getenv("XPLAINABLE_ORG_ID"),
                team_id=os.getenv("XPLAINABLE_TEAM_ID")
            )
            
            # Test connection by getting version info
            info = client.misc.get_version_info()
            
            print("\n✅ Successfully connected to Xplainable API")
            print(f"\nConnection Details:")
            print(f"  Username: {client.session.username}")
            print(f"  Hostname: {client.session.hostname}")
            print(f"  API Version: {info.model_dump().get('api_version', 'Unknown')}")
            
            return 0
            
        except ImportError:
            print("Error: xplainable-client not installed", file=sys.stderr)
            print("Install with: pip install xplainable-client", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"❌ Connection failed: {e}", file=sys.stderr)
            return 1
            
    except Exception as e:
        print(f"Error testing connection: {e}", file=sys.stderr)
        return 1


def cmd_generate_docs(args):
    """Generate documentation."""
    try:
        from xplainable_mcp.tool_discovery import get_modular_tools_registry
        
        discovery = get_modular_tools_registry()
        docs = discovery.generate_markdown_docs()
        
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(docs)
            print(f"✅ Documentation written to {args.output}")
        else:
            print(docs)
        
        return 0
        
    except Exception as e:
        print(f"Error generating documentation: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Xplainable MCP Server CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list-tools                    # List all available tools
  %(prog)s list-tools --format json      # Output as JSON
  %(prog)s validate-config               # Validate configuration
  %(prog)s test-connection               # Test API connection
  %(prog)s generate-docs                 # Generate tool documentation
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # list-tools command
    list_parser = subparsers.add_parser('list-tools', help='List available MCP tools')
    list_parser.add_argument(
        '--format',
        choices=['table', 'json', 'markdown'],
        default='table',
        help='Output format (default: table)'
    )
    
    # validate-config command
    validate_parser = subparsers.add_parser('validate-config', help='Validate server configuration')
    validate_parser.add_argument(
        '--env-file',
        help='Path to .env file (default: .env in current directory)'
    )
    
    # test-connection command
    test_parser = subparsers.add_parser('test-connection', help='Test connection to Xplainable API')
    test_parser.add_argument(
        '--env-file',
        help='Path to .env file (default: .env in current directory)'
    )
    
    # generate-docs command
    docs_parser = subparsers.add_parser('generate-docs', help='Generate tool documentation')
    docs_parser.add_argument(
        '--output',
        help='Output file path (default: stdout)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to appropriate command
    commands = {
        'list-tools': cmd_list_tools,
        'validate-config': cmd_validate_config,
        'test-connection': cmd_test_connection,
        'generate-docs': cmd_generate_docs,
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())