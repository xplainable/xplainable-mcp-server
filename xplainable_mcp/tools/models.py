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


@mcp.tool(icons=[XP_ICON])
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

@mcp.tool(icons=[XP_ICON])
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

@mcp.tool(icons=[XP_ICON])
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

@mcp.tool(icons=[XP_ICON])
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

@mcp.tool(icons=[XP_ICON])
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

@mcp.tool(icons=[XP_ICON])
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

@mcp.tool(icons=[XP_ICON])
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

@mcp.tool(icons=[XP_ICON])
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

@mcp.tool(icons=[XP_ICON])
def models_refit_model(model_id: str, version_id: str, target_column: str, file_path: Optional[str] = None, dataset_name: Optional[str] = None, csv_content: Optional[str] = None, model_type: str = 'classifier', features: Optional[List[str]] = None, preprocessor_version_id: Optional[str] = None, drop_columns: Optional[List[str]] = None, test_size: float = 0.2, max_depth: Optional[int] = None, min_info_gain: Optional[float] = None, min_leaf_size: Optional[float] = None, weight: Optional[float] = None, power_degree: Optional[float] = None, sigmoid_exponent: Optional[float] = None, tail_sensitivity: Optional[float] = None):
    """
    Rapidly refit an existing model with new parameters without retraining.
    
    This is orders of magnitude faster than train_model because it reuses
    the pre-computed feature partitions from the original training. Only the
    scores and profile are recomputed with the new parameters.
    
    Use this to iterate on hyperparameters after an initial train_model call.
    The model structure (splits) stays the same -- only the scoring changes.
    
    Args:
        model_id: ID of the existing model.
        version_id: ID of the model version to refit.
        target_column: Name of the target column.
        file_path: Path to a local CSV (same data used for training).
        dataset_name: Name of an xplainable public dataset.
        csv_content: Raw CSV string (for remote MCP servers).
        model_type: Either "classifier" or "regressor".
        features: List of feature names to update. Defaults to all features.
        preprocessor_version_id: Preprocessor version ID if one was used in training.
        drop_columns: Columns to drop (same as in original training).
        test_size: Test split fraction (use same value as original training).
        max_depth: New max depth (None = keep current).
        min_info_gain: New min info gain (None = keep current).
        min_leaf_size: New min leaf size (None = keep current).
        weight: New weight (None = keep current).
        power_degree: New power degree (None = keep current).
        sigmoid_exponent: New sigmoid exponent (None = keep current).
        tail_sensitivity: New tail sensitivity (None = keep current).
    
    Returns:
        Dictionary with new version_id, train/test metrics, feature_importances,
        and the parameters that were changed.

    Category: write
    """
    try:
        client = get_client()
        result = client.models.refit_model(
            model_id=model_id,
            version_id=version_id,
            target_column=target_column,
            file_path=file_path,
            dataset_name=dataset_name,
            csv_content=csv_content,
            model_type=model_type,
            features=features,
            preprocessor_version_id=preprocessor_version_id,
            drop_columns=drop_columns,
            test_size=test_size,
            max_depth=max_depth,
            min_info_gain=min_info_gain,
            min_leaf_size=min_leaf_size,
            weight=weight,
            power_degree=power_degree,
            sigmoid_exponent=sigmoid_exponent,
            tail_sensitivity=tail_sensitivity,
        )
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

@mcp.tool(icons=[XP_ICON])
def models_train_model(target_column: str, model_name: str, model_description: str = '', file_path: Optional[str] = None, dataset_name: Optional[str] = None, csv_content: Optional[str] = None, model_type: str = 'classifier', preprocessor_version_id: Optional[str] = None, drop_columns: Optional[List[str]] = None, test_size: float = 0.2, max_depth: int = 8, min_info_gain: float = 0.0001, min_leaf_size: float = 0.0001, weight: float = 1.0, power_degree: float = 1.0, sigmoid_exponent: float = 0.0, tail_sensitivity: float = 1.0):
    """
    Train an xplainable model on a dataset and upload it to the platform.
    
    Provide ONE of: file_path (local CSV), dataset_name (xplainable public dataset),
    or csv_content (raw CSV string -- for remote MCP servers where file paths aren't shared).
    
    Args:
        target_column: Name of the column to predict.
        model_name: Name for the uploaded model.
        model_description: Description for the uploaded model.
        file_path: Path to a local CSV file.
        dataset_name: Name of an xplainable public dataset (e.g. "telco_churn").
        csv_content: Raw CSV string. Use when the MCP server can't access the
            client's filesystem (e.g. hosted MCP). Claude can read the file
            and pass its content directly.
        model_type: Either "classifier" or "regressor".
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
        result = client.models.train_model(
            target_column=target_column,
            model_name=model_name,
            model_description=model_description,
            file_path=file_path,
            dataset_name=dataset_name,
            csv_content=csv_content,
            model_type=model_type,
            preprocessor_version_id=preprocessor_version_id,
            drop_columns=drop_columns,
            test_size=test_size,
            max_depth=max_depth,
            min_info_gain=min_info_gain,
            min_leaf_size=min_leaf_size,
            weight=weight,
            power_degree=power_degree,
            sigmoid_exponent=sigmoid_exponent,
            tail_sensitivity=tail_sensitivity,
        )
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
