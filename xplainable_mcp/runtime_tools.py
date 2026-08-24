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
from mcp.types import Icon

from .client_manager import get_client

logger = logging.getLogger(__name__)

XP_ICON = Icon(
    src="https://xplainable.io/assets/xplainable-icon.png", mimeType="image/png"
)

# Server-side tag overlays
# ------------------------
# The agentic trio delegates orchestration to the server-side pipeline
# (guided mode). It is opt-in via XPLAINABLE_GUIDED_TOOLS, not curated.
GUIDED_TOOLS = frozenset(
    {
        "workflow_train_model",
        "workflow_wait_for_update",
        "workflow_decide",
    }
)

# Preprocessing tools promoted into the curated (direct-mode) surface so
# Claude can author, preview, and apply preprocessing before training.
CURATED_PROMOTIONS = frozenset(
    {
        "preprocessing_list_available_transformers",
        "preprocessing_create_preprocessor_from_spec",
        "preprocessing_preview_from_data",
    }
)


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


def compute_tags(tool_name: str, entry: Dict[str, Any]) -> Set[str]:
    """Category tag plus server-side curated/guided overlays."""
    if tool_name in GUIDED_TOOLS:
        return {entry["category"].value, "guided"}
    tags = {entry["category"].value}
    if entry["curated"] or tool_name in CURATED_PROMOTIONS:
        tags.add("curated")
    return tags


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
        result = await anyio.to_thread.run_sync(
            functools.partial(method, **kwargs)
        )
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
            tags=compute_tags(tool_name, entry),
            icons=[XP_ICON],
        )
    logger.info(
        "Registered %d runtime tools from xplainable-client registry", len(entries)
    )
    return len(entries)
