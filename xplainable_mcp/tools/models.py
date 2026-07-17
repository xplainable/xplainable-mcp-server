"""
Models service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client, XP_ICON


# Models Tools
# ============================================


@mcp.tool(icons=[XP_ICON], tags={"read"})
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

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
def models_get_feature_info(version_id: str):
    """
    Get feature information including types, health metrics, and distributions.
    
    Args:
        version_id: ID of the model version.
    
    Returns:
        Dictionary containing feature information.

    Category: read
    """
    try:
        client = get_client()
        result = client.models.get_feature_info(version_id)
        logger.info(f"Executed models.get_feature_info")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_get_feature_info: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"read"})
def models_get_model_evaluation(partition_id: str):
    """
    Get detailed evaluation metrics for a model partition.
    
    Args:
        partition_id: ID of the model partition.
    
    Returns:
        Dictionary containing evaluation metrics.

    Category: read
    """
    try:
        client = get_client()
        result = client.models.get_model_evaluation(partition_id)
        logger.info(f"Executed models.get_model_evaluation")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_get_model_evaluation: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"read"})
def models_get_model_profile(version_id: str):
    """
    Get the model profile showing feature contributions and decision boundaries.
    
    Args:
        version_id: ID of the model version.
    
    Returns:
        Dictionary containing the model profile data.

    Category: read
    """
    try:
        client = get_client()
        result = client.models.get_model_profile(version_id)
        logger.info(f"Executed models.get_model_profile")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_get_model_profile: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
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

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
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

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
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

@mcp.tool(icons=[XP_ICON], tags={"curated", "read"})
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

@mcp.tool(icons=[XP_ICON], tags={"write"})
def models_refit_model(version_id: str, dataset_id: str, target_column: str, features: Optional[List[str]] = None, feature_params: Optional[Dict[str, Dict]] = None, drop_columns: Optional[List[str]] = None, test_size: float = 0.2, max_depth: Optional[int] = None, min_info_gain: Optional[float] = None, min_leaf_size: Optional[float] = None, weight: Optional[float] = None, power_degree: Optional[float] = None, sigmoid_exponent: Optional[float] = None, tail_sensitivity: Optional[float] = None):
    """
    Rapidly refit an existing model with new parameters without retraining.
    
    Everything happens server-side in a single API call -- data never
    leaves the platform. Orders of magnitude faster than train_model.
    
    Two modes:
    1. Same params for features: set max_depth, weight, etc. directly.
       Use 'features' to target specific features, or omit for all.
    2. Per-feature params: pass feature_params dict to tune each feature
       independently in one call. e.g.:
       feature_params={"Tenure Months": {"max_depth": 3}, "Contract": {"max_depth": 5}}
    
    Args:
        version_id: ID of the model version to refit.
        dataset_id: ID of the dataset on the platform.
        target_column: Name of the target column.
        features: List of feature names to update (mode 1). Defaults to all.
        feature_params: Per-feature params dict (mode 2). Keys are feature
            names, values are dicts of params. Overrides features/params.
            e.g. {"Tenure": {"max_depth": 3}, "Charges": {"max_depth": 5}}
        drop_columns: Columns to drop (same as in original training).
        test_size: Test split fraction (same as original training).
        max_depth: New max depth (mode 1, None = keep current).
        min_info_gain: New min info gain (mode 1, None = keep current).
        min_leaf_size: New min leaf size (mode 1, None = keep current).
        weight: New weight (mode 1, None = keep current).
        power_degree: New power degree (mode 1, None = keep current).
        sigmoid_exponent: New sigmoid exponent (mode 1, None = keep current).
        tail_sensitivity: New tail sensitivity (mode 1, None = keep current).
    
    Returns:
        Dictionary with new version_id, train/test metrics, feature_importances,
        and the parameters that were changed.

    Category: write
    """
    try:
        client = get_client()
        result = client.models.refit_model(version_id, dataset_id, target_column, features, feature_params, drop_columns, test_size, max_depth, min_info_gain, min_leaf_size, weight, power_degree, sigmoid_exponent, tail_sensitivity)
        logger.info(f"Executed models.refit_model")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_refit_model: {e}")
        raise

@mcp.tool(icons=[XP_ICON], tags={"write"})
def models_train_model(target_column: str, model_name: str, model_description: str = '', file_path: Optional[str] = None, dataset_name: Optional[str] = None, dataset_id: Optional[str] = None, csv_content: Optional[str] = None, model_type: str = 'classifier', partition_on: Optional[str] = None, preprocessor_version_id: Optional[str] = None, drop_columns: Optional[List[str]] = None, test_size: float = 0.2, max_depth: int = 8, min_info_gain: float = 0.0001, min_leaf_size: float = 0.0001, weight: float = 1.0, power_degree: float = 1.0, sigmoid_exponent: float = 0.0, tail_sensitivity: float = 1.0):
    """
    Train an xplainable model on a dataset and upload it to the platform.
    
    Provide ONE of: dataset_id (preferred for hosted MCP), file_path (local CSV),
    dataset_name (xplainable public dataset), or csv_content (raw CSV string).
    
    Args:
        target_column: Name of the column to predict.
        model_name: Name for the uploaded model.
        model_description: Description for the uploaded model.
        file_path: Path to a local CSV file.
        dataset_name: Name of an xplainable public dataset (e.g. "telco_churn").
        dataset_id: ID of a dataset already on the xplainable platform.
            Use datasets_list_team_datasets to find available IDs. This is the
            preferred method for hosted/remote MCP servers.
        csv_content: Raw CSV string for when file paths aren't accessible.
        model_type: Either "classifier" or "regressor".
        partition_on: Optional column name to partition on. Trains a separate
            sub-model per unique value in this column (e.g. partition_on="Industry"
            trains one model per industry). The column stays in the data for
            routing predictions but each partition gets its own tuned model.
        preprocessor_version_id: Optional preprocessor version ID to load
            and apply a fitted pipeline to the features before training.
        drop_columns: Optional list of column names to exclude from features.
        test_size: Fraction of data to hold out for testing (0 to 1).
        max_depth: Maximum depth of the model decision tree.
        min_info_gain: Minimum information gain required to split.
        min_leaf_size: Minimum leaf size as a fraction of training data.
        weight: Model weight parameter.
        power_degree: Power degree parameter.
        sigmoid_exponent: Sigmoid exponent parameter.
        tail_sensitivity: Tail sensitivity parameter.
    
    Returns:
        Dictionary with model_id, version_id, train/test metrics,
        feature_importances, and train/test sample counts.

    Category: write
    """
    try:
        client = get_client()
        result = client.models.train_model(target_column, model_name, model_description, file_path, dataset_name, dataset_id, csv_content, model_type, partition_on, preprocessor_version_id, drop_columns, test_size, max_depth, min_info_gain, min_leaf_size, weight, power_degree, sigmoid_exponent, tail_sensitivity)
        logger.info(f"Executed models.train_model")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in models_train_model: {e}")
        raise
