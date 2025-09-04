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
from ..server import get_client


# Autotrain Tools
# ============================================


@mcp.tool()
def autotrain_generate_labels(summary: xplainable_client.client.py_models.autotrain.DatasetSummary, team_id: Optional[str] = None, textgen_config: Optional[xplainable_client.client.py_models.autotrain.TextGenConfig] = None):
    """
    Generate label recommendations for training.
    
    Args:
        summary: Dataset summary from summarize_dataset
        team_id: Team ID (uses session team_id if not provided)
        textgen_config: Text generation configuration
        
    Returns:
        List of label recommendations
        
    Raises:
        XplainableAPIError: If label generation fails
    
    Category: analysis
    """
    try:
        client = get_client()
        result = client.autotrain.generate_labels(summary, team_id, textgen_config)
        logger.info(f"Executed autotrain.generate_labels")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_generate_labels: {e}")
        raise


@mcp.tool()
def autotrain_start_autotrain(model_name: str, model_description: str, summary: xplainable_client.client.py_models.autotrain.DatasetSummary, team_id: Optional[str] = None, textgen_config: Optional[xplainable_client.client.py_models.autotrain.TextGenConfig] = None):
    """
    Start the autotrain process.
    
    Args:
        model_name: Name for the model
        model_description: Description of the model
        summary: Dataset summary from summarize_dataset
        team_id: Team ID (uses session team_id if not provided)
        textgen_config: Text generation configuration
        
    Returns:
        Training job information
        
    Raises:
        XplainableAPIError: If autotrain fails to start
    
    Category: write
    """
    try:
        client = get_client()
        result = client.autotrain.start_autotrain(model_name, model_description, summary, team_id, textgen_config)
        logger.info(f"Executed autotrain.start_autotrain")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_start_autotrain: {e}")
        raise


@mcp.tool()
def autotrain_summarize_dataset(file_path: str, team_id: Optional[str] = None, textgen_config: Optional[xplainable_client.client.py_models.autotrain.TextGenConfig] = None):
    """
    Summarize a dataset by uploading a file.
    
    Args:
        file_path: Path to the dataset file
        team_id: Team ID (uses session team_id if not provided)
        textgen_config: Text generation configuration
        
    Returns:
        Dataset summary and metadata
        
    Raises:
        FileNotFoundError: If file doesn't exist
        XplainableAPIError: If summarization fails
    
    Category: analysis
    """
    try:
        client = get_client()
        result = client.autotrain.summarize_dataset(file_path, team_id, textgen_config)
        logger.info(f"Executed autotrain.summarize_dataset")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_summarize_dataset: {e}")
        raise


@mcp.tool()
def autotrain_generate_feature_engineering(summary: xplainable_client.client.py_models.autotrain.DatasetSummary, team_id: Optional[str] = None, n: int = 5, textgen_config: Optional[xplainable_client.client.py_models.autotrain.TextGenConfig] = None):
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


@mcp.tool()
def autotrain_generate_goals(summary: xplainable_client.client.py_models.autotrain.DatasetSummary, team_id: Optional[str] = None, n: int = 5, textgen_config: Optional[xplainable_client.client.py_models.autotrain.TextGenConfig] = None):
    """
    Generate training goals based on dataset summary.
    
    Args:
        summary: Dataset summary from summarize_dataset
        team_id: Team ID (uses session team_id if not provided)
        n: Number of goals to generate
        textgen_config: Text generation configuration
        
    Returns:
        List of training goals
        
    Raises:
        XplainableAPIError: If goal generation fails
    
    Category: analysis
    """
    try:
        client = get_client()
        result = client.autotrain.generate_goals(summary, team_id, n, textgen_config)
        logger.info(f"Executed autotrain.generate_goals")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_generate_goals: {e}")
        raise


@mcp.tool()
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


@mcp.tool()
def autotrain_generate_insights(goal: Dict[str, Any], summary: xplainable_client.client.py_models.autotrain.DatasetSummary, team_id: Optional[str] = None, textgen_config: Optional[xplainable_client.client.py_models.autotrain.TextGenConfig] = None):
    """
    Generate insights about the dataset.
    
    Args:
        goal: Analysis goal
        summary: Dataset summary
        team_id: Team ID (uses session team_id if not provided)
        textgen_config: Text generation configuration
        
    Returns:
        Generated insights and analysis
        
    Raises:
        XplainableAPIError: If insight generation fails
    
    Category: analysis
    """
    try:
        client = get_client()
        result = client.autotrain.generate_insights(goal, summary, team_id, textgen_config)
        logger.info(f"Executed autotrain.generate_insights")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_generate_insights: {e}")
        raise


@mcp.tool()
def autotrain_visualize_data(summary: xplainable_client.client.py_models.autotrain.DatasetSummary, goal: Dict[str, Any], team_id: Optional[str] = None, library: str = 'plotly', textgen_config: Optional[xplainable_client.client.py_models.autotrain.TextGenConfig] = None):
    """
    Generate data visualizations.
    
    Args:
        summary: Dataset summary
        goal: Visualization goal
        team_id: Team ID (uses session team_id if not provided)
        library: Visualization library (plotly, matplotlib, seaborn)
        textgen_config: Text generation configuration
        
    Returns:
        Visualization code and metadata
        
    Raises:
        XplainableAPIError: If visualization generation fails
    
    Category: analysis
    """
    try:
        client = get_client()
        result = client.autotrain.visualize_data(summary, goal, team_id, library, textgen_config)
        logger.info(f"Executed autotrain.visualize_data")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in autotrain_visualize_data: {e}")
        raise


@mcp.tool()
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

