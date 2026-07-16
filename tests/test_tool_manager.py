"""Regression tests for ToolFileManager block-boundary handling.

The v1.7.1 sync (commit 48e4f25) silently stripped ``@mcp.tool`` decorators
from 11 tools: when replacing or removing a tool, the end-of-function scan
treated a following top-level ``@mcp.tool`` decorator as part of the current
block and consumed it, leaving the next function undecorated (and therefore
unregistered).
"""

from pathlib import Path

import pytest

from xplainable_mcp.tool_manager import ToolFileManager


TWO_TOOLS = '''\
"""Service module."""

from ..mcp_instance import mcp
from ..server import get_client, XP_ICON


@mcp.tool(icons=[XP_ICON])
def svc_first(x: str):
    """First tool."""
    try:
        client = get_client()
        return client.svc.first(x)
    except Exception as e:
        raise

@mcp.tool(icons=[XP_ICON])
def svc_second(y: str):
    """Second tool."""
    try:
        client = get_client()
        return client.svc.second(y)
    except Exception as e:
        raise
'''

NEW_FIRST = '''\
@mcp.tool(icons=[XP_ICON])
def svc_first(x: str, z: int = 0):
    """First tool, updated."""
    try:
        client = get_client()
        return client.svc.first(x, z)
    except Exception as e:
        raise
'''


@pytest.fixture
def manager(tmp_path):
    return ToolFileManager(tmp_path)


def test_replace_tool_keeps_next_tools_decorator(manager):
    result = manager._replace_tool_in_content(TWO_TOOLS, NEW_FIRST, "svc_first")

    assert "def svc_first(x: str, z: int = 0):" in result
    lines = result.split("\n")
    second_def = lines.index('def svc_second(y: str):')
    assert lines[second_def - 1].strip() == "@mcp.tool(icons=[XP_ICON])", (
        "replacing svc_first must not consume svc_second's @mcp.tool decorator"
    )


def test_remove_tool_keeps_next_tools_decorator(manager):
    result = manager._remove_tool_from_content(TWO_TOOLS, "svc_first")

    assert "def svc_first(" not in result
    lines = result.split("\n")
    second_def = lines.index('def svc_second(y: str):')
    assert lines[second_def - 1].strip() == "@mcp.tool(icons=[XP_ICON])", (
        "removing svc_first must not consume svc_second's @mcp.tool decorator"
    )


def test_extract_tool_stops_before_next_tools_decorator(manager):
    extracted = manager._extract_tool_from_content(TWO_TOOLS, "svc_first")

    assert "def svc_first(" in extracted
    assert "@mcp.tool" not in extracted.split("def svc_first(")[1], (
        "extraction must not run into the next tool's decorator"
    )
