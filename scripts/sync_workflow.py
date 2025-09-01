#!/usr/bin/env python
"""
Automated sync workflow script for keeping MCP server in sync with xplainable-client changes.

This script automates the discovery and analysis phases of the sync workflow.
"""

import os
import sys
import json
import inspect
import subprocess
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


def get_latest_version() -> str:
    """Get latest xplainable-client version from PyPI."""
    try:
        result = subprocess.run(
            ["pip", "index", "versions", "xplainable-client"],
            capture_output=True,
            text=True,
            check=True
        )
        lines = result.stdout.strip().split('\n')
        if lines:
            # Format: "xplainable-client (1.2.3)"
            latest_line = lines[0]
            if '(' in latest_line and ')' in latest_line:
                return latest_line.split('(')[1].split(')')[0]
    except subprocess.CalledProcessError:
        pass
    return "unknown"


def discover_current_tools() -> List[str]:
    """Discover currently implemented MCP tools."""
    try:
        import xplainable_mcp.server as server_module
        tools = []
        
        for name, obj in inspect.getmembers(server_module):
            if callable(obj) and hasattr(obj, '__doc__') and not name.startswith('_'):
                # Skip utility functions
                if name in ['load_config', 'get_client', 'main', 'ServerConfig']:
                    continue
                tools.append(name)
        
        return tools
    except Exception as e:
        print(f"Error discovering current tools: {e}")
        return []


def analyze_client_methods() -> Dict[str, Any]:
    """Analyze xplainable-client methods to identify potential tools."""
    try:
        # Import sync utilities
        from xplainable_mcp.sync_utils import SyncValidator
        from xplainable_client.client.client import XplainableClient
        
        # Create client with dummy key for analysis
        client = XplainableClient(api_key="dummy-for-analysis")
        validator = SyncValidator(client)
        
        # Get current tools
        current_tools = discover_current_tools()
        
        # Validate coverage
        validation_report = validator.validate_tools(current_tools)
        
        # Get compatibility matrix
        compatibility_matrix = validator.generate_compatibility_matrix()
        
        return {
            "validation_report": validation_report,
            "compatibility_matrix": compatibility_matrix,
            "current_tools": current_tools
        }
        
    except Exception as e:
        print(f"Error analyzing client methods: {e}")
        return {
            "error": str(e),
            "current_tools": discover_current_tools()
        }


