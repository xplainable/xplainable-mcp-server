"""
Tests for env-gated tool-surface tag filtering (three tiers).

- default: direct mode — include_tags={"curated"} (curated tools only)
- XPLAINABLE_GUIDED_TOOLS truthy: {"curated", "guided"} adds the agentic trio
- XPLAINABLE_ADVANCED_TOOLS truthy: None disables filtering (full surface)
"""

import pytest

from xplainable_mcp.mcp_instance import resolve_include_tags

DIRECT = {"curated"}
GUIDED = {"curated", "guided"}


class TestResolveIncludeTags:
    def test_unset_env_returns_direct_set(self):
        assert resolve_include_tags(None, None) == DIRECT

    def test_default_excludes_workflow_tag(self):
        # "workflow" must NOT be in the default tags or the demoted guided
        # trio (still tagged "workflow") would leak back into direct mode.
        assert "workflow" not in resolve_include_tags(None, None)

    @pytest.mark.parametrize("value", ["true", "TRUE", " 1 ", "yes"])
    def test_truthy_advanced_returns_none_full_surface(self, value):
        assert resolve_include_tags(value, None) is None

    @pytest.mark.parametrize("value", ["true", "TRUE", " 1 ", "yes"])
    def test_truthy_guided_adds_guided_tag(self, value):
        assert resolve_include_tags(None, value) == GUIDED

    def test_advanced_wins_over_guided(self):
        assert resolve_include_tags("1", "1") is None

    @pytest.mark.parametrize("value", ["false", "", "0", "garbage"])
    def test_falsy_values_stay_direct(self, value):
        assert resolve_include_tags(value, value) == DIRECT


class TestMcpInstanceWiring:
    def test_mcp_instance_include_tags_default(self):
        """conftest keeps both surface env vars unset, so the shared
        FastMCP instance must be constructed with the direct tag set."""
        from xplainable_mcp.mcp_instance import mcp

        assert mcp.include_tags == DIRECT


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
    filtered out under include_tags={"curated"} and a multi-team user on
    the hosted OAuth server would have no in-band recovery path.
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
