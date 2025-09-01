# Xplainable MCP Server

A Model Context Protocol (MCP) server that provides secure access to Xplainable AI platform capabilities through standardized tools and resources.

## Features

- **Secure Authentication**: Token-based authentication with environment variable management
- **Read Operations**: Access models, deployments, preprocessors, and collections
- **Write Operations**: Deploy models, manage deployments, generate reports (with proper authorization)
- **Type Safety**: Full Pydantic model validation for all inputs/outputs
- **Rate Limiting**: Built-in rate limiting and request validation
- **Audit Logging**: Comprehensive logging of all operations

## Installation

```bash
pip install xplainable-mcp-server
```

## CLI Commands

The server includes a CLI for management and documentation:

```bash
# List all available tools
xplainable-mcp-cli list-tools
xplainable-mcp-cli list-tools --format json
xplainable-mcp-cli list-tools --format markdown

# Validate configuration
xplainable-mcp-cli validate-config
xplainable-mcp-cli validate-config --env-file /path/to/.env

# Test API connection
xplainable-mcp-cli test-connection

# Generate tool documentation
xplainable-mcp-cli generate-docs
xplainable-mcp-cli generate-docs --output TOOLS.md
```

## Quick Start

### For Production Users

If you just want to use this MCP server with Claude Code:

1. **Get your Xplainable API key** from https://platform.xplainable.io
2. **Add the MCP configuration** (see Claude Code Configuration above)
3. **That's it!** Claude Code will handle installation automatically

### For Developers

### 1. Set up environment variables

Create a `.env` file with your Xplainable credentials:

```env
XPLAINABLE_API_KEY=your-api-key-here
XPLAINABLE_HOST=https://platform.xplainable.io
XPLAINABLE_ORG_ID=your-org-id  # Optional
XPLAINABLE_TEAM_ID=your-team-id  # Optional
```

### 2. Run the server

```bash
# For development (localhost only)
xplainable-mcp

# For production (with TLS/proxy)
xplainable-mcp --host 0.0.0.0 --port 8000
```

### 3. Connect with an MCP client

#### Claude Code Configuration

**Option 1: Install from GitHub (Recommended)**
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

**Option 2: Clone and run from source**
```json
{
  "mcpServers": {
    "xplainable": {
      "command": "python",
      "args": ["-m", "xplainable_mcp.server"],
      "cwd": "/path/to/cloned/xplainable-mcp-server",
      "env": {
        "XPLAINABLE_API_KEY": "your-api-key-here",
        "XPLAINABLE_HOST": "https://platform.xplainable.io"
      }
    }
  }
}
```

**Option 3: Development with local backend**
```json
{
  "mcpServers": {
    "xplainable": {
      "command": "python",
      "args": ["-m", "xplainable_mcp.server"],
      "cwd": "/path/to/xplainable-mcp-server",
      "env": {
        "XPLAINABLE_API_KEY": "your-development-key",
        "XPLAINABLE_HOST": "http://localhost:8000",
        "ENABLE_WRITE_TOOLS": "true"
      }
    }
  }
}
```

#### Claude Desktop Configuration

Add the configuration to your Claude Desktop MCP settings file:

**File Locations:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

**Option 1: Install from GitHub (Recommended)**
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

**Option 2: Development setup (from source)**
```json
{
  "mcpServers": {
    "xplainable": {
      "command": "python",
      "args": ["-m", "xplainable_mcp.server"],
      "cwd": "/path/to/xplainable-mcp-server",
      "env": {
        "XPLAINABLE_API_KEY": "your-api-key",
        "XPLAINABLE_HOST": "https://platform.xplainable.io",
        "ENABLE_WRITE_TOOLS": "true"
      }
    }
  }
}
```

**Option 3: Using conda environment**
```json
{
  "mcpServers": {
    "xplainable": {
      "command": "conda",
      "args": ["run", "-n", "xplainable-mcp", "python", "-m", "xplainable_mcp.server"],
      "cwd": "/path/to/xplainable-mcp-server",
      "env": {
        "XPLAINABLE_API_KEY": "your-api-key",
        "XPLAINABLE_HOST": "https://platform.xplainable.io",
        "ENABLE_WRITE_TOOLS": "true"
      }
    }
  }
}
```

## Development Setup

### For Local Development with Claude Code

1. **Set up the environment:**
```bash
# Create conda environment
conda create -n xplainable-mcp python=3.9
conda activate xplainable-mcp

# Install dependencies
pip install -e .
pip install -e /path/to/xplainable-client
```

2. **Configure environment variables:**
```env
# .env file for development
XPLAINABLE_API_KEY=your-development-api-key
XPLAINABLE_HOST=http://localhost:8000
ENABLE_WRITE_TOOLS=true
RATE_LIMIT_ENABLED=false
```

