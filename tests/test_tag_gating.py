"""
Tests for the flat tool surface: no tag-based filtering.

The old three-tier surface (direct/guided/advanced via include_tags) is
gone — the shared FastMCP instance must apply no tag filtering at all.
Tags remain purely informational.
"""

import pytest


class TestNoTagFiltering:
    def test_mcp_instance_has_no_include_tags(self):
        """The shared FastMCP instance must not filter tools by tag."""
        from xplainable_mcp.mcp_instance import mcp

        assert mcp.include_tags is None

    def test_resolve_include_tags_removed(self):
        """The tier resolver must be gone from mcp_instance."""
        import xplainable_mcp.mcp_instance as mod

        assert not hasattr(mod, "resolve_include_tags")


@pytest.fixture(scope="module")
def registered_tools():
    import asyncio

    # Importing the server module registers the hand-written tools.
    import xplainable_mcp.server  # noqa: F401
    from xplainable_mcp.mcp_instance import mcp

    return asyncio.run(mcp.get_tools())


class TestTeamTools:
    """The hand-written team-selection tools stay registered and tagged
    "admin" (informational only — nothing filters on tags anymore)."""

    @pytest.mark.parametrize(
        "tool_name", ["list_user_teams", "set_active_team", "select_team"]
    )
    def test_team_tools_registered_and_tagged_admin(
        self, registered_tools, tool_name
    ):
        assert tool_name in registered_tools
        assert "admin" in set(registered_tools[tool_name].tags)
