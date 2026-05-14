"""
Autotrain service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp
import xplainable_client.client.py_models.autotrain

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client, XP_ICON


# Autotrain Tools
# ============================================


@mcp.tool(icons=[XP_ICON])
def autotrain_summarize_by_dataset_id(dataset_id: str, team_id: Optional[str] = None):
    """
    Summarize a dataset that's already on the xplainable platform.

    Downloads the dataset server-side and returns column statistics,
    types, distributions, and metadata. Use this to understand a dataset
    before training -- the raw data never leaves the platform.

    Use datasets_list_team_datasets to find available dataset IDs.

    Args:
        dataset_id: ID of the dataset on the platform
        team_id: Team ID (uses session team_id if not provided)

    Returns:
        Dataset summary with column statistics, types, and metadata

    Category: read
    """
    try:
        client = get_client()
        result = client.autotrain.summarize_by_dataset_id(
            dataset_id=dataset_id,
            team_id=team_id,
        )
        logger.info("Executed autotrain.summarize_by_dataset_id")

        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_summarize_by_dataset_id: {e}")
        raise


def autotrain_generate_feature_engineering(summary: dict, team_id: Optional[str] = None, n: int = 5, textgen_config: Optional[dict] = None):
    """
    Generate feature engineering recommendations.
    
    Args:
        summary: Dataset summary from summarize_dataset
        team_id: Team ID (uses session team_id if not provided)
        n: Number of recommendations to generate
        textgen_config: Text generation configuration
        
    Returns:
        List of feature engineering recommendations
        
    Raises:
        XplainableAPIError: If generation fails

    Category: analysis
    Workflow: Step 2 of autotrain. Run after: autotrain_summarize_dataset.
    """
    try:
        client = get_client()
        result = client.autotrain.generate_feature_engineering(summary, team_id, n, textgen_config)
        logger.info(f"Executed autotrain.generate_feature_engineering")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_generate_feature_engineering: {e}")
        raise

def autotrain_check_training_status(training_id: str, team_id: Optional[str] = None):
    """
    Check the status of a training job.
    
    Args:
        training_id: Training job ID from start_autotrain
        team_id: Team ID (uses session team_id if not provided)
        
    Returns:
        Training status and progress information
        
    Raises:
        XplainableAPIError: If status check fails

    Category: read
    Workflow: Step 4 of autotrain. Run after: autotrain_start_autotrain, autotrain_train_manual.
    """
    try:
        client = get_client()
        result = client.autotrain.check_training_status(training_id, team_id)
        logger.info(f"Executed autotrain.check_training_status")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_check_training_status: {e}")
        raise

def autotrain_train_manual(label: str, model_name: str, model_description: str, preprocessor_id: str, version_id: str, team_id: Optional[str] = None, drop_columns: Optional[List[str]] = None):
    """
    Train a model manually with specific parameters.
    
    Args:
        label: Target label column
        model_name: Name for the model
        model_description: Description of the model
        preprocessor_id: Preprocessor ID
        version_id: Preprocessor version ID
        team_id: Team ID (uses session team_id if not provided)
        drop_columns: Columns to drop
        
    Returns:
        Training job information
        
    Raises:
        XplainableAPIError: If training fails to start

    Category: write
    Workflow: Step 3 of autotrain. Run after: autotrain_summarize_dataset.
    """
    try:
        client = get_client()
        result = client.autotrain.train_manual(label, model_name, model_description, preprocessor_id, version_id, team_id, drop_columns)
        logger.info(f"Executed autotrain.train_manual")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_train_manual: {e}")
        raise
