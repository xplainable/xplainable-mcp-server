"""
Tests for the Xplainable MCP Server.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Mock the xplainable_client module before importing server
import sys
sys.modules['xplainable_client'] = MagicMock()
sys.modules['xplainable_client.client'] = MagicMock()
sys.modules['xplainable_client.client.client'] = MagicMock()

from xplainable_mcp.server import (
    ServerConfig,
    load_config,
    list_tools,
    get_connection_info,
    list_team_models,
    get_model,
    list_model_versions,
    list_deployments,
    get_active_team_deploy_keys_count,
    list_preprocessors,
    get_preprocessor,
    get_collection_scenarios,
    misc_get_version_info,
)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("XPLAINABLE_API_KEY", "test-api-key")
    monkeypatch.setenv("XPLAINABLE_HOST", "https://test.xplainable.io")
    monkeypatch.setenv("XPLAINABLE_ORG_ID", "test-org")
    monkeypatch.setenv("XPLAINABLE_TEAM_ID", "test-team")
    monkeypatch.setenv("ENABLE_WRITE_TOOLS", "false")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")


@pytest.fixture
def mock_client():
    """Create a mock Xplainable client."""
    client = Mock()
    
    # Mock connection info
    client.connection_info = {
        "hostname": "https://test.xplainable.io",
        "username": "test-user",
        "api_key_expires": "2024-12-31",
        "xplainable_version": "1.0.0",
        "python_version": "3.11.0",
        "org_id": "test-org",
        "team_id": "test-team",
    }
    
    # Mock models client
    client.models = Mock()
    model_mock = Mock()
    model_mock.model_dump.return_value = {"id": "model-1", "name": "Test Model"}
    client.models.list_team_models.return_value = [model_mock]
    client.models.get_model.return_value = model_mock
    client.models.list_model_versions.return_value = [model_mock]
    
    # Mock deployments client
    client.deployments = Mock()
    deployment_mock = Mock()
    deployment_mock.model_dump.return_value = {"id": "deploy-1", "status": "active"}
    client.deployments.list_deployments.return_value = [deployment_mock]
    client.deployments.get_active_team_deploy_keys_count.return_value = 5
    client.deployments.activate_deployment.return_value = {"status": "activated"}
    client.deployments.deactivate_deployment.return_value = {"status": "deactivated"}
    client.deployments.generate_deploy_key.return_value = "key-uuid-123"
    
    # Mock preprocessing client
    client.preprocessing = Mock()
    preprocessor_mock = Mock()
    preprocessor_mock.model_dump.return_value = {"id": "prep-1", "type": "standard"}
    client.preprocessing.list_preprocessors.return_value = [preprocessor_mock]
    client.preprocessing.get_preprocessor.return_value = preprocessor_mock
    
    # Mock collections client
    client.collections = Mock()
    client.collections.get_collection_scenarios.return_value = [
        {"id": "scenario-1", "name": "Test Scenario"}
    ]
    
    # Mock misc client
    client.misc = Mock()
    version_mock = Mock()
    version_mock.model_dump.return_value = {"version": "1.0.0", "api_version": "v1"}
    client.misc.get_version_info.return_value = version_mock
    
    # Mock GPT client
    client.gpt = Mock()
    report_mock = Mock()
    report_mock.model_dump.return_value = {"report": "Generated report content"}
    client.gpt.generate_report.return_value = report_mock
    
    return client


class TestServerConfig:
    """Test server configuration."""
    
    def test_load_config_with_all_vars(self, mock_env_vars):
        """Test loading configuration with all environment variables set."""
        config = load_config()
        
        assert config.api_key == "test-api-key"
        assert config.hostname == "https://test.xplainable.io"
        assert config.org_id == "test-org"
        assert config.team_id == "test-team"
        assert config.enable_write_tools is False
        assert config.rate_limit_enabled is True
    
    def test_load_config_missing_api_key(self, monkeypatch):
        """Test that missing API key causes exit."""
        monkeypatch.delenv("XPLAINABLE_API_KEY", raising=False)
        
        with pytest.raises(SystemExit):
            load_config()


class TestDiscoveryTools:
    """Test discovery and metadata tools."""
    
    def test_list_tools(self):
        """Test listing all available tools."""
        result = list_tools()
        
        assert "server_version" in result
        assert "total_tools" in result
        assert "categories" in result
        assert "summary" in result
        
        # Check categories
        assert "discovery" in result["categories"]
        assert "read" in result["categories"]
        assert "write" in result["categories"]
        
        # Check summary
        summary = result["summary"]
        assert "discovery_tools" in summary
        assert "read_tools" in summary
        assert "write_tools" in summary
        assert "write_tools_enabled" in summary
        
        # Verify at least the list_tools function itself is listed
        discovery_tools = result["categories"]["discovery"]
        tool_names = [tool["name"] for tool in discovery_tools]
        assert "list_tools" in tool_names
        
        # Verify total count matches
        total_from_categories = (
            len(result["categories"]["discovery"]) +
            len(result["categories"]["read"]) +
            len(result["categories"]["write"])
        )
        assert result["total_tools"] == total_from_categories


class TestReadOnlyTools:
    """Test read-only MCP tools."""
    
    @patch('xplainable_mcp.server.get_client')
    def test_get_connection_info(self, mock_get_client, mock_client):
        """Test getting connection information."""
        mock_get_client.return_value = mock_client
        
        result = get_connection_info()
        
        assert result["hostname"] == "https://test.xplainable.io"
        assert result["username"] == "test-user"
        assert result["api_key_expires"] == "2024-12-31"
        assert "api_key" not in result  # Ensure no sensitive data
    
    @patch('xplainable_mcp.server.get_client')
    def test_list_team_models(self, mock_get_client, mock_client):
        """Test listing team models."""
        mock_get_client.return_value = mock_client
        
        result = list_team_models()
        
        assert len(result) == 1
        assert result[0]["id"] == "model-1"
        assert result[0]["name"] == "Test Model"
        mock_client.models.list_team_models.assert_called_once_with(team_id=None)
    
    @patch('xplainable_mcp.server.get_client')
    def test_list_team_models_with_override(self, mock_get_client, mock_client):
        """Test listing team models with team_id override."""
        mock_get_client.return_value = mock_client
        
        result = list_team_models(team_id_override="other-team")
        
        assert len(result) == 1
        mock_client.models.list_team_models.assert_called_once_with(team_id="other-team")
    
    @patch('xplainable_mcp.server.get_client')
    def test_get_model(self, mock_get_client, mock_client):
        """Test getting a specific model."""
        mock_get_client.return_value = mock_client
        
        result = get_model("model-1")
        
        assert result["id"] == "model-1"
        assert result["name"] == "Test Model"
        mock_client.models.get_model.assert_called_once_with("model-1")
    
    @patch('xplainable_mcp.server.get_client')
    def test_list_model_versions(self, mock_get_client, mock_client):
        """Test listing model versions."""
        mock_get_client.return_value = mock_client
        
        result = list_model_versions("model-1")
        
        assert len(result) == 1
        mock_client.models.list_model_versions.assert_called_once_with("model-1")
    
    @patch('xplainable_mcp.server.get_client')
    def test_list_deployments(self, mock_get_client, mock_client):
        """Test listing deployments."""
        mock_get_client.return_value = mock_client
        
        result = list_deployments()
        
        assert len(result) == 1
        assert result[0]["id"] == "deploy-1"
        assert result[0]["status"] == "active"
        mock_client.deployments.list_deployments.assert_called_once_with(team_id=None)
    
    @patch('xplainable_mcp.server.get_client')
    def test_get_active_team_deploy_keys_count(self, mock_get_client, mock_client):
        """Test getting active deploy keys count."""
        mock_get_client.return_value = mock_client
        
        result = get_active_team_deploy_keys_count()
        
        assert result == 5
        mock_client.deployments.get_active_team_deploy_keys_count.assert_called_once()
    
    @patch('xplainable_mcp.server.get_client')
    def test_list_preprocessors(self, mock_get_client, mock_client):
        """Test listing preprocessors."""
        mock_get_client.return_value = mock_client
        
        result = list_preprocessors()
        
        assert len(result) == 1
        assert result[0]["id"] == "prep-1"
        assert result[0]["type"] == "standard"
        mock_client.preprocessing.list_preprocessors.assert_called_once()
    
    @patch('xplainable_mcp.server.get_client')
    def test_get_preprocessor(self, mock_get_client, mock_client):
        """Test getting a specific preprocessor."""
        mock_get_client.return_value = mock_client
        
        result = get_preprocessor("prep-1")
        
        assert result["id"] == "prep-1"
        assert result["type"] == "standard"
        mock_client.preprocessing.get_preprocessor.assert_called_once_with("prep-1")
    
    @patch('xplainable_mcp.server.get_client')
    def test_get_collection_scenarios(self, mock_get_client, mock_client):
        """Test getting collection scenarios."""
        mock_get_client.return_value = mock_client
        
        result = get_collection_scenarios("collection-1")
        
        assert len(result) == 1
        assert result[0]["id"] == "scenario-1"
        assert result[0]["name"] == "Test Scenario"
        mock_client.collections.get_collection_scenarios.assert_called_once_with("collection-1")
    
    @patch('xplainable_mcp.server.get_client')
    def test_misc_get_version_info(self, mock_get_client, mock_client):
        """Test getting version information."""
        mock_get_client.return_value = mock_client
        
        result = misc_get_version_info()
        
        assert result["version"] == "1.0.0"
        assert result["api_version"] == "v1"
        mock_client.misc.get_version_info.assert_called_once()


class TestErrorHandling:
    """Test error handling in MCP tools."""
    
    @patch('xplainable_mcp.server.get_client')
    def test_tool_error_handling(self, mock_get_client):
        """Test that tool errors are properly logged and re-raised."""
        mock_client = Mock()
        mock_client.models.list_team_models.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client
        
        with pytest.raises(Exception, match="API Error"):
            list_team_models()
    
    @patch('xplainable_mcp.server.get_client')
    def test_connection_error(self, mock_get_client):
        """Test handling of connection errors."""
        mock_get_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            get_connection_info()


@pytest.mark.skipif(
    "ENABLE_WRITE_TOOLS" not in os.environ or os.environ["ENABLE_WRITE_TOOLS"] != "true",
    reason="Write tools not enabled"
)
class TestWriteTools:
    """Test write-enabled MCP tools."""
    
    @patch('xplainable_mcp.server.config.enable_write_tools', True)
    @patch('xplainable_mcp.server.get_client')
    def test_generate_deploy_key(self, mock_get_client, mock_client):
        """Test generating a deploy key."""
        mock_get_client.return_value = mock_client
        
        # Import the function dynamically since it's conditionally defined
        from xplainable_mcp.server import generate_deploy_key
        
        result = generate_deploy_key("deploy-1", "Test key", 30)
        
        assert result == "key-uuid-123"
        mock_client.deployments.generate_deploy_key.assert_called_once_with(
            "deploy-1", "Test key", 30
        )
    
    @patch('xplainable_mcp.server.config.enable_write_tools', True)
    @patch('xplainable_mcp.server.get_client')
    def test_activate_deployment(self, mock_get_client, mock_client):
        """Test activating a deployment."""
        mock_get_client.return_value = mock_client
        
        from xplainable_mcp.server import activate_deployment
        
        result = activate_deployment("deploy-1")
        
        assert result["status"] == "activated"
        mock_client.deployments.activate_deployment.assert_called_once_with("deploy-1")
    
    @patch('xplainable_mcp.server.config.enable_write_tools', True)
    @patch('xplainable_mcp.server.get_client')
    def test_deactivate_deployment(self, mock_get_client, mock_client):
        """Test deactivating a deployment."""
        mock_get_client.return_value = mock_client
        
        from xplainable_mcp.server import deactivate_deployment
        
        result = deactivate_deployment("deploy-1")
        
        assert result["status"] == "deactivated"
        mock_client.deployments.deactivate_deployment.assert_called_once_with("deploy-1")
    
    @patch('xplainable_mcp.server.config.enable_write_tools', True)
    @patch('xplainable_mcp.server.get_client')
    def test_gpt_generate_report(self, mock_get_client, mock_client):
        """Test generating a GPT report."""
        mock_get_client.return_value = mock_client
        
        from xplainable_mcp.server import gpt_generate_report
        
        result = gpt_generate_report(
            "model-1",
            "version-1",
            "Target description",
            "Project objective",
            10,
            0.5
        )
        
        assert result["report"] == "Generated report content"
        mock_client.gpt.generate_report.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])