"""
Monitors (formerly collections) MCP tools.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

from ..server import get_client, XP_ICON


@mcp.tool(icons=[XP_ICON])
def monitors_create_monitor(
    model_id: str,
    name: str,
    description: str = "",
    threshold: float = 0.5,
):
    """
    Create a new monitor for a model.

    Args:
        model_id: ID of the model
        name: Name of the monitor
        description: Description of the monitor
        threshold: Decision threshold

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.create_monitor(
            model_id=model_id,
            name=name,
            description=description,
            threshold=threshold,
        )
        logger.info("Executed collections.create_monitor")
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

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_monitor(monitor_id)
        logger.info("Executed collections.get_monitor")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_get_monitor: {e}")
        raise


@mcp.tool(icons=[XP_ICON])
def monitors_get_model_monitors(model_id: str):
    """
    Get all monitors for a specific model.

    Args:
        model_id: ID of the model

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_model_monitors(model_id)
        logger.info("Executed collections.get_model_monitors")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_get_model_monitors: {e}")
        raise


@mcp.tool(icons=[XP_ICON])
def monitors_get_team_monitors():
    """
    Get all monitors for the active team.

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_team_monitors()
        logger.info("Executed collections.get_team_monitors")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_get_team_monitors: {e}")
        raise


@mcp.tool(icons=[XP_ICON])
def monitors_update_name(monitor_id: str, name: str):
    """
    Update the name of a monitor.

    Args:
        monitor_id: ID of the monitor
        name: New name

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.update_monitor_name(monitor_id, name)
        logger.info("Executed collections.update_monitor_name")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_update_name: {e}")
        raise


@mcp.tool(icons=[XP_ICON])
def monitors_update_description(monitor_id: str, description: str):
    """
    Update the description of a monitor.

    Args:
        monitor_id: ID of the monitor
        description: New description

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.update_monitor_description(monitor_id, description)
        logger.info("Executed collections.update_monitor_description")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_update_description: {e}")
        raise


@mcp.tool(icons=[XP_ICON])
def monitors_delete_monitor(monitor_id: str):
    """
    Delete a monitor.

    Args:
        monitor_id: ID of the monitor to delete

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.delete_monitor(monitor_id)
        logger.info("Executed collections.delete_monitor")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_delete_monitor: {e}")
        raise


@mcp.tool(icons=[XP_ICON])
def monitors_add_items(monitor_id: str, monitor_items: List[dict]):
    """
    Add items to a monitor.

    Args:
        monitor_id: ID of the monitor
        monitor_items: List of monitor item data

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.add_monitor_items(monitor_id, monitor_items)
        logger.info("Executed collections.add_monitor_items")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_add_items: {e}")
        raise


@mcp.tool(icons=[XP_ICON])
def monitors_get_alert_rules(monitor_id: str):
    """
    Get alert rules for a monitor.

    Args:
        monitor_id: ID of the monitor

    Category: read
    """
    try:
        client = get_client()
        result = client.monitors.get_alert_rules(monitor_id)
        logger.info("Executed collections.get_alert_rules")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_get_alert_rules: {e}")
        raise


@mcp.tool(icons=[XP_ICON])
def monitors_create_alert_rule(
    monitor_id: str,
    rule_type: str,
    value: float,
    notify_in_app: bool = True,
    notify_email: bool = False,
):
    """
    Create an alert rule for a monitor.

    Args:
        monitor_id: ID of the monitor
        rule_type: Type of rule (threshold, trend, volume)
        value: Rule threshold value
        notify_in_app: Send in-app notification
        notify_email: Send email notification

    Category: write
    """
    try:
        client = get_client()
        result = client.monitors.create_alert_rule(
            monitor_id=monitor_id,
            rule_type=rule_type,
            value=value,
            notify_in_app=notify_in_app,
            notify_email=notify_email,
        )
        logger.info("Executed collections.create_alert_rule")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_create_alert_rule: {e}")
        raise
