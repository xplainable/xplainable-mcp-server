"""Local target must expose the full 44-tool surface in-process."""

import pytest

from evals.harness.targets import local_toolset


@pytest.mark.smoke
async def test_local_toolset_exposes_44_tools():
    toolset = local_toolset()
    async with toolset:
        tools = await toolset.list_tools()
    assert len(tools) == 44


def test_local_toolset_requires_api_key(monkeypatch):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "")

    with pytest.raises(RuntimeError, match="XPLAINABLE_API_KEY"):
        local_toolset()


def test_hosted_toolset_fails_fast_with_incompatibility_message():
    # pydantic-ai 2.37 passes verify= to fastmcp 2.14.7's
    # StreamableHttpTransport, which rejects it. Until the dep pair is
    # upgraded, fail at selection time with an explanation instead of a
    # TypeError deep inside transport setup.
    from evals.harness.targets import get_toolset

    with pytest.raises(RuntimeError, match="hosted target.*--target local"):
        get_toolset("hosted")
