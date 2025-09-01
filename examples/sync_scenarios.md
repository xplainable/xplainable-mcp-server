# Sync Scenarios - Common Update Examples

This document provides real-world examples of common synchronization scenarios you may encounter when the xplainable-client is updated.

## Scenario 1: New API Endpoint Added

### Situation
The xplainable-client adds a new method `client.datasets.get_dataset_statistics(dataset_id)` that returns statistical analysis of a dataset.

### Detection
```bash
# Run sync analysis
python scripts/sync_workflow.py --markdown sync_report.md

# Output shows:
# Missing Tools:
# - datasets_get_dataset_statistics
```

### Implementation

1. **Add the new tool to server.py:**

```python
@mcp.tool()
def get_dataset_statistics(dataset_id: str) -> Dict[str, Any]:
    """
    Get statistical analysis of a dataset.
    
    Args:
        dataset_id: The ID of the dataset to analyze
        
    Returns:
        Dictionary containing dataset statistics
    """
    try:
        client = get_client()
        result = client.datasets.get_dataset_statistics(dataset_id)
        logger.info(f"Retrieved statistics for dataset: {dataset_id}")
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        logger.error(f"Error getting dataset statistics for {dataset_id}: {e}")
        raise
```

2. **Add corresponding test:**

```python
@patch('xplainable_mcp.server.get_client')
def test_get_dataset_statistics(self, mock_get_client, mock_client):
    """Test getting dataset statistics."""
    mock_get_client.return_value = mock_client
    
    # Mock the new method
    stats_mock = Mock()
    stats_mock.model_dump.return_value = {
        "total_rows": 1000,
        "columns": 15,
        "missing_values": 23,
        "data_types": {"numeric": 10, "categorical": 5}
    }
    mock_client.datasets.get_dataset_statistics.return_value = stats_mock
    
    result = get_dataset_statistics("dataset-123")
    
    assert result["total_rows"] == 1000
    assert result["columns"] == 15
    mock_client.datasets.get_dataset_statistics.assert_called_once_with("dataset-123")
```

3. **Update documentation:**

```markdown
### Read-Only Tools

- `get_dataset_statistics(dataset_id)` - Get statistical analysis of a dataset
```

---

## Scenario 2: Parameter Added to Existing Method

### Situation
The existing method `client.models.list_team_models(team_id)` now accepts an additional optional parameter `include_archived: bool = False`.

### Detection
```bash
# Current MCP tool signature doesn't match client method
# May cause runtime errors or miss functionality
```

### Implementation

1. **Update the existing tool:**

```python
@mcp.tool()
def list_team_models(
    team_id_override: Optional[str] = None,
    include_archived: bool = False  # New parameter
) -> List[Dict[str, Any]]:
    """
    List models for the current team or a provided team_id.
    
    Args:
        team_id_override: Optional team ID to override the default
        include_archived: Include archived models in the results
        
    Returns:
        List of model information dictionaries
    """
    try:
        client = get_client()
        models = client.models.list_team_models(
            team_id=team_id_override,
            include_archived=include_archived  # Pass new parameter
        )
        result = [m.model_dump() for m in models]
        logger.info(f"Listed {len(result)} models for team: {team_id_override or config.team_id} (archived: {include_archived})")
        return result
    except Exception as e:
        logger.error(f"Error listing team models: {e}")
        raise
```

2. **Update test to cover new parameter:**

```python
@patch('xplainable_mcp.server.get_client')
def test_list_team_models_with_archived(self, mock_get_client, mock_client):
    """Test listing team models including archived."""
    mock_get_client.return_value = mock_client
    
    # Mock both regular and archived models
    regular_model = Mock()
    regular_model.model_dump.return_value = {"id": "model-1", "name": "Active Model", "archived": False}
    archived_model = Mock() 
    archived_model.model_dump.return_value = {"id": "model-2", "name": "Old Model", "archived": True}
    
    mock_client.models.list_team_models.return_value = [regular_model, archived_model]
    
    result = list_team_models(include_archived=True)
    
    assert len(result) == 2
    mock_client.models.list_team_models.assert_called_once_with(
        team_id=None, 
        include_archived=True
    )
```

