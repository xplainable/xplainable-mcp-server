"""
Collections service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Collections Tools
# ============================================


@mcp.tool()
def collections_get_model_collections(model_id: str):
    """
    Get all collections for a specific model.
    
    Args:
        model_id: ID of the model
        
    Returns:
        List of collection information
        
    Raises:
        XplainableAPIError: If retrieval fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.collections.get_model_collections(model_id)
        logger.info(f"Executed collections.get_model_collections")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in collections_get_model_collections: {e}")
        raise


@mcp.tool()
def collections_update_collection_name(model_id: str, collection_id: str, name: str):
    """
    Update the name of a collection.
    
    Args:
        model_id: ID of the model
        collection_id: ID of the collection
        name: New name for the collection
        
    Returns:
        Success message
        
    Raises:
        XplainableAPIError: If update fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.collections.update_collection_name(model_id, collection_id, name)
        logger.info(f"Executed collections.update_collection_name")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in collections_update_collection_name: {e}")
        raise


@mcp.tool()
def collections_create_collection(model_id: str, name: str, description: str):
    """
    Create a new collection for a model.
    
    Args:
        model_id: ID of the model
        name: Name of the collection
        description: Description of the collection
        
    Returns:
        The collection ID
        
    Raises:
        XplainableAPIError: If collection creation fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.collections.create_collection(model_id, name, description)
        logger.info(f"Executed collections.create_collection")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in collections_create_collection: {e}")
        raise


@mcp.tool()
def collections_create_scenarios(collection_id: str, scenarios: list[dict]):
    """
    Create scenarios for a collection.
    
    Args:
        collection_id: ID of the collection
        scenarios: List of scenario data
        
    Returns:
        List of created scenarios
        
    Raises:
        XplainableAPIError: If creation fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.collections.create_scenarios(collection_id, scenarios)
        logger.info(f"Executed collections.create_scenarios")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in collections_create_scenarios: {e}")
        raise


@mcp.tool()
def collections_get_team_collections():
    """
    Get all collections for the team.
    
    Returns:
        List of collection information
        
    Raises:
        XplainableAPIError: If retrieval fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.collections.get_team_collections()
        logger.info(f"Executed collections.get_team_collections")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in collections_get_team_collections: {e}")
        raise


@mcp.tool()
def collections_delete_collection(model_id: str, collection_id: str):
    """
    Delete a collection.
    
    Args:
        model_id: ID of the model
        collection_id: ID of the collection to delete
        
    Returns:
        Success message
        
    Raises:
        XplainableAPIError: If deletion fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.collections.delete_collection(model_id, collection_id)
        logger.info(f"Executed collections.delete_collection")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in collections_delete_collection: {e}")
        raise


@mcp.tool()
def collections_get_collection_scenarios(collection_id: str):
    """
    Get all scenarios for a collection.
    
    Args:
        collection_id: ID of the collection
        
    Returns:
        List of scenarios
        
    Raises:
        XplainableAPIError: If retrieval fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.collections.get_collection_scenarios(collection_id)
        logger.info(f"Executed collections.get_collection_scenarios")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in collections_get_collection_scenarios: {e}")
        raise


@mcp.tool()
def collections_update_collection_description(model_id: str, collection_id: str, description: str):
    """
    Update the description of a collection.
    
    Args:
        model_id: ID of the model
        collection_id: ID of the collection
        description: New description for the collection
        
    Returns:
        Success message
        
    Raises:
        XplainableAPIError: If update fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.collections.update_collection_description(model_id, collection_id, description)
        logger.info(f"Executed collections.update_collection_description")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in collections_update_collection_description: {e}")
        raise

