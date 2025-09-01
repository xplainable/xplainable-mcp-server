# Xplainable Client Synchronization Workflow

This guide provides comprehensive steps for keeping the Xplainable MCP Server synchronized with changes in the xplainable-client library.

## Overview

The MCP server acts as a bridge between MCP clients (like Claude Desktop) and the Xplainable API. When the xplainable-client library is updated with new features, bug fixes, or API changes, the MCP server needs to be updated accordingly to expose these capabilities through MCP tools.

## When to Sync

You should run this synchronization workflow when:

1. **xplainable-client is updated** (new version released)
2. **New API endpoints** are added to the Xplainable platform
3. **Existing endpoints change** (parameters, return types, behavior)
4. **Deprecation notices** are announced for existing functionality
5. **Quarterly maintenance** (recommended regular check)

## Pre-requisites

Before starting the sync process, ensure you have:

- [ ] Access to both repositories (xplainable-client and xplainable-mcp-server)
- [ ] Valid Xplainable API credentials for testing
- [ ] Development environment set up with Python 3.9+
- [ ] Git access and appropriate permissions

## Step-by-Step Synchronization Process

### Phase 1: Assessment and Discovery

#### 1.1 Update the xplainable-client Dependency

```bash
# Navigate to your MCP server project
cd /path/to/xplainable-mcp-server

# Update to the latest xplainable-client version
pip install --upgrade xplainable-client

# Or update to a specific version
pip install xplainable-client==1.2.0
```

#### 1.2 Run Discovery Analysis

Use the built-in CLI tools to analyze the current state:

```bash
# Check what tools are currently available
xplainable-mcp-cli list-tools --format json > current_tools.json

# Test current connectivity
xplainable-mcp-cli test-connection

# Validate current configuration
xplainable-mcp-cli validate-config
```

#### 1.3 Discover New Client Capabilities

```bash
# Run the sync utility to analyze the updated client
python -c "
from xplainable_mcp.sync_utils import SyncValidator
from xplainable_client.client.client import XplainableClient
import os

client = XplainableClient(api_key=os.environ['XPLAINABLE_API_KEY'])
validator = SyncValidator(client)

# Get current tool names from the server
import xplainable_mcp.server as server
import inspect
current_tools = []
for name, obj in inspect.getmembers(server):
    if callable(obj) and hasattr(obj, '__doc__') and not name.startswith('_'):
        if name not in ['load_config', 'get_client', 'main']:
            current_tools.append(name)

# Validate coverage
report = validator.validate_tools(current_tools)
print('=== SYNCHRONIZATION REPORT ===')
print(f'Current tools: {report[\"existing_tools\"]}')
print(f'Potential tools: {report[\"potential_tools\"]}')
print(f'Coverage: {report[\"coverage_percentage\"]:.1f}%')
print(f'Missing tools: {report[\"missing\"]}')
print(f'Extra tools: {report[\"extra\"]}')

# Get compatibility matrix
matrix = validator.generate_compatibility_matrix()
print(f'\n=== CLIENT CAPABILITIES ===')
print(f'Total methods: {matrix[\"total_methods\"]}')
print(f'Read methods: {matrix[\"read_methods\"]}')
print(f'Write methods: {matrix[\"write_methods\"]}')
print(f'Admin methods: {matrix[\"admin_methods\"]}')
"
```

### Phase 2: Planning and Implementation

#### 2.1 Analyze the Discovery Report

Review the output from step 1.3 and identify:

- **Missing tools**: Client methods that should be exposed as MCP tools
- **Extra tools**: MCP tools that no longer have corresponding client methods
- **Changed signatures**: Existing tools with parameter mismatches
- **New categories**: Methods that represent entirely new functionality

#### 2.2 Create Implementation Plan

Document your findings and create a plan:

```bash
# Create a sync report
cat > sync_report_$(date +%Y%m%d).md << 'EOF'
# Sync Report - $(date +%Y-%m-%d)

## Client Version
- Previous: x.y.z
- New: a.b.c

## Changes Detected
### New Methods to Implement
- [ ] client.module.new_method_1
- [ ] client.module.new_method_2

### Methods to Update
- [ ] existing_tool_1: Parameter changes
- [ ] existing_tool_2: Return type changes

### Methods to Deprecate
- [ ] old_tool_1: Method removed from client
- [ ] old_tool_2: Method deprecated

### Breaking Changes
- [ ] authentication_change: New auth flow
- [ ] endpoint_migration: URL changes

## Implementation Priority
1. Critical fixes (authentication, breaking changes)
2. New read-only tools
3. New write tools (if enabled)
4. Deprecation handling
5. Documentation updates

## Testing Requirements
- [ ] Unit tests for new tools
- [ ] Integration tests with real API
- [ ] Backward compatibility verification
- [ ] Performance impact assessment
EOF
```

