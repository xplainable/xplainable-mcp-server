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


@mcp.tool(icons=[XP_ICON], tags={"read"})
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

@mcp.tool(icons=[XP_ICON], tags={"write"})
def datasets_delete_dataset(dataset_id: str):
    """
    Delete a dataset.
    
    Args:
        dataset_id: ID of the dataset to delete
    
    Returns:
        Success message
    
    Raises:
        XplainableAPIError: If deletion fails

    Category: write
    """
    try:
        client = get_client()
        result = client.datasets.delete_dataset(dataset_id)
        logger.info(f"Executed datasets.delete_dataset")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in datasets_delete_dataset: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"read"})
def datasets_get_dataset_info(dataset_id: str):
    """
    Get information about a specific dataset.
    
    Args:
        dataset_id: ID of the dataset
    
    Returns:
        Dataset information
    
    Raises:
        XplainableAPIError: If retrieval fails

    Category: read
    """
    try:
        client = get_client()
        result = client.datasets.get_dataset_info(dataset_id)
        logger.info(f"Executed datasets.get_dataset_info")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in datasets_get_dataset_info: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
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

@mcp.tool(icons=[XP_ICON], tags={"read"})
def datasets_load_dataset(name: str):
    """
    Load a public dataset by name. Downloads the CSV directly from
    the xplainable public blob storage.
    
    Known datasets: telco_churn, titanic, heart_disease, iris
    
    Args:
        name: Name of the dataset to load
    
    Returns:
        DataFrame containing the dataset
    
    Raises:
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

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def datasets_preview_dataset_json(dataset_id: str, rows: int = 10):
    """
    Preview a dataset as JSON records.
    
    Args:
        dataset_id: ID of the dataset
        rows: Number of rows to preview
    
    Returns:
        List of row dicts (JSON records)

    Category: read
    """
    try:
        client = get_client()
        result = client.datasets.preview_dataset_json(dataset_id, rows)
        logger.info(f"Executed datasets.preview_dataset_json")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in datasets_preview_dataset_json: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def datasets_upload_dataset(file_path: str, name: str, description: Optional[str] = None, team_id: Optional[str] = None):
    """
    Upload a dataset file.
    
    Args:
        file_path: Path to the dataset file
        name: Name for the dataset
        description: Optional description
        team_id: Optional team ID (uses session team_id if not provided)
    
    Returns:
        Upload response with dataset information
    
    Raises:
        FileNotFoundError: If file doesn't exist
        XplainableAPIError: If upload fails

    Category: write
    """
    try:
        client = get_client()
        result = client.datasets.upload_dataset(file_path, name, description, team_id)
        logger.info(f"Executed datasets.upload_dataset")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in datasets_upload_dataset: {e}")
        raise
