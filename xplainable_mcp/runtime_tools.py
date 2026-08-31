"""Runtime MCP tool generation from the xplainable-client @mcp_tool registry.

Replaces the old checked-in codegen (scripts/sync_workflow.py + tools/*.py).
The installed client is the single source of truth: every method decorated
with @mcp_tool is registered as a FastMCP tool at server startup, so a client
upgrade is automatically reflected in the tool surface (no sync PR).
"""

import functools
import logging
from typing import Any, Dict, List, Set

import anyio.to_thread
from fastmcp.exceptions import ToolError
from mcp.types import Icon, ToolAnnotations
from xplainable_client.client.base import XplainableAPIError

from .branding import XPLAINABLE_ICON_URL
from .client_manager import get_client

logger = logging.getLogger(__name__)

XP_ICON = Icon(src=XPLAINABLE_ICON_URL, mimeType="image/svg+xml")


def iter_registry_entries() -> List[Dict[str, Any]]:
    """Return @mcp_tool registry entries from the installed client."""
    # Importing the aggregate client module imports every sub-client module,
    # which populates the global registry as a side effect.
    import xplainable_client.client.client  # noqa: F401
    from xplainable_client.client.utils.mcp_markers import get_mcp_registry

    return list(get_mcp_registry().values())


def _module_attr(entry: Dict[str, Any]) -> str:
    """ModelsClient.get_model -> 'models' (attribute name on XplainableClient)."""
    class_name = entry["qualname"].split(".")[0]
    return class_name.replace("Client", "").lower()


def derive_tool_name(entry: Dict[str, Any]) -> str:
    """ModelsClient.get_model -> models_get_model."""
    return f"{_module_attr(entry)}_{entry['name']}"


def compute_tags(entry: Dict[str, Any]) -> Set[str]:
    """Informational tag: just the registry category (read/write)."""
    return {entry["category"].value}


def compute_annotations(entry: Dict[str, Any]) -> ToolAnnotations:
    """MCP tool annotations derived from the registry category."""
    category = entry["category"].value
    if category == "read":
        return ToolAnnotations(readOnlyHint=True)
    if category == "write":
        return ToolAnnotations(destructiveHint=True)
    raise ValueError(f"Unknown registry category: {category!r}")


def _dump(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, list) and result and hasattr(result[0], "model_dump"):
        return [item.model_dump() for item in result]
    return result


def _build_wrapper(entry: Dict[str, Any], tool_name: str, module_attr: str):
    method_name = entry["name"]

    async def wrapper(**kwargs):
        client = get_client()
        method = getattr(getattr(client, module_attr), method_name)
        # Offload the blocking client call to a worker thread. Sync tools run
        # directly on the event loop, so a long call (e.g. train, ~70s) starves
        # the SSE keepalive pings and the LB drops the connection at ~60s idle.
        try:
            result = await anyio.to_thread.run_sync(
                functools.partial(method, **kwargs)
            )
        except XplainableAPIError as e:
            # Surface the platform's structured error contract to the agent.
            # getattr-safe: older installed clients lack .code/.error/.suggestion.
            code = getattr(e, "code", None)
            if code:
                error = getattr(e, "error", None)
                # Prefer the raw platform message: str(e) already has the
                # client's " Suggestion: ..." appended, which would double up.
                msg = (error or {}).get("message") or str(e)
                suggestion = getattr(e, "suggestion", None)
                formatted = f"[{code}] {msg}"
                if suggestion:
                    formatted = f"{formatted} — Suggestion: {suggestion}"
            else:
                formatted = str(e)
            raise ToolError(formatted) from e
        logger.info("Executed %s.%s", module_attr, method_name)
        return _dump(result)

    params = [
        p
        for name, p in entry["signature"].parameters.items()
        if name not in ("self", "cls")
    ]
    wrapper.__signature__ = entry["signature"].replace(parameters=params)
    wrapper.__name__ = tool_name
    wrapper.__doc__ = entry["docstring"]
    fn = entry["function"]
    wrapper.__annotations__ = {
        k: v for k, v in getattr(fn, "__annotations__", {}).items() if k != "return"
    }
    return wrapper


def register_client_tools(mcp) -> int:
    """Register every client @mcp_tool method as a FastMCP tool. Returns count."""
    entries = iter_registry_entries()
    seen: Set[str] = set()
    for entry in entries:
        tool_name = derive_tool_name(entry)
        if tool_name in seen:
            raise RuntimeError(f"Duplicate runtime tool name: {tool_name}")
        seen.add(tool_name)
        wrapper = _build_wrapper(entry, tool_name, _module_attr(entry))
        mcp.tool(
            wrapper,
            name=tool_name,
            tags=compute_tags(entry),
            annotations=compute_annotations(entry),
            icons=[XP_ICON],
        )
    logger.info(
        "Registered %d runtime tools from xplainable-client registry", len(entries)
    )
    return len(entries)
