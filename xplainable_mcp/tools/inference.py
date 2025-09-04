"""
Inference service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Inference Tools
# ============================================


@mcp.tool()
def inference_predict(filename: str, model_id: str, version_id: str, threshold: float = 0.5, delimiter: str = ', '):
    """
    Predicts the target column of a dataset.
    
    Args:
        filename (str): The name of the file.
        model_id (str): The model id.
        version_id (str): The version id.
        threshold (float): The threshold for classification models.
        delimiter (str): The delimiter of the file.
        
    Returns:
        dict: The prediction results.
    
    Category: inference
    """
    try:
        client = get_client()
        result = client.inference.predict(filename, model_id, version_id, threshold, delimiter)
        logger.info(f"Executed inference.predict")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in inference_predict: {e}")
        raise


@mcp.tool()
def inference_stream_predictions(filename: str, model_id: str, version_id: str, threshold: float = 0.5, delimiter: str = ', ', batch_size: int = 1000):
    """
    Stream predictions for large datasets by processing in batches.
    
    Args:
        filename: Path to CSV file to stream
        model_id: ID of the model
        version_id: ID of the model version
        threshold: Classification threshold
        delimiter: CSV delimiter
        batch_size: Size of each batch to process
        
    Yields:
        Batch prediction results
    
    Category: inference
    """
    try:
        client = get_client()
        result = client.inference.stream_predictions(filename, model_id, version_id, threshold, delimiter, batch_size)
        logger.info(f"Executed inference.stream_predictions")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in inference_stream_predictions: {e}")
        raise

