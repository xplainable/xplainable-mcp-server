"""Local target must expose the full 42-tool surface in-process."""

import pytest

from evals.harness.targets import local_toolset


@pytest.mark.smoke
async def test_local_toolset_exposes_42_tools():
    toolset = local_toolset()
    async with toolset:
        tools = await toolset.list_tools()
    assert len(tools) == 42


def test_local_toolset_requires_api_key(monkeypatch):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "")

    with pytest.raises(RuntimeError, match="XPLAINABLE_API_KEY"):
        local_toolset()
