"""
Reports service MCP tools.

Auto-generated and maintained by the xplainable-client sync workflow.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

# Import shared utilities
from ..server import get_client


# Reports Tools
# ============================================


@mcp.tool()
def reports_available_widgets():
    """
    Return the available widget tags and their descriptions.
    
    Visual widgets (baseValue, confusionMatrix, etc.) should be used
    at most once per report. Text widgets (h2, p, divider) can repeat.

    Category: analysis
    Workflow: Step 1 of reports.
    """
    try:
        client = get_client()
        result = client.reports.available_widgets()
        logger.info(f"Executed reports.available_widgets")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in reports_available_widgets: {e}")
        raise

@mcp.tool()
def reports_create_report(run_id: str, report_name: str, report_description: str = '', is_public: bool = False, widgets: Optional[List[str]] = None, mode: str = 'dynamic', max_features: int = 40, constraints: Optional[Dict] = None, audience: Optional[Dict] = None):
    """
    Start async report generation via the wizard.
    
    Returns:
        Dict with job_id and status ("accepted")

    Category: write
    Workflow: Step 2 of reports. Run after: reports_available_widgets.
    """
    try:
        client = get_client()
        result = client.reports.create_report(run_id, report_name, report_description, is_public, widgets, mode, max_features, constraints, audience)
        logger.info(f"Executed reports.create_report")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in reports_create_report: {e}")
        raise

@mcp.tool()
def reports_create_report_sync(run_id: str, report_name: str, report_description: str = '', is_public: bool = False, widgets: Optional[List[str]] = None, mode: str = 'dynamic', max_features: int = 40, constraints: Optional[Dict] = None, audience: Optional[Dict] = None, timeout: int = 120, poll_interval: float = 2.0):
    """
    Create a report synchronously (polls until complete or timeout).
    
    Returns:
        Dict with status, report_id, version_id

    Category: write
    Workflow: Step 2 of reports. Run after: reports_available_widgets.
    """
    try:
        client = get_client()
        result = client.reports.create_report_sync(run_id, report_name, report_description, is_public, widgets, mode, max_features, constraints, audience, timeout, poll_interval)
        logger.info(f"Executed reports.create_report_sync")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in reports_create_report_sync: {e}")
        raise
