# Xplainable MCP Server - Claude Desktop Setup

This guide shows you how to add the Xplainable MCP Server to Claude Desktop.

## Quick Setup (2 steps)

### 1. Get Your API Key
Get your Xplainable API key from: https://platform.xplainable.io

### 2. Add MCP Configuration

**Find your Claude Desktop config file:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

**Add this configuration:**

```json
{
  "mcpServers": {
    "xplainable": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yourusername/xplainable-mcp-server.git", "xplainable-mcp-server"],
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
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yourusername/xplainable-mcp-server.git", "xplainable-mcp-server"],
      "env": {
        "XPLAINABLE_API_KEY": "your-api-key-here",
        "XPLAINABLE_HOST": "https://platform.xplainable.io"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

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
- Make sure you have `uvx` installed: `pip install uvx`
- Check that your API key is correct
- Restart Claude Desktop after making config changes

**Connection errors:**
- Verify your API key at https://platform.xplainable.io
- Make sure `XPLAINABLE_HOST` is set correctly
- Check your internet connection

**Permission errors:**
- Some operations require special permissions in your Xplainable account
- Contact your team admin if you can't perform certain actions

## Advanced Configuration

**Use a specific branch or commit:**
```json
"args": ["--from", "git+https://github.com/yourusername/xplainable-mcp-server.git@main", "xplainable-mcp-server"]
```

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

---

**Need help?** Open an issue at: https://github.com/yourusername/xplainable-mcp-server/issues