# Xplainable MCP Server Usage

## Sync Workflow

The sync workflow automatically generates MCP tools from `@mcp_tool` decorated methods in the xplainable-client.

### Basic Commands

```bash
# Basic sync - adds missing tools only
python scripts/sync_workflow.py --sync-files

# Force update all tools (useful after changing docstrings/parameters)
python scripts/sync_workflow.py --sync-files --force-update

# Generate markdown report
python scripts/sync_workflow.py --sync-files --markdown sync_report.md

# Quiet mode (less verbose output)
python scripts/sync_workflow.py --sync-files --quiet

# View all options
python scripts/sync_workflow.py --help
```

### Most Common Usage

- **Normal sync**: `python scripts/sync_workflow.py --sync-files`
  - Adds new tools from newly decorated client methods
  - Updates tools only if their implementation has changed
  - Skips unchanged tools

- **Force update**: `python scripts/sync_workflow.py --sync-files --force-update`
  - Updates all tools regardless of changes
  - Useful after modifying client method docstrings or parameters
  - Regenerates all MCP tools from current client state

### How It Works

1. **Scans** the xplainable-client for methods decorated with `@mcp_tool`
2. **Generates** corresponding MCP tools in service-specific files:
   - `xplainable_mcp/tools/models.py` - Model management tools
   - `xplainable_mcp/tools/inference.py` - Prediction tools
   - `xplainable_mcp/tools/deployments.py` - Deployment tools
   - `xplainable_mcp/tools/datasets.py` - Dataset tools
   - `xplainable_mcp/tools/collections.py` - Collection tools
3. **Reports** what was added/updated/skipped
4. **Updates** the `__init__.py` to import all service modules

### Output Example

```
🔍 Scanning for MCP-decorated methods...
   Found 8 decorated methods
   Found 12 current MCP tools
📁 Syncing tools to service files...
   5 tools processed:
   • Added: 2
   • Updated: 3
   • models: 1 added, 2 updated
   • inference: 1 added, 1 updated
```

### Adding New Tools

To add a new MCP tool:

1. Decorate the client method with `@mcp_tool(category=MCPCategory.READ/WRITE/INFERENCE)`
2. Run `python scripts/sync_workflow.py --sync-files`
3. The corresponding MCP tool will be automatically generated

### Updating Existing Tools

When you modify a client method's docstring or parameters:

1. Make your changes to the client method
2. Run `python scripts/sync_workflow.py --sync-files --force-update`
3. All MCP tools will be regenerated with the updated information