"""
Tests for env-gated tool-surface tag filtering.

By default the server exposes only the curated surface (tools tagged
"workflow" or "curated"). Setting XPLAINABLE_ADVANCED_TOOLS to a truthy
value disables filtering (include_tags=None → full surface).
"""

import pytest

from xplainable_mcp.mcp_instance import resolve_include_tags

CURATED = {"workflow", "curated"}


class TestResolveIncludeTags:
    def test_unset_env_returns_curated_set(self):
        assert resolve_include_tags(None) == CURATED

    @pytest.mark.parametrize("value", ["true", "TRUE", " 1 ", "yes"])
    def test_truthy_values_return_none_full_surface(self, value):
        assert resolve_include_tags(value) is None

    @pytest.mark.parametrize("value", ["false", "", "0", "garbage"])
    def test_falsy_values_return_curated_set(self, value):
        assert resolve_include_tags(value) == CURATED


class TestMcpInstanceWiring:
    def test_mcp_instance_include_tags_default(self):
        """conftest keeps XPLAINABLE_ADVANCED_TOOLS unset, so the shared
        FastMCP instance must be constructed with the curated tag set."""
        from xplainable_mcp.mcp_instance import mcp

        assert mcp.include_tags == CURATED


@pytest.fixture(scope="module")
def registered_tools():
    import asyncio

    # Importing the server module registers the hand-written tools.
    import xplainable_mcp.server  # noqa: F401
    from xplainable_mcp.mcp_instance import mcp

    return asyncio.run(mcp.get_tools())


class TestTeamToolsCurated:
    """The hand-written team-selection tools must be on the default surface.

    INSTRUCTIONS tell callers to recover from 'No team selected' via
    select_team / set_active_team; if these were untagged they would be
    filtered out under include_tags={"workflow", "curated"} and a
    multi-team user on the hosted OAuth server would have no in-band
    recovery path.
    """

    @pytest.mark.parametrize(
        "tool_name", ["list_user_teams", "set_active_team", "select_team"]
    )
    def test_team_tools_tagged_curated(self, registered_tools, tool_name):
        assert tool_name in registered_tools
        assert {"admin", "curated"} <= set(registered_tools[tool_name].tags)

    @pytest.mark.parametrize("tool_name", ["list_tools", "get_workflows"])
    def test_discovery_tools_stay_untagged(self, registered_tools, tool_name):
        """list_tools / get_workflows are deliberately advanced-only."""
        assert tool_name in registered_tools
        assert not registered_tools[tool_name].tags
