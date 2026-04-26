"""
Analytics and monitoring MCP tools.

Provides access to inference metrics, status code distributions,
and event logs via the xPanel analytics API.
"""

import logging
from typing import Optional
from ..mcp_instance import mcp

logger = logging.getLogger(__name__)

from ..server import get_client


# Analytics Tools
# ============================================

@mcp.tool()
def analytics_get_inference_metrics(
    from_date: str,
    to_date: str,
    deployment_id: Optional[str] = None,
    team_id: Optional[str] = None,
    unit: str = "day",
    metric: str = "count",
):
    """
    Get inference API call metrics over time.

    Args:
        from_date: Start date in YYYY-MM-DD format (e.g. '2024-01-01')
        to_date: End date in YYYY-MM-DD format (e.g. '2024-12-31')
        deployment_id: Filter to a specific deployment
        team_id: Filter to a specific team (returns all team deployments)
        unit: Time aggregation granularity - 'hour', 'day', 'month', or 'year'
        metric: Metric type - 'count', 'avg_latency', or 'success_rate'

    Returns:
        Time-series data with values keyed by date

    Category: read
    """
    try:
        client = get_client()
        result = client.analytics.get_inference_metrics(
            from_date=from_date,
            to_date=to_date,
            deployment_id=deployment_id,
            team_id=team_id,
            unit=unit,
            metric=metric,
        )
        logger.info("Executed analytics.get_inference_metrics")

        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in analytics_get_inference_metrics: {e}")
        raise


@mcp.tool()
def analytics_get_status_code_distribution(
    from_date: str,
    to_date: str,
    deployment_id: Optional[str] = None,
    team_id: Optional[str] = None,
    unit: Optional[str] = None,
):
    """
    Get status code distribution for inference predictions.

    When unit is omitted, returns total counts per status code (e.g. {200: 1523, 404: 12}).
    When unit is provided, returns time-series breakdown per status code for charting.

    Args:
        from_date: Start date in YYYY-MM-DD format (e.g. '2024-01-01')
        to_date: End date in YYYY-MM-DD format (e.g. '2024-12-31')
        deployment_id: Filter to a specific deployment
        team_id: Filter to a specific team (returns all team deployments)
        unit: Optional time granularity - 'hour', 'day', 'month', or 'year'. Omit for totals only.

    Returns:
        Status code distribution data

    Category: read
    """
    try:
        client = get_client()
        result = client.analytics.get_status_code_distribution(
            from_date=from_date,
            to_date=to_date,
            deployment_id=deployment_id,
            team_id=team_id,
            unit=unit,
        )
        logger.info("Executed analytics.get_status_code_distribution")

        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in analytics_get_status_code_distribution: {e}")
        raise


@mcp.tool()
def analytics_get_success_rate(
    from_date: str,
    to_date: str,
    deployment_id: Optional[str] = None,
    team_id: Optional[str] = None,
    unit: str = "day",
):
    """
    Get inference prediction success rate over time.

    Returns the ratio of successful (HTTP 200) predictions to total predictions.

    Args:
        from_date: Start date in YYYY-MM-DD format (e.g. '2024-01-01')
        to_date: End date in YYYY-MM-DD format (e.g. '2024-12-31')
        deployment_id: Filter to a specific deployment
        team_id: Filter to a specific team
        unit: Time aggregation granularity - 'hour', 'day', 'month', or 'year'

    Returns:
        Time-series data with success rate values (0.0 to 1.0) keyed by date

    Category: read
    """
    try:
        client = get_client()
        result = client.analytics.get_success_rate(
            from_date=from_date,
            to_date=to_date,
            deployment_id=deployment_id,
            team_id=team_id,
            unit=unit,
        )
        logger.info("Executed analytics.get_success_rate")

        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in analytics_get_success_rate: {e}")
        raise


@mcp.tool()
def analytics_get_events(
    from_date: str,
    to_date: str,
    event: Optional[str] = None,
    organisation_id: Optional[str] = None,
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
    model_id: Optional[str] = None,
    deployment_id: Optional[str] = None,
    page: Optional[int] = None,
    items_per_page: Optional[int] = None,
):
    """
    Get raw event logs with flexible filtering.

    Args:
        from_date: Start date in YYYY-MM-DD format (e.g. '2024-01-01')
        to_date: End date in YYYY-MM-DD format (e.g. '2024-12-31')
        event: Comma-separated event names (e.g. 'created_model,viewed_report')
        organisation_id: Filter by organisation
        team_id: Filter by team
        user_id: Filter by user
        model_id: Filter by model
        deployment_id: Filter by deployment
        page: Page number for pagination (starts at 1)
        items_per_page: Number of items per page

    Returns:
        List of event documents

    Category: read
    """
    try:
        client = get_client()
        result = client.analytics.get_events(
            from_date=from_date,
            to_date=to_date,
            event=event,
            organisation_id=organisation_id,
            team_id=team_id,
            user_id=user_id,
            model_id=model_id,
            deployment_id=deployment_id,
            page=page,
            items_per_page=items_per_page,
        )
        logger.info("Executed analytics.get_events")

        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif isinstance(result, list) and result and hasattr(result[0], 'model_dump'):
            return [item.model_dump() for item in result]
        else:
            return result
    except Exception as e:
        logger.error(f"Error in analytics_get_events: {e}")
        raise