def generate_sync_report(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a comprehensive sync report."""
    current_version = get_current_version()
    latest_version = get_latest_version()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "versions": {
            "current": current_version,
            "latest": latest_version,
            "update_available": current_version != latest_version
        },
        "analysis": analysis
    }
    
    # Determine if sync is needed
    needs_sync = False
    sync_reasons = []
    
    if report["versions"]["update_available"]:
        needs_sync = True
        sync_reasons.append(f"Client version update available: {current_version} -> {latest_version}")
    
    if "validation_report" in analysis:
        validation = analysis["validation_report"]
        if validation.get("missing"):
            needs_sync = True
            sync_reasons.append(f"{len(validation['missing'])} missing tools identified")
        
        if validation.get("coverage_percentage", 100) < 90:
            needs_sync = True
            sync_reasons.append(f"Low coverage: {validation.get('coverage_percentage', 0):.1f}%")
    
    report["sync_status"] = {
        "needs_sync": needs_sync,
        "reasons": sync_reasons
    }
    
    return report


def create_implementation_plan(report: Dict[str, Any]) -> List[Dict[str, str]]:
    """Create an implementation plan based on the sync report."""
    plan = []
    
    if not report.get("analysis", {}).get("validation_report"):
        return plan
    
    validation = report["analysis"]["validation_report"]
    
    # Add missing tools
    for missing_tool in validation.get("missing", []):
        plan.append({
            "action": "implement",
            "type": "new_tool",
            "item": missing_tool,
            "priority": "medium",
            "description": f"Implement missing tool: {missing_tool}"
        })
    
    # Remove extra tools
    for extra_tool in validation.get("extra", []):
        plan.append({
            "action": "review",
            "type": "extra_tool", 
            "item": extra_tool,
            "priority": "low",
            "description": f"Review extra tool (no client method): {extra_tool}"
        })
    
    # Version update task
    if report["versions"]["update_available"]:
        plan.insert(0, {
            "action": "update",
            "type": "dependency",
            "item": "xplainable-client",
            "priority": "high",
            "description": f"Update xplainable-client to {report['versions']['latest']}"
        })
    
    return plan


def save_report(report: Dict[str, Any], output_file: Optional[str] = None) -> str:
    """Save the sync report to a file."""
    if output_file is None:
        output_file = f"sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return str(output_path)


def generate_markdown_report(report: Dict[str, Any], plan: List[Dict[str, str]]) -> str:
    """Generate a markdown version of the sync report."""
    md_lines = [
        f"# Sync Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Version Status",
        f"- **Current**: {report['versions']['current']}",
        f"- **Latest**: {report['versions']['latest']}",
        f"- **Update Available**: {'Yes' if report['versions']['update_available'] else 'No'}",
        ""
    ]
    
    # Sync status
    status = report.get("sync_status", {})
    if status.get("needs_sync"):
        md_lines.extend([
            "## ⚠️ Sync Required",
            "",
            "**Reasons:**"
        ])
        for reason in status.get("reasons", []):
            md_lines.append(f"- {reason}")
        md_lines.append("")
    else:
        md_lines.extend([
            "## ✅ No Sync Required",
            "",
            "The MCP server is up to date with the client.",
            ""
        ])
    
    # Analysis results
    if "validation_report" in report.get("analysis", {}):
        validation = report["analysis"]["validation_report"]
        md_lines.extend([
            "## Analysis Results",
            "",
            f"- **Total Current Tools**: {validation.get('existing_tools', 0)}",
            f"- **Potential Tools**: {validation.get('potential_tools', 0)}",
            f"- **Coverage**: {validation.get('coverage_percentage', 0):.1f}%",
            f"- **Missing Tools**: {len(validation.get('missing', []))}",
            f"- **Extra Tools**: {len(validation.get('extra', []))}",
            ""
        ])
        
        if validation.get("missing"):
            md_lines.extend([
                "### Missing Tools",
                ""
            ])
            for tool in validation["missing"]:
                md_lines.append(f"- `{tool}`")
            md_lines.append("")
        
        if validation.get("extra"):
            md_lines.extend([
                "### Extra Tools (No Client Method)",
                ""
            ])
            for tool in validation["extra"]:
                md_lines.append(f"- `{tool}`")
            md_lines.append("")
    
    # Implementation plan
    if plan:
        md_lines.extend([
            "## Implementation Plan",
            ""
        ])
        
        # Group by priority
        by_priority = {"high": [], "medium": [], "low": []}
        for item in plan:
            priority = item.get("priority", "medium")
            by_priority.setdefault(priority, []).append(item)
        
        for priority in ["high", "medium", "low"]:
            items = by_priority.get(priority, [])
            if items:
                md_lines.extend([
                    f"### {priority.title()} Priority",
                    ""
                ])
                for item in items:
                    md_lines.append(f"- [ ] **{item['action'].title()}**: {item['description']}")
                md_lines.append("")
    
    # Next steps
    md_lines.extend([
        "## Next Steps",
        "",
        "1. Review the implementation plan above",
        "2. Update dependencies if needed",
        "3. Implement missing tools following the patterns in `server.py`",
        "4. Add tests for new functionality",
        "5. Update documentation and version numbers",
        "6. Test thoroughly before deployment",
        "",
        "See `SYNC_WORKFLOW.md` for detailed instructions."
    ])
    
    return "\n".join(md_lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze sync status between MCP server and xplainable-client"
    )
    parser.add_argument(
        "--output",
        help="Output file for JSON report (default: auto-generated filename)"
    )
    parser.add_argument(
        "--markdown",
        help="Also generate markdown report at this path"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output"
    )
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("🔍 Analyzing sync status...")
    
    # Run analysis
    analysis = analyze_client_methods()
    
    # Generate report
    report = generate_sync_report(analysis)
    
    # Create implementation plan
    plan = create_implementation_plan(report)
    
    # Save JSON report
    json_path = save_report(report, args.output)
    if not args.quiet:
        print(f"📄 JSON report saved to: {json_path}")
    
    # Save markdown report if requested
    if args.markdown:
        md_content = generate_markdown_report(report, plan)
        md_path = Path(args.markdown)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_content)
        if not args.quiet:
            print(f"📝 Markdown report saved to: {args.markdown}")
    
    # Print summary to console
    if not args.quiet:
        print("\n" + "="*60)
        print("SYNC ANALYSIS SUMMARY")
        print("="*60)
        
        versions = report["versions"]
        print(f"Current version: {versions['current']}")
        print(f"Latest version:  {versions['latest']}")
        
        status = report.get("sync_status", {})
        if status.get("needs_sync"):
            print("\n⚠️  SYNC REQUIRED")
            for reason in status.get("reasons", []):
                print(f"   • {reason}")
            
            if plan:
                print(f"\n📋 Implementation plan created with {len(plan)} tasks")
                high_priority = [p for p in plan if p.get("priority") == "high"]
                if high_priority:
                    print(f"   • {len(high_priority)} high priority tasks")
        else:
            print("\n✅ NO SYNC REQUIRED")
            print("   MCP server is up to date")
        
        print(f"\n📊 Analysis Details:")
        if "validation_report" in analysis:
            val = analysis["validation_report"]
            print(f"   • Coverage: {val.get('coverage_percentage', 0):.1f}%")
            print(f"   • Missing tools: {len(val.get('missing', []))}")
            print(f"   • Extra tools: {len(val.get('extra', []))}")
        
        print("\nRun with --markdown FILENAME.md to generate detailed report")
    
    # Exit with appropriate code
    sys.exit(1 if report.get("sync_status", {}).get("needs_sync") else 0)


if __name__ == "__main__":
    main()