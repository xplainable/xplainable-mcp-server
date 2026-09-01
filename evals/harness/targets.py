"""Eval targets: where the agent's MCP toolset points."""

import os

from pydantic_ai.mcp import MCPToolset

HOSTED_URL = "https://mcp.xplainable.io/mcp"


def local_toolset() -> MCPToolset:
    """In-process server. Env (XPLAINABLE_API_KEY etc.) must be set first —
    xplainable_mcp.server exits at import time without it."""
    if not os.environ.get("XPLAINABLE_API_KEY"):
        raise RuntimeError("Set XPLAINABLE_API_KEY before using the local target")
    from xplainable_mcp.server import mcp  # deferred: import-time config check

    return MCPToolset(mcp)


def hosted_toolset() -> MCPToolset:
    """Hosted server via OAuth (browser consent on first run, token cached)."""
    from fastmcp.client.auth.oauth import OAuth
    from key_value.aio.stores.disk import DiskStore

    auth = OAuth(HOSTED_URL, token_storage=DiskStore(directory="/tmp/xp-mcp-oauth"))
    return MCPToolset(HOSTED_URL, auth=auth)


def get_toolset(target: str) -> MCPToolset:
    return {"local": local_toolset, "hosted": hosted_toolset}[target]()
