"""
Preprocessing service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client, XP_ICON


# Preprocessing Tools
# ============================================


@mcp.tool(icons=[XP_ICON])
def preprocessing_get_preprocessor(preprocessor_id: str):
    """
    Get detailed information about a preprocessor.
    
    Args:
        preprocessor_id: ID of the preprocessor
    
    Returns:
        Preprocessor information

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

@mcp.tool(icons=[XP_ICON])
def preprocessing_add_version_from_spec(preprocessor_id: str, spec: dict, sample_data: Optional[List[Dict]] = None, parent_version_id: Optional[str] = None):
    """
    Add a new version to an existing preprocessor.
    
    Args:
        preprocessor_id: ID of the existing preprocessor
        spec: PipelineSpec dict
        sample_data: Optional sample data as a list of row dicts (JSON records)
        parent_version_id: Optional parent version for lineage tracking
    
    Returns:
        Dict with version_id

    Category: write
    """
    try:
        client = get_client()
        result = client.preprocessing.add_version_from_spec(preprocessor_id, spec, sample_data, parent_version_id)
        logger.info(f"Executed preprocessing.add_version_from_spec")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_add_version_from_spec: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_check_signature(version_id: str, columns: List[str]):
    """
    Check if a preprocessor version's output schema matches expected columns.
    
    Args:
        version_id: The version ID to check
        columns: Expected output column names
    
    Returns:
        Signature check result dict

    Category: read
    """
    try:
        client = get_client()
        result = client.preprocessing.check_signature(version_id, columns)
        logger.info(f"Executed preprocessing.check_signature")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_check_signature: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_create_preprocessor_from_spec(name: str, description: str, spec: dict, sample_data: Optional[List[Dict]] = None):
    """
    Create a new preprocessor from a PipelineSpec dict.
    
    The spec should follow the PipelineSpec format:
    {"version": "2.0", "steps": [{"id": "...", "type": "...", "columns": [...], "params": {...}}]}
    
    Use preprocessing_list_available_transformers to see available transformer types and their parameters.
    
    Args:
        name: Name of the preprocessor
        description: Description of the preprocessor
        spec: PipelineSpec dict
        sample_data: Optional sample data as a list of row dicts (JSON records)
    
    Returns:
        Dict with preprocessor_id and version_id

    Category: write
    """
    try:
        client = get_client()
        result = client.preprocessing.create_preprocessor_from_spec(name, description, spec, sample_data)
        logger.info(f"Executed preprocessing.create_preprocessor_from_spec")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_create_preprocessor_from_spec: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_delete_preprocessor(preprocessor_id: str):
    """
    Delete a preprocessor and all its versions.
    
    Args:
        preprocessor_id: The preprocessor ID to delete
    
    Returns:
        Deletion result dict

    Category: write
    """
    try:
        client = get_client()
        result = client.preprocessing.delete_preprocessor(preprocessor_id)
        logger.info(f"Executed preprocessing.delete_preprocessor")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_delete_preprocessor: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_delete_version(version_id: str):
    """
    Delete a preprocessor version.
    
    Args:
        version_id: The version ID to delete
    
    Returns:
        Deletion result dict

    Category: write
    """
    try:
        client = get_client()
        result = client.preprocessing.delete_version(version_id)
        logger.info(f"Executed preprocessing.delete_version")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_delete_version: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_fit_version_from_data(version_id: str, sample_data: List[Dict]):
    """
    Fit a preprocessor version with sample data.
    
    Args:
        version_id: The version ID to fit
        sample_data: Sample data as a list of row dicts (JSON records)
    
    Returns:
        Fit result dict with schemas and status

    Category: write
    """
    try:
        client = get_client()
        result = client.preprocessing.fit_version_from_data(version_id, sample_data)
        logger.info(f"Executed preprocessing.fit_version_from_data")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_fit_version_from_data: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_get_version(version_id: str):
    """
    Get metadata for a preprocessor version.
    
    Args:
        version_id: The version ID
    
    Returns:
        Version info dict with spec, schemas, etc.

    Category: read
    """
    try:
        client = get_client()
        result = client.preprocessing.get_version(version_id)
        logger.info(f"Executed preprocessing.get_version")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_get_version: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_list_available_transformers():
    """
    List all available preprocessing transformers with their parameters.
    
    Returns a catalog of transformer types that can be used in PipelineSpec steps,
    including their constructor parameters and descriptions.
    
    Returns:
        Formatted string describing all available transformers

    Category: read
    """
    try:
        client = get_client()
        result = client.preprocessing.list_available_transformers()
        logger.info(f"Executed preprocessing.list_available_transformers")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_list_available_transformers: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_list_preprocessors(team_id: Optional[str] = None):
    """
    List all preprocessors for a team.
    
    Args:
        team_id: Optional team ID (uses session team_id if not provided)
    
    Returns:
        List of preprocessor information

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

@mcp.tool(icons=[XP_ICON])
def preprocessing_preview_from_data(version_id: str, sample_data: List[Dict]):
    """
    Preview pipeline transformation on sample data.
    
    Args:
        version_id: The version ID to preview
        sample_data: Sample data as a list of row dicts (JSON records)
    
    Returns:
        Preview dict with deltas, schemas, and samples

    Category: read
    """
    try:
        client = get_client()
        result = client.preprocessing.preview_from_data(version_id, sample_data)
        logger.info(f"Executed preprocessing.preview_from_data")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_preview_from_data: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def preprocessing_update_version_from_spec(version_id: str, spec: dict, sample_data: Optional[List[Dict]] = None):
    """
    Update an existing preprocessor version with a new spec.
    
    Args:
        version_id: ID of the version to update
        spec: Updated PipelineSpec dict
        sample_data: Optional sample data as a list of row dicts (JSON records)
    
    Returns:
        Dict with version_id

    Category: write
    """
    try:
        client = get_client()
        result = client.preprocessing.update_version_from_spec(version_id, spec, sample_data)
        logger.info(f"Executed preprocessing.update_version_from_spec")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in preprocessing_update_version_from_spec: {e}")
        raise
