"""
Xplainable MCP Server implementation using FastMCP.

This server provides secure access to Xplainable AI platform capabilities
through standardized MCP tools.
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastmcp import FastMCP
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from .response_handlers import (
    handle_none_as_empty_list,
    safe_model_dump_list,
    safe_model_dump,
    safe_list_response,
    safe_client_call
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServerConfig(BaseModel):
    """Server configuration model."""
    api_key: str = Field(..., description="Xplainable API key")
    hostname: str = Field(
        default="https://platform.xplainable.io",
        description="Xplainable API hostname"
    )
    org_id: Optional[str] = Field(None, description="Organization ID")
    team_id: Optional[str] = Field(None, description="Team ID")
    enable_write_tools: bool = Field(
        default=False,
        description="Enable write operations (deploy, activate, etc.)"
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )


def load_config() -> ServerConfig:
    """Load configuration from environment variables."""
    api_key = os.environ.get("XPLAINABLE_API_KEY")
    if not api_key:
        logger.error("XPLAINABLE_API_KEY environment variable not set")
        sys.exit(1)
    
    return ServerConfig(
        api_key=api_key,
        hostname=os.getenv("XPLAINABLE_HOST", "https://platform.xplainable.io"),
        org_id=os.getenv("XPLAINABLE_ORG_ID"),
        team_id=os.getenv("XPLAINABLE_TEAM_ID"),
        enable_write_tools=os.getenv("ENABLE_WRITE_TOOLS", "false").lower() == "true",
        rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
    )


# Initialize configuration
config = load_config()

# Initialize FastMCP server
mcp = FastMCP(
    name="xplainable-mcp",
    version="0.1.0"
)

# Lazy initialization of Xplainable client
_client = None

def get_client():
    """Get or create the Xplainable client instance."""
    global _client
    if _client is None:
        # Import here to avoid issues if xplainable-client is not installed during testing
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
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to initialize Xplainable client: {e}")
            sys.exit(1)
    return _client


# ============================================================================
# DISCOVERY/METADATA TOOLS
# ============================================================================

@mcp.tool()
def list_tools() -> Dict[str, Any]:
    """
    List all available MCP tools and their descriptions.
    
    Returns:
        Dictionary containing tool information organized by category
    """
    try:
        # Use the enhanced tool registry for better introspection
        from xplainable_mcp.tool_registry import get_registry
        
        registry = get_registry(mcp)
        tools_info = registry.to_dict()
        
        logger.info(f"Listed {tools_info['total_tools']} available tools")
        return tools_info
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise


# ============================================================================
# READ-ONLY TOOLS
# ============================================================================

@mcp.tool()
def get_connection_info() -> Dict[str, Any]:
    """
    Return connection and user info for diagnostics (no secrets).
    
    Returns:
        Dictionary containing connection information
    """
    try:
        client = get_client()
        info = client.connection_info
        # Remove sensitive information
        safe_info = {
            "hostname": info.get("hostname"),
            "username": info.get("username"),
            "api_key_expires": info.get("api_key_expires"),
            "xplainable_version": info.get("xplainable_version"),
            "python_version": info.get("python_version"),
            "org_id": info.get("org_id"),
            "team_id": info.get("team_id"),
        }
        logger.info(f"Connection info retrieved for user: {safe_info.get('username')}")
        return safe_info
    except Exception as e:
        logger.error(f"Error getting connection info: {e}")
        raise


@mcp.tool()
def list_team_models(team_id_override: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List models for the current team or a provided team_id.
    
    Args:
        team_id_override: Optional team ID to override the default
        
    Returns:
        List of model information dictionaries
    """
    try:
        client = get_client()
        models = safe_client_call(
            client.models.list_team_models,
            "list_team_models",
            team_id=team_id_override
        )
        result = safe_model_dump_list(models, "list_team_models")
        logger.info(f"Listed {len(result)} models for team: {team_id_override or config.team_id}")
        return result
    except Exception as e:
        logger.error(f"Error listing team models: {e}")
        raise


