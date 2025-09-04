"""
Preprocessing service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Preprocessing Tools
# ============================================


@mcp.tool()
def preprocessing_list_preprocessors(team_id: Optional[str] = None):
    """
    List all preprocessors for a team.
    
    Args:
        team_id: Optional team ID (uses session team_id if not provided)
        
    Returns:
        List of preprocessor information
        
    Raises:
        XplainableAPIError: If listing fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.preprocessing.list_preprocessors(team_id)
        logger.info(f"Executed preprocessing.list_preprocessors")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_list_preprocessors: {e}")
        raise


@mcp.tool()
def preprocessing_get_preprocessor(preprocessor_id: str):
    """
    Get detailed information about a preprocessor.
    
    Args:
        preprocessor_id: ID of the preprocessor
        
    Returns:
        Preprocessor information
        
    Raises:
        XplainableAPIError: If retrieval fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.preprocessing.get_preprocessor(preprocessor_id)
        logger.info(f"Executed preprocessing.get_preprocessor")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_get_preprocessor: {e}")
        raise

