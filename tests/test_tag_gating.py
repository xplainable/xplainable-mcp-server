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
