"""
Client manager for Xplainable MCP Server.

Handles per-user client initialization when running in HTTP mode (OAuth),
and falls back to a singleton client in stdio mode (API key from env).
"""

import os
import logging
import threading
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Per-user client cache (keyed by user ID from JWT)
_clients: dict[str, object] = {}
_clients_lock = threading.Lock()

# Singleton client for stdio/API-key mode
_static_client = None


class ServerConfig:
    """Simple config for client initialization."""
    api_key: str = os.getenv("XPLAINABLE_API_KEY", "")
    hostname: str = os.getenv("XPLAINABLE_HOSTNAME", "https://platform.xplainable.io")
    org_id: Optional[str] = os.getenv("XPLAINABLE_ORG_ID")
    team_id: Optional[str] = os.getenv("XPLAINABLE_TEAM_ID")


config = ServerConfig()


def _get_static_client():
    """Get or create the singleton client (API key mode)."""
    global _static_client
    if _static_client is None:
        from xplainable_client.client.client import XplainableClient
        _static_client = XplainableClient(
            api_key=config.api_key,
            hostname=config.hostname,
            org_id=config.org_id,
            team_id=config.team_id,
        )
        logger.info("Static XplainableClient initialized (API key mode)")
    return _static_client


def _get_user_client(user_id: str, token: str):
    """Get or create a per-user client (OAuth mode)."""
    with _clients_lock:
        if user_id not in _clients:
            from xplainable_client.client.client import XplainableClient
            _clients[user_id] = XplainableClient(
                bearer_token=token,
                hostname=config.hostname,
                team_id=config.team_id,
            )
            logger.info(f"Per-user XplainableClient created for user {user_id[:12]}...")
        return _clients[user_id]


def _get_current_user_id():
    """Get the current user ID from the request context, or None in stdio mode."""
    try:
        from fastmcp.server.dependencies import get_access_token
        access_token = get_access_token()
        if access_token is not None:
            user_id = access_token.client_id or "anonymous"
            if hasattr(access_token, 'claims') and access_token.claims:
                user_id = access_token.claims.get("sub", user_id)
            return user_id, access_token.token
    except Exception:
        pass
    return None, None


def set_active_team(team_id: str):
    """Set the active team for the current user's session.

    Updates the user's cached client session headers so all subsequent
    tool calls are scoped to that team.
    """
    user_id, token = _get_current_user_id()

    if user_id and token:
        with _clients_lock:
            if user_id in _clients:
                # Update team_id on existing client's session headers
                client = _clients[user_id]
                client.session.team_id = team_id
                client.session._session.headers['team_id'] = team_id
                logger.info(f"Updated team_id to {team_id} for user {user_id[:12]}...")
            else:
                # Create new client with team_id
                from xplainable_client.client.client import XplainableClient
                _clients[user_id] = XplainableClient(
                    bearer_token=token,
                    hostname=config.hostname,
                    team_id=team_id,
                )
                logger.info(f"Created client with team {team_id} for user {user_id[:12]}...")
    else:
        # Stdio mode: update or recreate static client
        global _static_client
        if _static_client is not None:
            _static_client.session.team_id = team_id
            _static_client.session._session.headers['team_id'] = team_id
            logger.info(f"Updated static client team_id to {team_id}")
        else:
            from xplainable_client.client.client import XplainableClient
            _static_client = XplainableClient(
                api_key=config.api_key,
                hostname=config.hostname,
                org_id=config.org_id,
                team_id=team_id,
            )
            logger.info(f"Created static client with team {team_id}")


def get_client():
    """Get the appropriate XplainableClient for the current request.

    In HTTP mode: extracts the user's JWT from the request context and
    returns a per-user client. In stdio mode: returns a singleton client
    using the API key from environment variables.

    All tool functions call this — no tool code changes needed.
    """
    user_id, token = _get_current_user_id()

    if user_id and token:
        client = _get_user_client(user_id, token)
        logger.debug(f"get_client: user={user_id[:12]}... team_id={client.session.team_id} cached_users={list(_clients.keys())}")
        return client

    # Fallback to static client (stdio mode or no auth context)
    return _get_static_client()
