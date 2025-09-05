"""
Gpt service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Gpt Tools
# ============================================


@mcp.tool()
def gpt_explain_model(model_id: str, version_id: str, language: str = 'en', detail_level: str = 'medium'):
    """
    Get a natural language explanation of the model.
    
    Args:
        model_id: ID of the model
        version_id: ID of the model version
        language: Language for the explanation (e.g., "en", "es", "fr")
        detail_level: Level of detail ("low", "medium", "high")
        
    Returns:
        Natural language explanation of the model
        
    Raises:
        XplainableAPIError: If explanation generation fails
    
    Category: analysis
    """
    try:
        client = get_client()
        result = client.gpt.explain_model(model_id, version_id, language, detail_level)
        logger.info(f"Executed gpt.explain_model")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in gpt_explain_model: {e}")
        raise


@mcp.tool()
def gpt_generate_documentation(model_id: str, version_id: str, include_technical: bool = True, include_business: bool = True, format: str = 'markdown'):
    """
    Generate comprehensive documentation for a model.
    
    Args:
        model_id: ID of the model
        version_id: ID of the model version
        include_technical: Include technical details
        include_business: Include business context
        format: Output format ("markdown", "html", "pdf")
        
    Returns:
        Generated documentation
        
    Raises:
        XplainableAPIError: If documentation generation fails
    
    Category: analysis
    """
    try:
        client = get_client()
        result = client.gpt.generate_documentation(model_id, version_id, include_technical, include_business, format)
        logger.info(f"Executed gpt.generate_documentation")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in gpt_generate_documentation: {e}")
        raise


@mcp.tool()
def gpt_generate_report(model_id: str, version_id: str, target_description: str = 'text', project_objective: str = 'text', max_features: int = 15, temperature: float = 0.7):
    """
    Generate a GPT-powered report for a model.
    
    Args:
        model_id: ID of the model
        version_id: ID of the model version
        target_description: Description of the target variable
        project_objective: Objective of the project/model
        max_features: Maximum number of features to include in report
        temperature: GPT temperature parameter (0-2, higher = more creative)
        
    Returns:
        Generated report with insights
        
    Raises:
        XplainableAPIError: If report generation fails
    
    Category: analysis
    """
    try:
        client = get_client()
        result = client.gpt.generate_report(model_id, version_id, target_description, project_objective, max_features, temperature)
        logger.info(f"Executed gpt.generate_report")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in gpt_generate_report: {e}")
        raise