---

## Scenario 3: Method Signature Changed (Breaking Change)

### Situation
The method `client.deployments.deploy(model_version_id)` now requires additional parameters: `deploy(model_version_id, environment, scaling_config)`.

### Detection
```bash
# Runtime errors when calling the tool
# Tests failing due to signature mismatch
```

### Implementation

1. **Update the tool with new required parameters:**

```python
@mcp.tool()
def deploy_model(
    model_version_id: str,
    environment: str,
    scaling_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deploy a model version to a specified environment.
    
    Args:
        model_version_id: The model version to deploy
        environment: Target environment (e.g., 'staging', 'production')
        scaling_config: Configuration for scaling (min/max instances, etc.)
        
    Returns:
        Dictionary containing deployment information
    """
    try:
        client = get_client()
        result = client.deployments.deploy(
            model_version_id=model_version_id,
            environment=environment,
            scaling_config=scaling_config
        )
        logger.info(f"Deployed model version {model_version_id} to {environment}")
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        logger.error(f"Error deploying model version {model_version_id}: {e}")
        raise
```

2. **Add backward compatibility wrapper (if needed):**

```python
@mcp.tool()
def deploy_model_simple(model_version_id: str) -> Dict[str, Any]:
    """
    [DEPRECATED] Deploy a model version with default settings.
    Use 'deploy_model' for full configuration options.
    
    This tool provides backward compatibility and will be removed in v2.0.
    """
    logger.warning("deploy_model_simple is deprecated, use deploy_model instead")
    
    # Provide sensible defaults
    default_config = {
        "min_instances": 1,
        "max_instances": 3,
        "instance_type": "standard"
    }
    
    return deploy_model(
        model_version_id=model_version_id,
        environment="staging",  # Default to staging for safety
        scaling_config=default_config
    )
```

3. **Update documentation and migration guide:**

```markdown
## Breaking Changes in v1.2.0

### deploy_model Tool
The `deploy_model` tool now requires additional parameters:

**Old usage:**
```json
{
  "tool": "deploy_model",
  "arguments": {
    "model_version_id": "version-123"
  }
}
```

**New usage:**
```json
{
  "tool": "deploy_model", 
  "arguments": {
    "model_version_id": "version-123",
    "environment": "staging",
    "scaling_config": {
      "min_instances": 1,
      "max_instances": 5,
      "instance_type": "standard"
    }
  }
}
```

**Migration:** Use `deploy_model_simple` for temporary compatibility, but update to new signature for production use.
```

---

## Scenario 4: Method Deprecated/Removed

### Situation
The method `client.legacy.old_analysis_method()` has been deprecated and replaced with `client.analysis.new_analysis_method()`.

### Detection
```bash
# Client method no longer exists
# ImportError or AttributeError when trying to call
```

### Implementation

1. **Mark tool as deprecated and provide migration:**

```python
@mcp.tool()
def old_analysis_method() -> Dict[str, Any]:
    """
    [DEPRECATED] Legacy analysis method - will be removed in v2.0.
    Use 'new_analysis_method' instead.
    
    Returns:
        Analysis results using the new method
    """
    logger.warning("old_analysis_method is deprecated and will be removed in v2.0. Use new_analysis_method instead.")
    
    # Redirect to new method
    return new_analysis_method()


@mcp.tool()
def new_analysis_method() -> Dict[str, Any]:
    """
    Perform modern analysis using the updated API.
    
    Returns:
        Dictionary containing analysis results
    """
    try:
        client = get_client()
        result = client.analysis.new_analysis_method()
        logger.info("Executed new analysis method")
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        logger.error(f"Error in new analysis method: {e}")
        raise
```

2. **Plan removal timeline:**

