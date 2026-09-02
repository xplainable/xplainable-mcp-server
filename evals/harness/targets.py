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
    """Hosted server via OAuth (browser consent on first run, token cached).

    Currently broken: pydantic-ai 2.37 passes ``verify=`` to fastmcp
    2.14.7's StreamableHttpTransport, which rejects it. Fail fast with an
    explanation instead of a TypeError deep inside transport setup. Remove
    the guard once the dep pair is upgraded; the OAuth wiring below is the
    intended implementation.
    """
    raise RuntimeError(
        "The hosted target is broken with the current pydantic-ai/fastmcp "
        "pair (pydantic-ai 2.37 passes verify= to fastmcp 2.14.7's "
        "StreamableHttpTransport, which rejects it). Use --target local — "
        "the in-process server hits the same live platform API."
    )
    from fastmcp.client.auth.oauth import OAuth
    from key_value.aio.stores.disk import DiskStore

    auth = OAuth(HOSTED_URL, token_storage=DiskStore(directory="/tmp/xp-mcp-oauth"))
    return MCPToolset(HOSTED_URL, auth=auth)


def get_toolset(target: str) -> MCPToolset:
    return {"local": local_toolset, "hosted": hosted_toolset}[target]()
