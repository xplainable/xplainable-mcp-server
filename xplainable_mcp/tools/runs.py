"""
Runs service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client, XP_ICON


# Runs Tools
# ============================================

@mcp.tool(icons=[XP_ICON], tags={"write"})
def runs_create_run(team_id: str, user_id: str, run_id: Optional[str] = None, model_id: Optional[str] = None, name: Optional[str] = None, metadata: Optional[Dict] = None):
    """
    Create a new training run.
    
    Args:
        team_id: Team ID for the run
        user_id: User ID who owns the run
        run_id: Optional run ID (will be generated if not provided)
        model_id: Optional associated model ID
        name: Optional run name
        metadata: Optional metadata dictionary
    
    Returns:
        The run ID (either provided or newly generated)
    
    Raises:
        XplainableAPIError: If run creation fails

    Category: write
    """
    try:
        client = get_client()
        result = client.runs.create_run(team_id, user_id, run_id, model_id, name, metadata)
        logger.info(f"Executed runs.create_run")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in runs_create_run: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def runs_get_run(run_id: str):
    """
    Get run details by ID.
    
    Args:
        run_id: The run ID
    
    Returns:
        Run details dictionary
    
    Raises:
        XplainableAPIError: If run retrieval fails

    Category: read
    """
    try:
        client = get_client()
        result = client.runs.get_run(run_id)
        logger.info(f"Executed runs.get_run")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in runs_get_run: {e}")
        raise
