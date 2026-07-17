"""
Optimisers service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp
from ..server import get_client, XP_ICON

logger = logging.getLogger(__name__)


# Optimisers Tools
# ============================================

@mcp.tool(icons=[XP_ICON], tags={"write"})
def optimisers_create_optimiser(model_id: str, model_version_id: str, name: str, description: Optional[str] = None):
    """
    Create a named optimiser policy on a v2 model version.

    Category: write
    Workflow: Step 1 of optimisers.
    """
    try:
        client = get_client()
        result = client.optimisers.create_optimiser(model_id, model_version_id, name, description)
        logger.info(f"Executed optimisers.create_optimiser")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_create_optimiser: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def optimisers_create_optimiser_version(optimiser_id: str, data: Optional[Dict] = None, description: Optional[str] = None):
    """
    Create a named policy version (OptimizationConfig overrides).
    
    ``data`` may contain any of the recognised batch keys (objective,
    budget, target, cost_weight, mutable_features, per_row_immutable,
    feature_bounds, cost_structure, infeasible, max_joint_candidates,
    n_grid, cost_resolution). Bounds are tighten-only relative to the
    model's default config.

    Category: write
    Workflow: Step 2 of optimisers.
    """
    try:
        client = get_client()
        result = client.optimisers.create_optimiser_version(optimiser_id, data, description)
        logger.info(f"Executed optimisers.create_optimiser_version")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_create_optimiser_version: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"inference"})
def optimisers_run_optimiser(optimiser_id: str, dataset_id: str, version_id: Optional[str] = None, params: Optional[Dict] = None, run_name: Optional[str] = None, run_description: Optional[str] = None):
    """
    Run a batch prescriptive optimisation over a dataset.
    
    Proxies to the deployed model's inference runtime and returns
    ``{run_id, batch_id, result}`` where ``result`` is the XGM envelope
    (branch on ``result['status']`` / ``result['error']['code']``).
    
    Args:
        optimiser_id: The optimiser to run.
        dataset_id: Dataset of rows to optimise (must be deployed model's signature).
        version_id: Optional named policy version; omit for the default policy.
        params: Per-run batch kwargs (override the policy), e.g.
            {"objective": "target", "budget": 100.0}.
        run_name: Optional run label.
        run_description: Optional run description.

    Category: inference
    Workflow: Step 3 of optimisers.
    """
    try:
        client = get_client()
        result = client.optimisers.run_optimiser(optimiser_id, dataset_id, version_id, params, run_name, run_description)
        logger.info(f"Executed optimisers.run_optimiser")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_run_optimiser: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def optimisers_list_optimisers(model_id: str):
    """
    List optimisers for a model.

    Category: read
    """
    try:
        client = get_client()
        result = client.optimisers.list_optimisers(model_id)
        logger.info(f"Executed optimisers.list_optimisers")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_list_optimisers: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def optimisers_list_optimiser_versions(optimiser_id: str):
    """
    List policy versions for an optimiser.

    Category: read
    """
    try:
        client = get_client()
        result = client.optimisers.list_optimiser_versions(optimiser_id)
        logger.info(f"Executed optimisers.list_optimiser_versions")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_list_optimiser_versions: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"read"})
def optimisers_get_optimiser_version(optimiser_id: str, version_id: str):
    """
    Get a single policy version.

    Category: read
    """
    try:
        client = get_client()
        result = client.optimisers.get_optimiser_version(optimiser_id, version_id)
        logger.info(f"Executed optimisers.get_optimiser_version")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_get_optimiser_version: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def optimisers_get_optimiser_run(optimiser_id: str, run_id: str):
    """
    Get an optimiser run and its batches.

    Category: read
    """
    try:
        client = get_client()
        result = client.optimisers.get_optimiser_run(optimiser_id, run_id)
        logger.info(f"Executed optimisers.get_optimiser_run")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_get_optimiser_run: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def optimisers_delete_optimiser(optimiser_id: str):
    """
    Delete an optimiser and its versions/runs.

    Category: write
    """
    try:
        client = get_client()
        result = client.optimisers.delete_optimiser(optimiser_id)
        logger.info(f"Executed optimisers.delete_optimiser")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_delete_optimiser: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def optimisers_delete_optimiser_version(optimiser_id: str, version_id: str):
    """
    Delete a policy version.

    Category: write
    """
    try:
        client = get_client()
        result = client.optimisers.delete_optimiser_version(optimiser_id, version_id)
        logger.info(f"Executed optimisers.delete_optimiser_version")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in optimisers_delete_optimiser_version: {e}")
        raise
