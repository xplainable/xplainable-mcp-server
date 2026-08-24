"""
Tests for the agentic lifecycle MCP tools (server-side pipeline control).

The agentic tools are runtime-generated from the client's AgenticClient
@mcp_tool methods. The raw-blob persistence path (models_create_model_v2)
must NOT be exposed as a tool.
"""

import asyncio
import inspect

import pytest
from unittest.mock import Mock, patch

from xplainable_mcp.server import mcp


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


@pytest.fixture(scope="module")
def tool_map():
    return asyncio.run(mcp.get_tools())


@pytest.fixture
def mock_client():
    client = Mock()
    client.agentic = Mock()
    return client


class TestToolSurface:
    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_exists(self, tool_map, tool_name):
        assert tool_name in tool_map, f"missing {tool_name}"

    def test_create_model_v2_not_exposed(self, tool_map):
        # Raw-blob persistence is the internal training agent's path only.
        # Exposing it would let MCP consumers push arbitrary v2 blobs,
        # bypassing server-side-only training.
        assert "models_create_model_v2" not in tool_map


class TestWorkflowMetadata:
    """Category and step metadata come from the client @mcp_tool registry."""

    def _registry_entry(self, tool_name):
        from xplainable_mcp.runtime_tools import (
            derive_tool_name,
            iter_registry_entries,
        )

        for entry in iter_registry_entries():
            if derive_tool_name(entry) == tool_name:
                return entry
        raise AssertionError(f"{tool_name} not in registry")

    def test_start_run_is_step_1_write(self, tool_map):
        entry = self._registry_entry("agentic_start_run")
        assert entry["category"].value == "write"
        assert entry["step"] == 1
        assert "write" in tool_map["agentic_start_run"].tags

    def test_get_run_state_is_step_2_read(self, tool_map):
        entry = self._registry_entry("agentic_get_run_state")
        assert entry["category"].value == "read"
        assert entry["step"] == 2
        assert "read" in tool_map["agentic_get_run_state"].tags

    @pytest.mark.parametrize("tool_name,category", [
        ("agentic_get_pending_decision", "read"),
        ("agentic_get_phases", "read"),
        ("agentic_submit_decision", "write"),
        ("agentic_send_chat", "write"),
        ("agentic_cancel_run", "write"),
        ("agentic_skip_phase", "write"),
        ("agentic_retrain", "write"),
    ])
    def test_categories(self, tool_map, tool_name, category):
        assert category in tool_map[tool_name].tags


class TestStartRunDefaults:
    def test_wrapper_defaults_match_client_signature(self, tool_map):
        """Single source of truth: the tool signature IS the client method
        signature (minus self), so defaults can never drift."""
        from xplainable_client.client.agentic import AgenticClient

        wrapper_sig = inspect.signature(tool_map["agentic_start_run"].fn)
        client_sig = inspect.signature(AgenticClient.start_run)
        client_params = {
            n: p for n, p in client_sig.parameters.items() if n != "self"
        }
        assert list(wrapper_sig.parameters) == list(client_params)
        for name, param in wrapper_sig.parameters.items():
            assert param.default == client_params[name].default, name

    def test_algorithm_defaults_to_xgm(self, tool_map):
        sig = inspect.signature(tool_map["agentic_start_run"].fn)
        assert sig.parameters["algorithm"].default == "xgm"

    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_only_provided_kwargs_forwarded(self, mock_get_client, tool_map, mock_client):
        """The wrapper forwards exactly what the caller supplied; the client
        method applies its own defaults (no default duplication in the MCP
        layer)."""
        mock_get_client.return_value = mock_client
        mock_client.agentic.start_run.return_value = {"run_id": "r1"}

        asyncio.run(tool_map["agentic_start_run"].fn(model_name="My Model"))

        mock_client.agentic.start_run.assert_called_once_with(model_name="My Model")

    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_overrides_forwarded(self, mock_get_client, tool_map, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.agentic.start_run.return_value = {"run_id": "r1"}

        asyncio.run(
            tool_map["agentic_start_run"].fn(
                model_name="M",
                auto_mode=False,
                algorithm="xplainable",
                run_id="seeded-run",
                user_query="predict churn",
            )
        )

        kwargs = mock_client.agentic.start_run.call_args.kwargs
        assert kwargs["auto_mode"] is False
        assert kwargs["algorithm"] == "xplainable"
        assert kwargs["run_id"] == "seeded-run"
        assert kwargs["user_query"] == "predict churn"


class TestLifecycleCalls:
    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_get_run_state(self, mock_get_client, tool_map, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.agentic.get_run_state.return_value = {"status": "running"}

        result = asyncio.run(tool_map["agentic_get_run_state"].fn(run_id="run-1"))

        assert result == {"status": "running"}
        mock_client.agentic.get_run_state.assert_called_once_with(run_id="run-1")

    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_submit_decision_forwards_fields(self, mock_get_client, tool_map, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.agentic.submit_decision.return_value = {"status": "ok"}

        asyncio.run(
            tool_map["agentic_submit_decision"].fn(
                run_id="run-1",
                decision_type="model_deployment",
                action="approve",
            )
        )

        kwargs = mock_client.agentic.submit_decision.call_args.kwargs
        assert kwargs["run_id"] == "run-1"
        assert kwargs["decision_type"] == "model_deployment"
        assert kwargs["action"] == "approve"

    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_send_chat(self, mock_get_client, tool_map, mock_client):
        mock_get_client.return_value = mock_client
        reply = Mock()
        reply.model_dump.return_value = {"content": "hi"}
        mock_client.agentic.send_chat.return_value = reply

        result = asyncio.run(
            tool_map["agentic_send_chat"].fn(run_id="run-1", message="explain the metrics")
        )

        assert result == {"content": "hi"}
        mock_client.agentic.send_chat.assert_called_once_with(
            run_id="run-1", message="explain the metrics"
        )

    @patch("xplainable_mcp.runtime_tools.get_client")
    def test_cancel_skip_phases_retrain(self, mock_get_client, tool_map, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.agentic.cancel_run.return_value = {"success": True}
        mock_client.agentic.skip_phase.return_value = {"skipped_phase": "x"}
        mock_client.agentic.get_phases.return_value = [{"phase": "p"}]
        mock_client.agentic.get_pending_decision.return_value = None
        mock_client.agentic.retrain.return_value = {"status": "queued"}

        assert asyncio.run(tool_map["agentic_cancel_run"].fn(run_id="r")) == {"success": True}
        assert asyncio.run(tool_map["agentic_skip_phase"].fn(run_id="r")) == {"skipped_phase": "x"}
        assert asyncio.run(tool_map["agentic_get_phases"].fn(run_id="r")) == [{"phase": "p"}]
        assert asyncio.run(tool_map["agentic_get_pending_decision"].fn(run_id="r")) is None
        assert asyncio.run(tool_map["agentic_retrain"].fn(run_id="r")) == {"status": "queued"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
