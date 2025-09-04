"""
Misc service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Misc Tools
# ============================================


@mcp.tool()
def misc_load_classifier(model_id: str, version_id: str, model=None):
    """
    Load a binary classification model.
    
    Args:
        model_id: Model ID
        version_id: Version ID
        model: Existing model to add partitions to
        
    Returns:
        Loaded xplainable classifier
        
    Raises:
        ValueError: If model is not a classification model
        XplainableAPIError: If loading fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.misc.load_classifier(model_id, version_id, model)
        logger.info(f"Executed misc.load_classifier")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in misc_load_classifier: {e}")
        raise


@mcp.tool()
def misc_ping_gateway(hostname: Optional[str] = None):
    """
    Ping the API gateway to check connectivity.
    
    Args:
        hostname: Optional hostname to ping (uses session hostname if not provided)
        
    Returns:
        Ping response with success status
        
    Raises:
        XplainableAPIError: If ping fails
    
    Category: admin
    """
    try:
        client = get_client()
        result = client.misc.ping_gateway(hostname)
        logger.info(f"Executed misc.ping_gateway")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in misc_ping_gateway: {e}")
        raise


@mcp.tool()
def misc_health_check(check_database: bool = True, check_storage: bool = True, check_compute: bool = True):
    """
    Perform a comprehensive health check.
    
    Args:
        check_database: Whether to check database connectivity
        check_storage: Whether to check storage systems
        check_compute: Whether to check compute resources
        
    Returns:
        Health check results
        
    Raises:
        XplainableAPIError: If health check fails
    
    Category: admin
    """
    try:
        client = get_client()
        result = client.misc.health_check(check_database, check_storage, check_compute)
        logger.info(f"Executed misc.health_check")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in misc_health_check: {e}")
        raise


@mcp.tool()
def misc_get_model_info(model_id: str, version_id: str):
    """
    Get information about a model without loading it.
    
    Args:
        model_id: Model ID
        version_id: Version ID
        
    Returns:
        Model information
        
    Raises:
        XplainableAPIError: If retrieval fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.misc.get_model_info(model_id, version_id)
        logger.info(f"Executed misc.get_model_info")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in misc_get_model_info: {e}")
        raise


@mcp.tool()
def misc_ping_server(hostname: Optional[str] = None):
    """
    Ping the compute server to check connectivity.
    
    Args:
        hostname: Optional hostname to ping (uses session hostname if not provided)
        
    Returns:
        Ping response with success status
        
    Raises:
        XplainableAPIError: If ping fails
    
    Category: admin
    """
    try:
        client = get_client()
        result = client.misc.ping_server(hostname)
        logger.info(f"Executed misc.ping_server")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in misc_ping_server: {e}")
        raise


@mcp.tool()
def misc_get_version_info():
    """
    Get comprehensive version information.
    
    Returns:
        Version information for all components
    
    Category: read
    """
    try:
        client = get_client()
        result = client.misc.get_version_info()
        logger.info(f"Executed misc.get_version_info")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in misc_get_version_info: {e}")
        raise


@mcp.tool()
def misc_load_regressor(model_id: str, version_id: str, model=None):
    """
    Load a regression model.
    
    Args:
        model_id: Model ID
        version_id: Version ID
        model: Existing model to add partitions to
        
    Returns:
        Loaded xplainable regressor
        
    Raises:
        ValueError: If model is not a regression model
        XplainableAPIError: If loading fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.misc.load_regressor(model_id, version_id, model)
        logger.info(f"Executed misc.load_regressor")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in misc_load_regressor: {e}")
        raise

