# Xplainable MCP Server - Claude Desktop Setup

This guide shows you how to add the Xplainable MCP Server to Claude Desktop using a Python virtual environment for reliable dependency management.

## Setup Instructions

### 1. Get Your API Key
Get your Xplainable API key from: https://platform.xplainable.io

### 2. Create Python Virtual Environment

**Create and set up the virtual environment:**

```bash
# Navigate to your projects directory
cd /path/to/your/projects

# Clone the MCP server (if you haven't already)
git clone https://github.com/xplainable/xplainable-mcp-server.git
cd xplainable-mcp-server

# Create Python virtual environment
python3 -m venv xplainable-mcp-env

# Activate the environment
source xplainable-mcp-env/bin/activate

# Install the MCP server and dependencies
pip install -e .

# Verify installation
python -m xplainable_mcp.server --help
```

### 3. Configure Claude Desktop

**Find your Claude Desktop config file:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

**Add this configuration (replace `/path/to/your/projects` with your actual path):**

```json
{
  "mcpServers": {
    "xplainable": {
      "command": "/path/to/your/projects/xplainable-mcp-server/xplainable-mcp-env/bin/python",
      "args": ["-m", "xplainable_mcp.server"],
      "env": {
        "XPLAINABLE_API_KEY": "your-api-key-here",
        "XPLAINABLE_HOST": "https://platform.xplainable.io"
      }
    }
  }
}
```

**For this specific setup, the configuration would be:**

```json
{
  "mcpServers": {
    "xplainable": {
      "command": "/Users/jtuppack/projects/xplainable-mcp-server/xplainable-mcp-env/bin/python",
      "args": ["-m", "xplainable_mcp.server"],
      "env": {
        "XPLAINABLE_API_KEY": "your-api-key-here",
        "XPLAINABLE_HOST": "https://platform.xplainable.io"
      }
    }
  }
}
```

**If you already have other MCP servers configured,** just add the `"xplainable"` section inside your existing `"mcpServers"` object:

```json
{
  "mcpServers": {
    "existing-server": {
      "command": "some-command"
    },
    "xplainable": {
      "command": "/Users/jtuppack/projects/xplainable-mcp-server/xplainable-mcp-env/bin/python",
      "args": ["-m", "xplainable_mcp.server"],
      "env": {
        "XPLAINABLE_API_KEY": "your-api-key-here",
        "XPLAINABLE_HOST": "https://platform.xplainable.io"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

Close and reopen Claude Desktop. The Xplainable tools should now be available!

## What You Can Do

Once configured, you can ask Claude to:

- List your team's models: *"Show me all the models in my team"*
- Get model details: *"Get information about model ID xyz"*
- List deployments: *"What deployments do I have?"*
- Deploy a model: *"Deploy version abc123 of my model"*
- Generate deployment keys: *"Create a deployment key for deployment xyz"*
- Get model reports: *"Generate a report for my model"*

## Troubleshooting

**"MCP server not found" error:**
- Verify the Python path in your config is correct
- Make sure the virtual environment exists and has the MCP server installed
- Check that your API key is correct
- Restart Claude Desktop after making config changes

**"Module not found" error:**
- Activate your virtual environment: `source xplainable-mcp-env/bin/activate`
- Reinstall the server: `pip install -e . --force-reinstall`
- Verify installation: `python -m xplainable_mcp.server --help`

**Connection errors:**
- Verify your API key at https://platform.xplainable.io
- Make sure `XPLAINABLE_HOST` is set correctly
- Check your internet connection

**Permission errors:**
- Some operations require special permissions in your Xplainable account
- Contact your team admin if you can't perform certain actions

**Virtual environment issues:**
- Make sure you're using Python 3.9 or later
- Recreate the environment if needed: `rm -rf xplainable-mcp-env && python3 -m venv xplainable-mcp-env`
- Check that all dependencies installed correctly

## Advanced Configuration

**Enable write operations (deployment, keys, etc.):**
```json
"env": {
  "XPLAINABLE_API_KEY": "your-api-key-here",
  "XPLAINABLE_HOST": "https://platform.xplainable.io",
  "ENABLE_WRITE_TOOLS": "true"
}
```

**Connect to a different Xplainable instance:**
```json
"env": {
  "XPLAINABLE_API_KEY": "your-api-key-here",
  "XPLAINABLE_HOST": "https://your-custom-instance.com"
}
```

**Update the MCP server:**
```bash
cd /path/to/your/projects/xplainable-mcp-server
source xplainable-mcp-env/bin/activate
git pull origin main
pip install -e . --force-reinstall
```

**Check available tools:**
```bash
source xplainable-mcp-env/bin/activate
python -c "
from xplainable_mcp.server import list_tools
tools = list_tools()
print(f'Total tools: {tools[\"total_tools\"]}')
for category, tool_list in tools['categories'].items():
    print(f'{category}: {len(tool_list)} tools')
"
```

---

**Need help?** Open an issue at: https://github.com/xplainable/xplainable-mcp-server/issues