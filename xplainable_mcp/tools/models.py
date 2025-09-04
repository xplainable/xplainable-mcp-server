"""
Models service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Models Tools
# ============================================


@mcp.tool()
def models_link_preprocessor(model_version_id: str, preprocessor_version_id: str):
    """
    Link a model version to a preprocessor version.
    
    Args:
        model_version_id: The model version ID
        preprocessor_version_id: The preprocessor version ID
        
    Raises:
        XplainableAPIError: If linking fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.models.link_preprocessor(model_version_id, preprocessor_version_id)
        logger.info(f"Executed models.link_preprocessor")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_link_preprocessor: {e}")
        raise


@mcp.tool()
def models_list_model_versions(model_id: str):
    """
    List all versions of a model.
    
    Args:
        model_id: ID of the model
        
    Returns:
        List of model versions
        
    Raises:
        XplainableAPIError: If listing fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.models.list_model_versions(model_id)
        logger.info(f"Executed models.list_model_versions")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_list_model_versions: {e}")
        raise


@mcp.tool()
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


@mcp.tool()
def models_list_model_version_partitions(version_id: str):
    """
    List all partitions for a model version.
    
    Args:
        version_id: ID of the model version (or "latest")
        
    Returns:
        Dictionary containing partition information
        
    Raises:
        XplainableAPIError: If listing fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.models.list_model_version_partitions(version_id)
        logger.info(f"Executed models.list_model_version_partitions")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_list_model_version_partitions: {e}")
        raise


@mcp.tool()
def models_list_team_models():
    """
    List all models for the current team (based on API key).
    
    This method returns comprehensive information about all models
    accessible to the authenticated user's team.
    
    Returns:
        List of model information including names, descriptions, and metadata
        
    Raises:
        XplainableAPIError: If listing fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.models.list_team_models()
        logger.info(f"Executed models.list_team_models")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_list_team_models: {e}")
        raise

