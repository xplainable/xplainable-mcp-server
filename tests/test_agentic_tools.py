"""
Tests for the agentic lifecycle MCP tools (XGM v2 primary workflow).

The agentic tools mirror the client's AgenticClient lifecycle so the MCP
server can trigger server-side v2 training. The raw-blob persistence path
(models_create_model_v2) must NOT be exposed as a tool.
"""

import inspect
import pytest
from unittest.mock import Mock, patch

from xplainable_mcp.tools import agentic
from xplainable_mcp.tools import models as models_tools


EXPECTED_TOOLS = [
    "agentic_start_run",
    "agentic_get_run_state",
    "agentic_get_pending_decision",
    "agentic_submit_decision",
    "agentic_send_chat",
    "agentic_cancel_run",
    "agentic_skip_phase",
    "agentic_get_phases",
    "agentic_retrain",
]


@pytest.fixture
def mock_client():
    client = Mock()
    client.agentic = Mock()
    return client


class TestToolSurface:
    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_exists(self, tool_name):
        assert callable(getattr(agentic, tool_name, None)), f"missing {tool_name}"

    def test_create_model_v2_not_exposed(self):
        # Raw-blob persistence is the internal training agent's path only.
        # Exposing it would let MCP consumers push arbitrary v2 blobs,
        # bypassing server-side-only training.
        assert not hasattr(models_tools, "models_create_model_v2")

    def test_agentic_module_registered(self):
        from xplainable_mcp import tools
        assert hasattr(tools, "agentic")


class TestWorkflowMetadata:
    def test_start_run_is_step_1_write(self):
        doc = agentic.agentic_start_run.__doc__
        assert "Category: write" in doc
        assert "Workflow: Step 1" in doc

    def test_get_run_state_is_step_2_read(self):
        doc = agentic.agentic_get_run_state.__doc__
        assert "Category: read" in doc
        assert "Workflow: Step 2" in doc

    @pytest.mark.parametrize("tool_name,category", [
        ("agentic_get_pending_decision", "read"),
        ("agentic_get_phases", "read"),
        ("agentic_submit_decision", "write"),
        ("agentic_send_chat", "write"),
        ("agentic_cancel_run", "write"),
        ("agentic_skip_phase", "write"),
        ("agentic_retrain", "write"),
    ])
    def test_categories(self, tool_name, category):
        doc = getattr(agentic, tool_name).__doc__
        assert f"Category: {category}" in doc


class TestStartRunDefaults:
    @patch("xplainable_mcp.tools.agentic.get_client")
    def test_defaults_are_v2_auto(self, mock_get_client, mock_client):
        """Simple case = one call: auto_mode on, algorithm xgm."""
        mock_get_client.return_value = mock_client
        mock_client.agentic.start_run.return_value = {"run_id": "r1"}

        agentic.agentic_start_run(model_name="My Model")

        kwargs = mock_client.agentic.start_run.call_args.kwargs
        assert kwargs["auto_mode"] is True
        assert kwargs["algorithm"] == "xgm"

    @patch("xplainable_mcp.tools.agentic.get_client")
    def test_overrides_forwarded(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.agentic.start_run.return_value = {"run_id": "r1"}

        agentic.agentic_start_run(
            model_name="M",
            auto_mode=False,
            algorithm="xplainable",
            run_id="seeded-run",
            user_query="predict churn",
        )

        kwargs = mock_client.agentic.start_run.call_args.kwargs
        assert kwargs["auto_mode"] is False
        assert kwargs["algorithm"] == "xplainable"
        assert kwargs["run_id"] == "seeded-run"
        assert kwargs["user_query"] == "predict churn"


class TestLifecycleCalls:
    @patch("xplainable_mcp.tools.agentic.get_client")
    def test_get_run_state(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.agentic.get_run_state.return_value = {"status": "running"}

        result = agentic.agentic_get_run_state("run-1")

        assert result == {"status": "running"}
        mock_client.agentic.get_run_state.assert_called_once_with("run-1")

    @patch("xplainable_mcp.tools.agentic.get_client")
    def test_submit_decision_forwards_fields(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.agentic.submit_decision.return_value = {"status": "ok"}

        agentic.agentic_submit_decision(
            run_id="run-1",
            decision_type="model_deployment",
            action="approve",
        )

        kwargs = mock_client.agentic.submit_decision.call_args.kwargs
        assert kwargs["run_id"] == "run-1"
        assert kwargs["decision_type"] == "model_deployment"
        assert kwargs["action"] == "approve"

    @patch("xplainable_mcp.tools.agentic.get_client")
    def test_send_chat(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        reply = Mock()
        reply.model_dump.return_value = {"content": "hi"}
        mock_client.agentic.send_chat.return_value = reply

        result = agentic.agentic_send_chat("run-1", "explain the metrics")

        assert result == {"content": "hi"}
        mock_client.agentic.send_chat.assert_called_once_with(
            "run-1", "explain the metrics"
        )

    @patch("xplainable_mcp.tools.agentic.get_client")
    def test_cancel_skip_phases_retrain(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.agentic.cancel_run.return_value = {"success": True}
        mock_client.agentic.skip_phase.return_value = {"skipped_phase": "x"}
        mock_client.agentic.get_phases.return_value = [{"phase": "p"}]
        mock_client.agentic.get_pending_decision.return_value = None
        mock_client.agentic.retrain.return_value = {"status": "queued"}

        assert agentic.agentic_cancel_run("r") == {"success": True}
        assert agentic.agentic_skip_phase("r") == {"skipped_phase": "x"}
        assert agentic.agentic_get_phases("r") == [{"phase": "p"}]
        assert agentic.agentic_get_pending_decision("r") is None
        assert agentic.agentic_retrain("r") == {"status": "queued"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