```python
# In version 1.3.0 - add removal warning
@mcp.tool()
def old_analysis_method() -> Dict[str, Any]:
    """[DEPRECATED - REMOVAL PLANNED] This tool will be removed in v2.0."""
    logger.error("old_analysis_method has been deprecated and will be removed in v2.0. Please update to use new_analysis_method.")
    raise DeprecationWarning("Tool deprecated - use new_analysis_method instead")

# In version 2.0.0 - remove entirely
# (delete the function)
```

---

## Scenario 5: Authentication Method Changed

### Situation
The xplainable-client now uses OAuth2 instead of API keys, requiring changes to how the client is initialized.

### Detection
```bash
# Authentication errors when starting server
# Client initialization fails
```

### Implementation

1. **Update server configuration:**

```python
# In server.py - update ServerConfig
class ServerConfig(BaseModel):
    """Server configuration model."""
    # Legacy API key support
    api_key: Optional[str] = Field(None, description="Legacy API key (deprecated)")
    
    # New OAuth2 configuration
    oauth_client_id: Optional[str] = Field(None, description="OAuth2 client ID")
    oauth_client_secret: Optional[str] = Field(None, description="OAuth2 client secret")
    oauth_token_url: str = Field(
        default="https://auth.xplainable.io/oauth/token",
        description="OAuth2 token endpoint"
    )
    
    # ... other existing fields

def get_client():
    """Get or create the Xplainable client instance with flexible auth."""
    global _client
    if _client is None:
        try:
            from xplainable_client.client.client import XplainableClient
            
            # Try OAuth2 first, fall back to API key
            if config.oauth_client_id and config.oauth_client_secret:
                _client = XplainableClient(
                    oauth_client_id=config.oauth_client_id,
                    oauth_client_secret=config.oauth_client_secret,
                    oauth_token_url=config.oauth_token_url,
                    hostname=config.hostname,
                    org_id=config.org_id,
                    team_id=config.team_id
                )
                logger.info("Xplainable client initialized with OAuth2")
            elif config.api_key:
                logger.warning("Using deprecated API key authentication. Migrate to OAuth2.")
                _client = XplainableClient(
                    api_key=config.api_key,
                    hostname=config.hostname,
                    org_id=config.org_id,
                    team_id=config.team_id
                )
                logger.info("Xplainable client initialized with API key (deprecated)")
            else:
                logger.error("No authentication method configured. Set either OAUTH_CLIENT_ID/SECRET or XPLAINABLE_API_KEY")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Failed to initialize Xplainable client: {e}")
            sys.exit(1)
    return _client
```

2. **Update environment configuration:**

```bash
# .env.example - add OAuth2 options
# Legacy authentication (deprecated)
XPLAINABLE_API_KEY=your-api-key-here

# New OAuth2 authentication (recommended)
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
OAUTH_TOKEN_URL=https://auth.xplainable.io/oauth/token
```

3. **Provide migration documentation:**

```markdown
## Authentication Migration Guide

### Background
Starting with xplainable-client v2.0, OAuth2 is the preferred authentication method.

### Migration Steps

1. **Obtain OAuth2 credentials from the Xplainable dashboard**
2. **Update your environment configuration:**
   ```bash
   # Replace API key with OAuth2
   # XPLAINABLE_API_KEY=old-key  # Remove this
   OAUTH_CLIENT_ID=your-client-id
   OAUTH_CLIENT_SECRET=your-client-secret
   ```
3. **Restart your MCP server**
4. **Verify connection:** `xplainable-mcp-cli test-connection`

### Backward Compatibility
API key authentication will continue to work until v2.0 but will show deprecation warnings.
```

---

## Scenario 6: Return Type Changed

### Situation
The method `client.models.get_model_metrics(model_id)` now returns a `ModelMetrics` Pydantic model instead of a plain dictionary.

### Detection
```bash
# Runtime errors when accessing result fields
# Type checking failures
```

### Implementation

1. **Update tool to handle new return type:**

