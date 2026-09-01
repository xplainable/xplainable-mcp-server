#!/usr/bin/env python
"""Drive the hosted MCP (mcp.xplainable.io) tool-by-tool for E2E testing.

Usage: hosted_e2e.py <tool_name> ['<json-args>']
       hosted_e2e.py --list
First run opens a browser for the Auth0 OAuth consent; the token is cached
by fastmcp under ~/.fastmcp.
"""
import asyncio
import json
import sys

from fastmcp import Client
from fastmcp.client.auth.oauth import OAuth
from key_value.aio.stores.disk import DiskStore

URL = "https://mcp.xplainable.io/mcp"
AUTH = OAuth(URL, token_storage=DiskStore(directory="/tmp/xp-mcp-oauth"))


async def main() -> None:
    async with Client(URL, auth=AUTH) as c:
        if sys.argv[1] == "--list":
            tools = await c.list_tools()
            print(f"total: {len(tools)}")
            for t in sorted(tools, key=lambda t: t.name):
                print(" ", t.name)
            return
        args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = await c.call_tool(sys.argv[1], args, raise_on_error=False)
        if result.is_error:
            print("TOOL ERROR:")
        if result.structured_content is not None:
            print(json.dumps(result.structured_content, indent=1, default=str))
        else:
            for block in result.content:
                text = getattr(block, "text", None)
                print(text if text is not None else block)


asyncio.run(main())
