"""
Deployments service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Deployments Tools
# ============================================


@mcp.tool()
def deployments_get_deployment_payload(deployment_id: str):
    """
    Get sample payload data for a deployment.
    
    Args:
        deployment_id: ID of the deployment
        
    Returns:
        List containing sample data dictionary for inference
        
    Raises:
        XplainableAPIError: If payload generation fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.deployments.get_deployment_payload(deployment_id)
        logger.info(f"Executed deployments.get_deployment_payload")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in deployments_get_deployment_payload: {e}")
        raise


@mcp.tool()
def deployments_list_deployments(team_id: Optional[str] = None):
    """
    List all deployments for a team.
    
    Args:
        team_id: Optional team ID (uses session team_id if not provided)
        
    Returns:
        List of deployment information
        
    Raises:
        XplainableAPIError: If listing fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.deployments.list_deployments(team_id)
        logger.info(f"Executed deployments.list_deployments")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in deployments_list_deployments: {e}")
        raise


@mcp.tool()
def deployments_activate_deployment(deployment_id: str):
    """
    Activate a deployment.
    
    Args:
        deployment_id: ID of the deployment to activate
        
    Returns:
        Success message
        
    Raises:
        XplainableAPIError: If activation fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.deployments.activate_deployment(deployment_id)
        logger.info(f"Executed deployments.activate_deployment")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in deployments_activate_deployment: {e}")
        raise


@mcp.tool()
def deployments_deploy(model_version_id: str):
    """
    Deploy a model version.
    
    Args:
        model_version_id: ID of the model version to deploy
        
    Returns:
        CreateDeploymentResponse containing the deployment_id
        
    Raises:
        XplainableAPIError: If deployment fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.deployments.deploy(model_version_id)
        logger.info(f"Executed deployments.deploy")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in deployments_deploy: {e}")
        raise


@mcp.tool()
def deployments_deactivate_deployment(deployment_id: str):
    """
    Deactivate a deployment.
    
    Args:
        deployment_id: ID of the deployment to deactivate
        
    Returns:
        Success message
        
    Raises:
        XplainableAPIError: If deactivation fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.deployments.deactivate_deployment(deployment_id)
        logger.info(f"Executed deployments.deactivate_deployment")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in deployments_deactivate_deployment: {e}")
        raise


@mcp.tool()
def deployments_generate_deploy_key(deployment_id: str, description: str = '', days_until_expiry: int = 90):
    """
    Generate a deploy key for a deployment.
    
    Args:
        deployment_id: ID of the deployment
        description: Description of the deploy key use case
        days_until_expiry: Number of days until the key expires
        
    Returns:
        The deploy key UUID
        
    Raises:
        XplainableAPIError: If key generation fails
    
    Category: write
    """
    try:
        client = get_client()
        result = client.deployments.generate_deploy_key(deployment_id, description, days_until_expiry)
        logger.info(f"Executed deployments.generate_deploy_key")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in deployments_generate_deploy_key: {e}")
        raise


@mcp.tool()
def deployments_get_active_team_deploy_keys_count(team_id: Optional[str] = None):
    """
    Get count of active deploy keys for a team.
    
    Args:
        team_id: Optional team ID (uses session team_id if not provided)
        
    Returns:
        Count of active deploy keys
        
    Raises:
        XplainableAPIError: If request fails
    
    Category: read
    """
    try:
        client = get_client()
        result = client.deployments.get_active_team_deploy_keys_count(team_id)
        logger.info(f"Executed deployments.get_active_team_deploy_keys_count")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in deployments_get_active_team_deploy_keys_count: {e}")
        raise

