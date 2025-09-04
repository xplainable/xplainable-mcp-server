"""
Datasets service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Datasets Tools
# ============================================


@mcp.tool()
def datasets_load_dataset(name: str):
    """
    Load a public dataset by name.
    
    Args:
        name: Name of the dataset to load
        
    Returns:
        DataFrame containing the dataset
        
    Raises:
        ValueError: If dataset doesn't exist
        XplainableAPIError: If loading fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.datasets.load_dataset(name)
        logger.info(f"Executed datasets.load_dataset")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in datasets_load_dataset: {e}")
        raise


@mcp.tool()
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


@mcp.tool()
def datasets_list_team_datasets(team_id: Optional[str] = None):
    """
    List all datasets for a team.
    
    Args:
        team_id: Optional team ID (uses session team_id if not provided)
        
    Returns:
        List of dataset information
        
    Raises:
        XplainableAPIError: If listing fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.datasets.list_team_datasets(team_id)
        logger.info(f"Executed datasets.list_team_datasets")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in datasets_list_team_datasets: {e}")
        raise

