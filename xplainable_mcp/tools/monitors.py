"""
Monitors MCP tools.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

from ..server import get_client, XP_ICON


@mcp.tool(icons=[XP_ICON])
def monitors_create_monitor(model_id: str, name: str, description: str = '', threshold: float = 0.5, data_source_type: str = 'csv', schedule_type: str = 'manual'):
    """
    Create a new monitor for a model.
    
    Args:
        model_id: ID of the model
        name: Name of the monitor
        description: Description of the monitor
        threshold: Decision threshold
        data_source_type: Data source type
        schedule_type: Schedule type
    
    Returns:
        The monitor ID

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.create_monitor(model_id, name, description, threshold, data_source_type, schedule_type)
        logger.info(f"Executed monitors.create_monitor")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_create_monitor: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def monitors_get_monitor(monitor_id: str):
    """
    Get a monitor by ID.
    
    Args:
        monitor_id: ID of the monitor
    
    Returns:
        Monitor data

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_monitor(monitor_id)
        logger.info(f"Executed monitors.get_monitor")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_get_monitor: {e}")
        raise

def monitors_get_model_monitors(model_id: str):
    """
    Get all monitors for a specific model.
    
    Args:
        model_id: ID of the model
    
    Returns:
        List of monitor information

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_model_monitors(model_id)
        logger.info(f"Executed monitors.get_model_monitors")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_get_model_monitors: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def monitors_get_team_monitors(team_id: Optional[str] = None):
    """
    Get all monitors for a team.
    
    Args:
        team_id: Optional team ID (uses session team_id if not provided)
    
    Returns:
        List of monitor information

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_team_monitors(team_id)
        logger.info(f"Executed monitors.get_team_monitors")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_get_team_monitors: {e}")
        raise

def monitors_delete_monitor(monitor_id: str):
    """
    Delete a monitor.
    
    Args:
        monitor_id: ID of the monitor to delete
    
    Returns:
        Success message

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.delete_monitor(monitor_id)
        logger.info(f"Executed monitors.delete_monitor")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_delete_monitor: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def monitors_get_alert_rules(monitor_id: str):
    """
    Get alert rules for a monitor.
    
    Args:
        monitor_id: ID of the monitor
    
    Returns:
        Alert rules data

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_alert_rules(monitor_id)
        logger.info(f"Executed monitors.get_alert_rules")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_get_alert_rules: {e}")
        raise

def monitors_create_alert_rule(monitor_id: str, rule_type: str, value: float, notify_in_app: bool = True, notify_email: bool = False):
    """
    Create an alert rule for a monitor.
    
    Args:
        monitor_id: ID of the monitor
        rule_type: Type of rule (threshold, trend, volume)
        value: Rule threshold value
        notify_in_app: Send in-app notification
        notify_email: Send email notification
    
    Returns:
        Created alert rule data

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.create_alert_rule(monitor_id, rule_type, value, notify_in_app, notify_email)
        logger.info(f"Executed monitors.create_alert_rule")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_create_alert_rule: {e}")
        raise

def monitors_add_monitor_items(monitor_id: str, monitor_items: List[dict]):
    """
    Add items to a monitor.
    
    Args:
        monitor_id: ID of the monitor
        monitor_items: List of monitor item data
    
    Returns:
        Created item IDs

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.add_monitor_items(monitor_id, monitor_items)
        logger.info(f"Executed monitors.add_monitor_items")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_add_monitor_items: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def monitors_delete_monitor_item(monitor_item_id: str):
    """
    Delete a monitor item.
    
    Args:
        monitor_item_id: ID of the monitor item
    
    Returns:
        Success message

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.delete_monitor_item(monitor_item_id)
        logger.info(f"Executed monitors.delete_monitor_item")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_delete_monitor_item: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def monitors_get_monitor_item(monitor_item_id: str):
    """
    Get a specific monitor item.
    
    Args:
        monitor_item_id: ID of the monitor item
    
    Returns:
        Monitor item data

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_monitor_item(monitor_item_id)
        logger.info(f"Executed monitors.get_monitor_item")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_get_monitor_item: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def monitors_update_monitor_description(monitor_id: str, description: str):
    """
    Update the description of a monitor.
    
    Args:
        monitor_id: ID of the monitor
        description: New description
    
    Returns:
        Updated monitor data

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.update_monitor_description(monitor_id, description)
        logger.info(f"Executed monitors.update_monitor_description")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_update_monitor_description: {e}")
        raise

@mcp.tool(icons=[XP_ICON])
def monitors_update_monitor_name(monitor_id: str, name: str):
    """
    Update the name of a monitor.
    
    Args:
        monitor_id: ID of the monitor
        name: New name
    
    Returns:
        Updated monitor data

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.update_monitor_name(monitor_id, name)
        logger.info(f"Executed monitors.update_monitor_name")
        
        # Handle different return types
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in monitors_update_monitor_name: {e}")
        raise
