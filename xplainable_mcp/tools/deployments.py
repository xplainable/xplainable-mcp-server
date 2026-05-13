"""
Deployments service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client, XP_ICON


# Deployments Tools
# ============================================


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
    Workflow: Step 3 of deployments. Run after: deployments_deploy.
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
    Workflow: Step 3 of deployments. Run after: deployments_deploy.
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