#### 2.3 Update Tool Implementations

For each identified change:

**Adding New Tools:**
```python
# Example: Adding a new read-only tool
@mcp.tool()
def new_client_method(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """
    Description of what this tool does.
    
    Args:
        param1: Description of param1
        param2: Optional description of param2
        
    Returns:
        Dictionary containing the result
    """
    try:
        client = get_client()
        result = client.module.new_method(param1, param2)
        logger.info(f"Executed new_client_method with param1={param1}")
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        logger.error(f"Error in new_client_method: {e}")
        raise
```

**Updating Existing Tools:**
```python
# Example: Updating tool with new parameters
@mcp.tool()
def existing_tool(
    existing_param: str, 
    new_param: Optional[str] = None  # New parameter added
) -> Dict[str, Any]:
    """Updated tool description."""
    try:
        client = get_client()
        # Handle backward compatibility
        if new_param is not None:
            result = client.module.method(existing_param, new_param)
        else:
            result = client.module.method(existing_param)
        logger.info(f"Executed updated existing_tool")
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        logger.error(f"Error in existing_tool: {e}")
        raise
```

**Handling Deprecations:**
```python
@mcp.tool()
def deprecated_tool(param: str) -> Dict[str, Any]:
    """
    [DEPRECATED] This tool is deprecated and will be removed in v2.0.
    Use 'new_replacement_tool' instead.
    """
    logger.warning("deprecated_tool is deprecated, use new_replacement_tool instead")
    try:
        # Provide migration path or legacy support
        return new_replacement_tool(param)
    except Exception as e:
        logger.error(f"Error in deprecated_tool: {e}")
        raise
```

### Phase 3: Testing and Validation

#### 3.1 Update Tests

```bash
# Run existing tests to check for regressions
pytest tests/ -v

# Add tests for new tools
cat >> tests/test_new_tools.py << 'EOF'
def test_new_client_method(mock_get_client, mock_client):
    """Test the new client method tool."""
    mock_get_client.return_value = mock_client
    mock_client.module.new_method.return_value.model_dump.return_value = {"result": "success"}
    
    result = new_client_method("test_param")
    
    assert result["result"] == "success"
    mock_client.module.new_method.assert_called_once_with("test_param", None)
EOF

# Run updated test suite
pytest tests/ --cov=xplainable_mcp --cov-report=html
```

#### 3.2 Integration Testing

```bash
# Test with real API connection
XPLAINABLE_API_KEY=your_real_key xplainable-mcp-cli test-connection

# Verify tool listing reflects changes
xplainable-mcp-cli list-tools --format json | jq '.total_tools'

# Test new tools manually
python -c "
import os
from xplainable_mcp.server import new_client_method
os.environ['XPLAINABLE_API_KEY'] = 'your_real_key'
try:
    result = new_client_method('test')
    print('✅ New tool works correctly')
    print(result)
except Exception as e:
    print(f'❌ New tool failed: {e}')
"
```

#### 3.3 Compatibility Testing

```bash
# Test with different client versions
pip install xplainable-client==1.0.0  # Test with older version
python -m pytest tests/test_backward_compatibility.py

pip install xplainable-client==latest  # Return to latest
python -m pytest tests/ -v
```

### Phase 4: Documentation and Deployment

#### 4.1 Update Documentation

```bash
# Generate updated tool documentation
xplainable-mcp-cli generate-docs --output TOOLS.md

# Update README if needed
# Update CHANGELOG.md with changes
cat >> CHANGELOG.md << EOF

## [Unreleased]

### Added
- new_client_method: Support for new API endpoint
- Enhanced parameter validation for existing_tool

### Changed
- existing_tool: Added optional new_param parameter
- Updated xplainable-client dependency to v1.2.0

### Deprecated
- deprecated_tool: Use new_replacement_tool instead

### Fixed
- Fixed parameter handling in legacy_tool

EOF
```

#### 4.2 Update Version and Dependencies