3. **Test the setup:**
```bash
# Test connection to local backend
python -c "
import sys
sys.path.append('.')
from xplainable_mcp.server import get_client
client = get_client()
print('Connection successful!')
print(f'Connected to: {client.connection_info}')
"
```

### Example Deployment Workflow

Here's a complete example of deploying a model and testing inference:

```bash
# 1. List available models
python -c "
from xplainable_mcp.server import get_client
client = get_client()
models = client.models.list_team_models()
for model in models[:3]:  # Show first 3
    print(f'Model: {model.display_name} (ID: {model.model_id})')
    print(f'  Version: {model.active_version}')
    print(f'  Deployed: {model.deployed}')
"

# 2. Deploy a model version (replace with actual version_id)
python -c "
from xplainable_mcp.server import get_client
client = get_client()
deployment = client.deployments.deploy('your-version-id-here')
print(f'Deployment ID: {deployment.deployment_id}')
"

# 3. Generate deployment key
python -c "
from xplainable_mcp.server import get_client
client = get_client()
key = client.deployments.generate_deploy_key('deployment-id', 'Test Key')
print(f'Deploy Key: {key}')
"

# 4. Test inference (requires active deployment)
curl -X POST https://inference.xplainable.io/v1/predict \
  -H 'Content-Type: application/json' \
  -d '{
    "deploy_key": "your-deploy-key",
    "data": {"feature1": "value1", "feature2": 123}
  }'
```

## Available Tools

### Discovery Tools

- `list_tools()` - List all available MCP tools with descriptions and parameters

### Read-Only Tools

- `get_connection_info()` - Get connection and diagnostic information
- `list_team_models(team_id?)` - List all models for a team
- `get_model(model_id)` - Get detailed model information
- `list_model_versions(model_id)` - List all versions of a model
- `list_deployments(team_id?)` - List all deployments
- `list_preprocessors(team_id?)` - List all preprocessors
- `get_preprocessor(preprocessor_id)` - Get preprocessor details
- `get_collection_scenarios(collection_id)` - List scenarios in a collection
- `get_active_team_deploy_keys_count(team_id?)` - Get count of active deploy keys
- `misc_get_version_info()` - Get version information

### Write Tools (Restricted)

*Note: Write tools require `ENABLE_WRITE_TOOLS=true` in environment*

- `activate_deployment(deployment_id)` - Activate a deployment  
- `deactivate_deployment(deployment_id)` - Deactivate a deployment
- `generate_deploy_key(deployment_id, description?, days_until_expiry?)` - Generate deployment key
- `get_deployment_payload(deployment_id)` - Get sample payload data for deployment
- `gpt_generate_report(model_id, version_id, ...)` - Generate GPT report

## Security

### Authentication

The server requires authentication via:
- Bearer tokens for MCP client connections
- API keys for Xplainable backend (from environment only)

### Transport Security

- Default binding to localhost only
- TLS termination at reverse proxy recommended
- Origin/Host header validation

### Rate Limiting

Per-tool and per-principal rate limits are enforced to prevent abuse.

## Synchronization with xplainable-client

When the xplainable-client library is updated, use these tools to keep the MCP server synchronized:

### Quick Sync Check
```bash
# Check if sync is needed
python scripts/sync_workflow.py

# Generate detailed report
python scripts/sync_workflow.py --markdown sync_report.md

# Check current tool coverage
xplainable-mcp-cli list-tools --format json
```

### Comprehensive Sync Process
1. **Read the sync workflow guide:** [`SYNC_WORKFLOW.md`](SYNC_WORKFLOW.md)
2. **Review common scenarios:** [`examples/sync_scenarios.md`](examples/sync_scenarios.md)
3. **Run automated analysis:** `python scripts/sync_workflow.py`
4. **Implement changes following the patterns in `server.py`**
5. **Test thoroughly and update documentation**

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/xplainable/xplainable-mcp-server
cd xplainable-mcp-server

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy xplainable_mcp

# Linting
ruff check .
black --check .
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=xplainable_mcp

# Run specific tests
pytest tests/test_tools.py
```

## Deployment

### Docker

```bash
# Build the image
docker build -t xplainable-mcp-server .

# Run with environment file
docker run --env-file .env -p 8000:8000 xplainable-mcp-server
```

## Compatibility Matrix

| MCP Server Version | Xplainable Client | Backend API |
|-------------------|-------------------|-------------|
| 0.1.x             | >=1.0.0           | v1          |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

For security issues, please see [SECURITY.md](SECURITY.md).

## License

MIT License - see [LICENSE](LICENSE) for details.