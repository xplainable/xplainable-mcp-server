"""
Tool-surface invariants across the three tiers (direct / guided / advanced).

Uses the in-memory fastmcp Client because include_tags filtering is applied
at protocol list time, not by mcp.get_tools().
"""

import asyncio

import pytest
from fastmcp import Client

from xplainable_mcp.mcp_instance import resolve_include_tags
from xplainable_mcp.runtime_tools import CURATED_PROMOTIONS, GUIDED_TOOLS
from xplainable_mcp.server import mcp


def _surface(include_tags):
    async def go():
        saved = mcp.include_tags
        mcp.include_tags = include_tags
        try:
            async with Client(mcp) as client:
                return {tool.name for tool in await client.list_tools()}
        finally:
            mcp.include_tags = saved

    return asyncio.run(go())


@pytest.fixture(scope="module")
def direct():
    return _surface(resolve_include_tags(None, None))


@pytest.fixture(scope="module")
def guided():
    return _surface(resolve_include_tags(None, "1"))


@pytest.fixture(scope="module")
def advanced():
    return _surface(resolve_include_tags("1", None))


class TestDirectSurface:
    def test_training_loop_tools_present(self, direct):
        for name in (
            "workflow_list_assets",
            "datasets_preview_dataset_json",
            "models_train_model",
            "models_refit_model",
            "models_get_feature_info",
            "workflow_deploy_model",
            "workflow_predict",
            "workflow_create_report",
            "reports_get_job_status",
        ):
            assert name in direct, name

    def test_preprocessing_promotions_present(self, direct):
        assert CURATED_PROMOTIONS <= direct

    def test_team_recovery_tools_present(self, direct):
        for name in ("select_team", "set_active_team", "list_user_teams"):
            assert name in direct, name

    def test_guided_trio_excluded(self, direct):
        assert GUIDED_TOOLS.isdisjoint(direct)

    def test_direct_count(self, direct):
        assert len(direct) == 33


class TestGuidedSurface:
    def test_guided_adds_exactly_the_trio(self, direct, guided):
        assert guided - direct == set(GUIDED_TOOLS)


class TestAdvancedSurface:
    def test_advanced_is_strict_superset(self, direct, guided, advanced):
        assert direct < guided < advanced

    def test_advanced_exposes_full_registry(self, advanced):
        assert len(advanced) >= 105
        # advanced-only examples
        for name in ("agentic_start_run", "list_tools", "get_workflows"):
            assert name in advanced, name