```toml
# Update pyproject.toml
[project]
version = "0.2.0"  # Bump version appropriately
dependencies = [
    "xplainable-client>=1.2.0,<2.0.0",  # Update version constraint
    # ... other deps
]
```

#### 4.3 Prepare Release

```bash
# Commit changes
git add .
git commit -m "feat: sync with xplainable-client v1.2.0

- Add new_client_method tool
- Update existing_tool with new parameter
- Deprecate deprecated_tool
- Update tests and documentation

Resolves compatibility with xplainable-client 1.2.0"

# Tag release
git tag v0.2.0
git push origin main --tags

# Build and test package
python -m build
twine check dist/*
```

### Phase 5: Monitoring and Follow-up

#### 5.1 Post-Deployment Monitoring

```bash
# Monitor logs for errors after deployment
tail -f /var/log/xplainable-mcp.log | grep ERROR

# Check tool usage metrics
xplainable-mcp-cli list-tools --format json | jq '.summary'

# Validate all tools still work
python scripts/test_all_tools.py
```

#### 5.2 User Communication

Create announcements for:
- **Breaking changes**: Notify users of required configuration updates
- **New features**: Highlight new capabilities
- **Deprecations**: Provide migration timeline and guidance
- **Performance improvements**: Document any performance gains

Example announcement:
```markdown
## Xplainable MCP Server v0.2.0 Release

### 🆕 New Features
- Added support for new dataset analysis tools
- Enhanced model deployment capabilities

### ⚠️ Breaking Changes
- `old_authentication_method` has been replaced with `new_auth_flow`
- Update your configuration to use the new authentication

### 📖 Migration Guide
See MIGRATION.md for step-by-step upgrade instructions.
```

## Automation Opportunities

To streamline this process, consider automating:

### 5.3 CI/CD Integration

```yaml
# .github/workflows/sync-check.yml
name: Client Sync Check
on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly Monday check
  workflow_dispatch:

jobs:
  sync-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install --upgrade xplainable-client
      
      - name: Run sync analysis
        run: |
          python scripts/sync_analysis.py
          
      - name: Create issue if sync needed
        if: steps.sync.outputs.needs_update == 'true'
        uses: actions/create-issue@v1
        with:
          title: "Client sync required - xplainable-client updated"
          body: ${{ steps.sync.outputs.report }}
```

### 5.4 Monitoring Script

```bash
# scripts/monitor_client_updates.sh
#!/bin/bash
set -e

echo "Checking for xplainable-client updates..."

CURRENT_VERSION=$(pip show xplainable-client | grep Version | cut -d' ' -f2)
LATEST_VERSION=$(pip index versions xplainable-client | head -1 | cut -d' ' -f2)

if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    echo "🔄 Update available: $CURRENT_VERSION -> $LATEST_VERSION"
    echo "Run sync workflow: python scripts/sync_workflow.py"
    exit 1
else
    echo "✅ xplainable-client is up to date ($CURRENT_VERSION)"
fi
```

## Best Practices

1. **Version Pinning**: Always pin xplainable-client versions with appropriate ranges
2. **Backward Compatibility**: Maintain backward compatibility for at least one major version
3. **Feature Flags**: Use environment variables to enable/disable new features during transition
4. **Comprehensive Testing**: Test both new functionality and existing workflows
5. **Documentation**: Keep all documentation current with each sync
6. **Communication**: Notify users of changes with clear migration paths

## Troubleshooting Common Issues

### Authentication Changes
```bash
# If authentication flow changes
xplainable-mcp-cli test-connection  # Verify connectivity
# Update server.py authentication logic
# Test with both old and new auth methods during transition
```

### Parameter Mismatches
```bash
# Check function signatures
python -c "
import inspect
from xplainable_client.client.client import XplainableClient
client = XplainableClient(api_key='dummy')
print(inspect.signature(client.models.list_team_models))
"
# Update MCP tool signatures to match
```

### Type Changes
```bash
# Verify return types haven't changed
python -c "
from xplainable_client.client.client import XplainableClient
client = XplainableClient(api_key=os.environ['XPLAINABLE_API_KEY'])
result = client.models.list_team_models()
print(type(result[0]) if result else 'No results')
print(dir(result[0]) if result else 'No attributes')
"
```

## Conclusion

Regular synchronization ensures your MCP server stays current with the Xplainable platform's evolving capabilities. Following this workflow helps maintain reliability, security, and feature completeness while minimizing disruption to existing users.

Remember to always test thoroughly and communicate changes clearly to your users!