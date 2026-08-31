"""
Tests for the Xplainable MCP Server core: config, discovery, and
representative runtime tool wrappers.

fastmcp 2.x: @mcp.tool-decorated names are FunctionTool objects, not
callables — tools are fetched from the FastMCP registry and invoked via
`.fn(...)`. Runtime-generated wrappers resolve the client via
xplainable_mcp.runtime_tools.get_client, which is patched here.
"""

import asyncio

import pytest
from unittest.mock import Mock, patch

from xplainable_mcp.server import ServerConfig, load_config, mcp


@pytest.fixture(scope="module")
def tool_map():
    """All registered tools."""
    return asyncio.run(mcp.get_tools())


@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "test-api-key")
    monkeypatch.setenv("XPLAINABLE_HOST", "https://test.xplainable.io")
    monkeypatch.setenv("XPLAINABLE_ORG_ID", "test-org")
    monkeypatch.setenv("XPLAINABLE_TEAM_ID", "test-team")
    monkeypatch.setenv("ENABLE_WRITE_TOOLS", "false")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")


class TestServerConfig:
    """Test server configuration."""

    def test_load_config_with_all_vars(self, mock_env_vars):
        config = load_config()

        assert config.api_key == "test-api-key"
        assert config.hostname == "https://test.xplainable.io"
        assert config.org_id == "test-org"
        assert config.team_id == "test-team"
        assert config.enable_write_tools is False
        assert config.rate_limit_enabled is True

    def test_load_config_missing_credentials(self, monkeypatch):
        """Without an API key or Auth0 domain the server refuses to start."""
        monkeypatch.delenv("XPLAINABLE_API_KEY", raising=False)
        monkeypatch.delenv("AUTH0_DOMAIN", raising=False)

        with pytest.raises(SystemExit):
            load_config()

    def test_defaults(self):
        config = ServerConfig(api_key="k")
        assert config.hostname == "https://platform.xplainable.io"
        assert config.enable_write_tools is True


class TestModelTools:
    """Representative runtime read-tool wrappers (patched client)."""

    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_models_list_team_models(self, mock_get_client, tool_map):
        model_mock = Mock()
        model_mock.model_dump.return_value = {"id": "model-1", "name": "Test Model"}
        client = Mock()
        client.models.list_team_models.return_value = [model_mock]
        mock_get_client.return_value = client

        result = asyncio.run(tool_map["models_list_team_models"].fn())

        assert result == [{"id": "model-1", "name": "Test Model"}]
        client.models.list_team_models.assert_called_once_with()

    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_models_get_model(self, mock_get_client, tool_map):
        client = Mock()
        client.models.get_model.return_value = {"id": "model-1"}
        mock_get_client.return_value = client

        result = asyncio.run(tool_map["models_get_model"].fn(model_id="model-1"))

        assert result == {"id": "model-1"}
        client.models.get_model.assert_called_once_with(model_id="model-1")

    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_tool_error_propagates(self, mock_get_client, tool_map):
        client = Mock()
        client.models.get_model.side_effect = Exception("API Error")
        mock_get_client.return_value = client

        with pytest.raises(Exception, match="API Error"):
            asyncio.run(tool_map["models_get_model"].fn(model_id="model-1"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