```python
@mcp.tool()
def get_model_metrics(model_id: str) -> Dict[str, Any]:
    """
    Get performance metrics for a model.
    
    Args:
        model_id: The model ID
        
    Returns:
        Dictionary containing model metrics
    """
    try:
        client = get_client()
        result = client.models.get_model_metrics(model_id)
        
        # Handle both old dict format and new Pydantic model
        if hasattr(result, 'model_dump'):
            # New Pydantic model format
            metrics_dict = result.model_dump()
        else:
            # Legacy dict format
            metrics_dict = result
            
        logger.info(f"Retrieved metrics for model: {model_id}")
        return metrics_dict
    except Exception as e:
        logger.error(f"Error getting model metrics for {model_id}: {e}")
        raise
```

2. **Update tests for new return type:**

```python
@patch('xplainable_mcp.server.get_client')
def test_get_model_metrics_new_format(self, mock_get_client, mock_client):
    """Test getting model metrics with new Pydantic return type."""
    mock_get_client.return_value = mock_client
    
    # Mock new Pydantic model response
    metrics_mock = Mock()
    metrics_mock.model_dump.return_value = {
        "accuracy": 0.95,
        "precision": 0.92,
        "recall": 0.88,
        "f1_score": 0.90
    }
    mock_client.models.get_model_metrics.return_value = metrics_mock
    
    result = get_model_metrics("model-123")
    
    assert result["accuracy"] == 0.95
    assert result["f1_score"] == 0.90
    mock_client.models.get_model_metrics.assert_called_once_with("model-123")
```

---

## Automated Detection and Handling

### CI/CD Pipeline Integration

```yaml
# .github/workflows/client-sync-check.yml
name: Client Sync Check
on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly Monday check
  push:
    paths: 
      - 'requirements.txt'
      - 'pyproject.toml'

jobs:
  sync-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -e .
      
      - name: Run sync analysis  
        run: python scripts/sync_workflow.py --markdown sync_report.md
        env:
          XPLAINABLE_API_KEY: ${{ secrets.XPLAINABLE_API_KEY }}
      
      - name: Upload sync report
        uses: actions/upload-artifact@v3
        with:
          name: sync-report
          path: sync_report.md
          
      - name: Create issue if sync needed
        if: failure()  # sync_workflow.py exits 1 if sync needed
        uses: actions/create-issue@v1
        with:
          title: "🔄 Client synchronization required"
          body: |
            The automated sync check detected that the MCP server needs updates.
            
            Please review the sync report and implement necessary changes.
            
            Generated by: ${{ github.workflow }} #${{ github.run_number }}
          assignees: maintainer-username
```

### Monitoring Script

```python
#!/usr/bin/env python
"""
Continuous monitoring script for client changes.
Run this periodically to detect when sync is needed.
"""

import time
import requests
import json
from datetime import datetime

def check_pypi_version():
    """Check latest xplainable-client version on PyPI."""
    try:
        response = requests.get("https://pypi.org/pypi/xplainable-client/json")
        data = response.json()
        return data["info"]["version"]
    except Exception as e:
        print(f"Error checking PyPI: {e}")
        return None

def load_last_known_version():
    """Load the last known version from file."""
    try:
        with open('.last_client_version', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_version(version):
    """Save the current version to file."""
    with open('.last_client_version', 'w') as f:
        f.write(version)

def main():
    """Check for version changes and alert if needed."""
    current_version = check_pypi_version()
    if not current_version:
        return
    
    last_version = load_last_known_version()
    
    if last_version != current_version:
        print(f"🔄 New xplainable-client version detected: {last_version} -> {current_version}")
        print("Run sync workflow: python scripts/sync_workflow.py --markdown report.md")
        
        # Save new version
        save_version(current_version)
        
        # Exit with code 1 to indicate action needed
        exit(1)
    else:
        print(f"✅ No updates detected (current: {current_version})")

if __name__ == "__main__":
    main()
```

This comprehensive guide covers the most common scenarios you'll encounter when synchronizing with xplainable-client updates, providing practical examples and automation strategies to streamline the process.