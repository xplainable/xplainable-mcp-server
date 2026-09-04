"""
Flat tool-surface contract: everything in the client @mcp_tool registry
plus the hand-written server-native tools, with no tag filtering.

Uses the in-memory fastmcp Client so the assertion matches what an MCP
host actually sees at protocol list time.
"""

import asyncio

import pytest
from fastmcp import Client

from xplainable_mcp.runtime_tools import derive_tool_name, iter_registry_entries
from xplainable_mcp.server import mcp

# Hand-written tools registered by the server itself (team session tools
# in server.py, docs tools in docs_tools.py).
SERVER_NATIVE_TOOLS = {
    "list_user_teams",
    "set_active_team",
    "select_team",
    "docs_list_pages",
    "docs_get_page",
    "docs_search",
}


@pytest.fixture(scope="module")
def surface():
    async def go():
        async with Client(mcp) as client:
            return {tool.name for tool in await client.list_tools()}

    return asyncio.run(go())


class TestFlatSurface:
    def test_surface_is_registry_plus_server_native(self, surface):
        expected = {
            derive_tool_name(e) for e in iter_registry_entries()
        } | SERVER_NATIVE_TOOLS
        assert surface == expected

    def test_registry_count(self):
        assert len(list(iter_registry_entries())) == 38

    def test_total_count(self, surface):
        assert len(surface) == 44  # 38 registry + 6 server-native

    def test_training_loop_tools_present(self, surface):
        for name in (
            "datasets_list_team_datasets",
            "datasets_preview_dataset_json",
            "preprocessing_list_available_transformers",
            "preprocessing_create_preprocessor_from_spec",
            "preprocessing_preview_from_data",
            "models_train_model",
            "models_refit_model",
            "models_get_feature_info",
            "gpt_explain_model",
            "deployments_deploy",
            "inference_predict",
            "optimisers_run_optimiser",
            "reports_create_report",
            "reports_get_job_status",
        ):
            assert name in surface, name

    def test_team_recovery_tools_present(self, surface):
        for name in ("select_team", "set_active_team", "list_user_teams"):
            assert name in surface, name

    def test_removed_tools_absent(self, surface):
        for name in (
            # workflow wrappers (WorkflowClient deleted from the client)
            "workflow_list_assets",
            "workflow_train_model",
            "workflow_wait_for_update",
            "workflow_decide",
            "workflow_deploy_model",
            "workflow_predict",
            "workflow_optimise_model",
            "workflow_create_report",
            "workflow_explain_model",
            "workflow_get_run_charts",
            # server introspection tools
            "list_tools",
            "get_workflows",
            # raw-blob persistence must never be exposed
            "models_create_model_v2",
        ):
            assert name not in surface, name