@mcp.tool()
def get_model(model_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a model by id.
    
    Args:
        model_id: The model ID to retrieve
        
    Returns:
        Dictionary containing model information
    """
    try:
        client = get_client()
        info = client.models.get_model(model_id)
        result = safe_model_dump(info, "get_model")
        if result is None:
            raise ValueError(f"Model {model_id} not found")
        logger.info(f"Retrieved model info for: {model_id}")
        return result
    except Exception as e:
        logger.error(f"Error getting model {model_id}: {e}")
        raise


@mcp.tool()
def list_model_versions(model_id: str) -> List[Dict[str, Any]]:
    """
    List all versions for a model.
    
    Args:
        model_id: The model ID to list versions for
        
    Returns:
        List of version information dictionaries
    """
    try:
        client = get_client()
        versions = client.models.list_model_versions(model_id)
        result = safe_model_dump_list(versions, "list_model_versions")
        logger.info(f"Listed {len(result)} versions for model: {model_id}")
        return result
    except Exception as e:
        logger.error(f"Error listing model versions for {model_id}: {e}")
        raise


@mcp.tool()
def list_deployments(team_id_override: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List deployments for the team.
    
    Args:
        team_id_override: Optional team ID to override the default
        
    Returns:
        List of deployment information dictionaries
    """
    try:
        client = get_client()
        deployments = client.deployments.list_deployments(team_id=team_id_override)
        result = safe_model_dump_list(deployments, "list_deployments")
        logger.info(f"Listed {len(result)} deployments for team: {team_id_override or config.team_id}")
        return result
    except Exception as e:
        logger.error(f"Error listing deployments: {e}")
        raise


@mcp.tool()
def get_active_team_deploy_keys_count(team_id_override: Optional[str] = None) -> int:
    """
    Return the count of active deploy keys for a team.
    
    Args:
        team_id_override: Optional team ID to override the default
        
    Returns:
        Count of active deploy keys
    """
    try:
        client = get_client()
        count = client.deployments.get_active_team_deploy_keys_count(team_id=team_id_override)
        logger.info(f"Active deploy keys count for team {team_id_override or config.team_id}: {count}")
        return count
    except Exception as e:
        logger.error(f"Error getting deploy keys count: {e}")
        raise


@mcp.tool()
def list_preprocessors(team_id_override: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List preprocessors for the team.
    
    Args:
        team_id_override: Optional team ID to override the default
        
    Returns:
        List of preprocessor information dictionaries
    """
    try:
        client = get_client()
        results = client.preprocessing.list_preprocessors(team_id=team_id_override)
        result = safe_model_dump_list(results, "list_preprocessors")
        logger.info(f"Listed {len(result)} preprocessors for team: {team_id_override or config.team_id}")
        return result
    except Exception as e:
        logger.error(f"Error listing preprocessors: {e}")
        raise


@mcp.tool()
def get_preprocessor(preprocessor_id: str) -> Dict[str, Any]:
    """
    Get a preprocessor by id.
    
    Args:
        preprocessor_id: The preprocessor ID to retrieve
        
    Returns:
        Dictionary containing preprocessor information
    """
    try:
        client = get_client()
        info = client.preprocessing.get_preprocessor(preprocessor_id)
        result = safe_model_dump(info, "get_preprocessor")
        if result is None:
            raise ValueError(f"Preprocessor {preprocessor_id} not found")
        logger.info(f"Retrieved preprocessor: {preprocessor_id}")
        return result
    except Exception as e:
        logger.error(f"Error getting preprocessor {preprocessor_id}: {e}")
        raise


@mcp.tool()
def get_collection_scenarios(collection_id: str) -> List[Dict[str, Any]]:
    """
    List scenarios for a collection.
    
    Args:
        collection_id: The collection ID to list scenarios for
        
    Returns:
        List of scenario dictionaries
    """
    try:
        client = get_client()
        scenarios = client.collections.get_collection_scenarios(collection_id)
        # This endpoint likely returns plain dicts, so use safe_list_response
        result = safe_list_response(scenarios, "get_collection_scenarios")
        logger.info(f"Listed {len(result)} scenarios for collection: {collection_id}")
        return result
    except Exception as e:
        logger.error(f"Error getting collection scenarios for {collection_id}: {e}")
        raise


@mcp.tool()
def misc_get_version_info() -> Dict[str, Any]:
    """
    Return Xplainable client/server version info.
    
    Returns:
        Dictionary containing version information
    """
    try:
        client = get_client()
        info = client.misc.get_version_info()
        logger.info("Retrieved version information")
        return info.model_dump()
    except Exception as e:
        logger.error(f"Error getting version info: {e}")
        raise


# ============================================================================
# WRITE TOOLS (RESTRICTED)
# ============================================================================

if config.enable_write_tools:
    
    @mcp.tool()
    def generate_deploy_key(
        deployment_id: str, 
        description: str = "", 
        days_until_expiry: int = 90
    ) -> str:
        """
        Generate a deploy key for a deployment and return the UUID string.
        
        Args:
            deployment_id: The deployment ID
            description: Optional description for the key
            days_until_expiry: Days until the key expires (default: 90)
            
        Returns:
            UUID string of the generated deploy key
        """
        try:
            client = get_client()
            key = client.deployments.generate_deploy_key(
                deployment_id, 
                description, 
                days_until_expiry
            )
            logger.info(f"Generated deploy key for deployment: {deployment_id}")
            return str(key)
        except Exception as e:
            logger.error(f"Error generating deploy key for {deployment_id}: {e}")
            raise
    
    
    @mcp.tool()
    def activate_deployment(deployment_id: str) -> Dict[str, Any]:
        """
        Activate a deployment.
        
        Args:
            deployment_id: The deployment ID to activate
            
        Returns:
            Dictionary with activation result
        """
        try:
            client = get_client()
            result = client.deployments.activate_deployment(deployment_id)
            logger.info(f"Activated deployment: {deployment_id}")
            return result
        except Exception as e:
            logger.error(f"Error activating deployment {deployment_id}: {e}")
            raise
    
    
    @mcp.tool()
    def deactivate_deployment(deployment_id: str) -> Dict[str, Any]:
        """
        Deactivate a deployment.
        
        Args:
            deployment_id: The deployment ID to deactivate
            
        Returns:
            Dictionary with deactivation result
        """
        try:
            client = get_client()
            result = client.deployments.deactivate_deployment(deployment_id)
            logger.info(f"Deactivated deployment: {deployment_id}")
            return result
        except Exception as e:
            logger.error(f"Error deactivating deployment {deployment_id}: {e}")
            raise
    
    
    @mcp.tool()
    def gpt_generate_report(
        model_id: str,
        version_id: str,
        target_description: str = "text",
        project_objective: str = "text",
        max_features: int = 15,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate a GPT report for a model version.
        
        Args:
            model_id: The model ID
            version_id: The version ID
            target_description: Description of the target variable
            project_objective: Description of the project objective
            max_features: Maximum number of features to include
            temperature: GPT temperature parameter
            
        Returns:
            Dictionary containing the GPT report
        """
        try:
            client = get_client()
            resp = client.gpt.generate_report(
                model_id,
                version_id,
                target_description,
                project_objective,
                max_features,
                temperature
            )
            logger.info(f"Generated GPT report for model {model_id} version {version_id}")
            return resp.model_dump()
        except Exception as e:
            logger.error(f"Error generating GPT report: {e}")
            raise
    
    
    @mcp.tool()
    def get_deployment_payload(deployment_id: str) -> List[Dict[str, Any]]:
        """
        Get sample payload data for a deployment.
        
        Args:
            deployment_id: The deployment ID to get payload for
            
        Returns:
            List containing sample data dictionary for inference
        """
        try:
            client = get_client()
            payload = client.deployments.get_deployment_payload(deployment_id)
            logger.info(f"Retrieved deployment payload for: {deployment_id}")
            return payload
        except Exception as e:
            logger.error(f"Error getting deployment payload for {deployment_id}: {e}")
            raise


def main():
    """Main entry point for the server."""
    try:
        # Log startup information
        logger.info("Starting Xplainable MCP Server")
        logger.info(f"Write tools enabled: {config.enable_write_tools}")
        logger.info(f"Rate limiting enabled: {config.rate_limit_enabled}")
        
        # Initialize the client to verify connection
        client = get_client()
        logger.info("Successfully connected to Xplainable API")
        
        # Run the MCP server
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()