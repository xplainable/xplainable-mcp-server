"""
Client manager for Xplainable MCP Server.

This module handles the lazy initialization of the Xplainable client.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Lazy initialization of Xplainable client
_client = None


class ServerConfig:
    """Simple config for client initialization."""
    api_key: str = os.getenv("XPLAINABLE_API_KEY", "")
    hostname: str = os.getenv("XPLAINABLE_HOSTNAME", "https://platform.xplainable.io")
    org_id: Optional[str] = os.getenv("XPLAINABLE_ORG_ID")
    team_id: Optional[str] = os.getenv("XPLAINABLE_TEAM_ID")


config = ServerConfig()


def get_client():
    """Get or create the Xplainable client instance."""
    global _client
    if _client is None:
        try:
            from xplainable_client.client.client import XplainableClient
            _client = XplainableClient(
                api_key=config.api_key,
                hostname=config.hostname,
                org_id=config.org_id,
                team_id=config.team_id
            )
            logger.info("Xplainable client initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import xplainable_client: {e}")
            logger.error("Please install xplainable-client: pip install xplainable-client")
            raise RuntimeError("xplainable-client not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Xplainable client: {e}")
            raise RuntimeError(f"Failed to initialize Xplainable client: {e}")
    return _client