"""
Datasets service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client, XP_ICON


# Datasets Tools
# ============================================


def datasets_list_datasets():
    """
    List all available public datasets.
    
    Returns:
        List of dataset names
        
    Raises:
        XplainableAPIError: If listing fails

    Category: read
    """
    try:
        client = get_client()
        result = client.datasets.list_datasets()
        logger.info(f"Executed datasets.list_datasets")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in datasets_list_datasets: {e}")
        raise
