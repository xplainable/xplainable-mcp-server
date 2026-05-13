"""
Models service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client, XP_ICON


# Models Tools
# ============================================


def models_get_model(model_id: str):
    """
    Get detailed information about a model.
    
    Args:
        model_id: ID of the model
        
    Returns:
        Model information
        
    Raises:
        XplainableAPIError: If retrieval fails

    Category: read
    """
    try:
        client = get_client()
        result = client.models.get_model(model_id)
        logger.info(f"Executed models.get_model")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_get_model: {e}")
        raise
