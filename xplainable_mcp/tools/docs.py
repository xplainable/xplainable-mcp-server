"""Documentation tools — let LLMs search and read xplainable docs."""

import json
import logging
from typing import Optional, List, Dict, Any

import httpx

from ..mcp_instance import mcp
from ..server import XP_ICON

logger = logging.getLogger(__name__)

DOCS_INDEX_URL = "https://docs.xplainable.io/docs-index.json"

# Cache the index in memory after first fetch
_docs_cache: Optional[List[Dict[str, Any]]] = None


async def _get_docs_index() -> List[Dict[str, Any]]:
    """Fetch and cache the docs index.

    Returns:
        The parsed docs index as a list of page objects.

    Raises:
        httpx.HTTPStatusError: If the request fails.
    """
    global _docs_cache
    if _docs_cache is not None:
        return _docs_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(DOCS_INDEX_URL, timeout=10)
        resp.raise_for_status()
        _docs_cache = resp.json()
    return _docs_cache


# Docs Tools
# ============================================


@mcp.tool(icons=[XP_ICON])
async def docs_list_pages() -> List[Dict[str, Any]]:
    """
    List all available xplainable documentation pages.

    Returns a summary of every page in the docs site including its id,
    title, category, and description. Full page content is NOT included —
    use docs_get_page to retrieve that.

    Returns:
        List of page summaries with id, title, category, and description.

    Category: read
    """
    try:
        pages = await _get_docs_index()
        summaries = []
        for page in pages:
            summaries.append({
                "id": page.get("id", ""),
                "title": page.get("title", ""),
                "category": page.get("category", ""),
                "description": page.get("description", ""),
            })
        logger.info(f"Listed {len(summaries)} documentation pages")
        return summaries
    except Exception as e:
        logger.error(f"Error in docs_list_pages: {e}")
        return [{"error": f"Failed to fetch docs index: {str(e)}"}]


@mcp.tool(icons=[XP_ICON])
async def docs_get_page(page_id: str) -> Dict[str, Any]:
    """
    Get the full content of a specific documentation page.

    Args:
        page_id: The page identifier, e.g. "getting-started/installation".
                 Use docs_list_pages to discover available page IDs.

    Returns:
        The full page including title, category, description, and content
        rendered as markdown.

    Category: read
    """
    try:
        pages = await _get_docs_index()
        for page in pages:
            if page.get("id") == page_id:
                return {
                    "id": page.get("id", ""),
                    "title": page.get("title", ""),
                    "category": page.get("category", ""),
                    "description": page.get("description", ""),
                    "content": page.get("content", ""),
                }
        return {"error": f"Page not found: {page_id}"}
    except Exception as e:
        logger.error(f"Error in docs_get_page: {e}")
        return {"error": f"Failed to fetch docs index: {str(e)}"}


@mcp.tool(icons=[XP_ICON])
async def docs_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search the xplainable documentation by keyword.

    Performs a case-insensitive keyword search across page titles,
    descriptions, headings, and body content. Returns the top matching
    pages with a snippet showing the match context.

    Args:
        query: The search term to look for.
        limit: Maximum number of results to return (default 5).

    Returns:
        List of matching pages with title, category, id, and a text
        snippet around the first match.

    Category: read
    """
    try:
        pages = await _get_docs_index()
        query_lower = query.lower()
        results: List[Dict[str, Any]] = []

        for page in pages:
            title = page.get("title", "")
            description = page.get("description", "")
            content = page.get("content", "")
            headings = " ".join(page.get("headings", []))

            # Build a single searchable blob
            searchable = f"{title} {description} {headings} {content}"

            pos = searchable.lower().find(query_lower)
            if pos == -1:
                continue

            # Extract a snippet around the match
            snippet_start = max(0, pos - 80)
            snippet_end = min(len(searchable), pos + len(query) + 80)
            snippet = searchable[snippet_start:snippet_end].strip()
            if snippet_start > 0:
                snippet = "..." + snippet
            if snippet_end < len(searchable):
                snippet = snippet + "..."

            results.append({
                "id": page.get("id", ""),
                "title": title,
                "category": page.get("category", ""),
                "snippet": snippet,
            })

            if len(results) >= limit:
                break

        logger.info(f"docs_search for '{query}' returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Error in docs_search: {e}")
        return [{"error": f"Failed to search docs: {str(e)}"}]
