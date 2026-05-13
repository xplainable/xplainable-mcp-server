"""
Monitors MCP tools.
"""

import logging
from typing import Optional, List, Dict, Any
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

from ..server import get_client, XP_ICON


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
        logger.info("Executed monitors.create_monitor")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_create_monitor: {e}")
        raise


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
        logger.info("Executed monitors.create_alert_rule")
        return result
    except Exception as e:
        logger.error(f"Error in monitors_create_alert_rule: {e}")
        raise
