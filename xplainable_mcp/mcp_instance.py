"""
Shared MCP instance for the Xplainable MCP Server.

This module provides a single FastMCP instance that is shared across
all tool modules to ensure proper registration.
"""

import os
from fastmcp import FastMCP
from mcp.types import Icon
from . import __version__

# Auth is only configured when running in HTTP transport mode.
# In stdio mode (local dev), no auth is applied.
auth_provider = None

if os.getenv("MCP_TRANSPORT") == "streamable-http":
    auth0_domain = os.getenv("AUTH0_DOMAIN")
    auth0_client_id = os.getenv("AUTH0_CLIENT_ID")
    auth0_client_secret = os.getenv("AUTH0_CLIENT_SECRET")
    auth0_audience = os.getenv("AUTH0_AUDIENCE", "")
    mcp_server_url = os.getenv("MCP_SERVER_URL", "https://mcp.xplainable.io")

    if auth0_domain and auth0_client_id and auth0_client_secret:
        from fastmcp.server.auth.providers.auth0 import Auth0Provider

        auth_provider = Auth0Provider(
            config_url=f"https://{auth0_domain}/.well-known/openid-configuration",
            client_id=auth0_client_id,
            client_secret=auth0_client_secret,
            audience=auth0_audience,
            base_url=mcp_server_url,
            redirect_path="/auth/callback",
            require_authorization_consent="external",
        )

INSTRUCTIONS = """\
IMPORTANT: You MUST call select_team (or list_user_teams then set_active_team) \
as your very first action before calling any other tool. All tools require an \
active team to be set. If a tool returns 'No team selected', call select_team first.

## xplainable Best Practices

xplainable models are inherently explainable. Every decision must preserve this.

### Preprocessing Rules
- NEVER scale numeric columns (no StandardScaler, MinMaxScaler, RobustScaler, etc.). \
Feature contributions are expressed in original units — scaling destroys interpretability. \
The model handles raw values natively.
- NEVER use OrdinalEncoder on nominal categories. xplainable handles categories natively.
- DO: drop IDs/irrelevant columns, fill missing values (median/mode), extract datetime \
components, condense high-cardinality categoricals (>15 unique → CategoryCondenseTransformer).

### Training Rules
- Start with default hyperparameters (max_depth=8). Look at train vs test metrics before adjusting.
- Use `train_model()` for initial training. Use `refit_model()` for instant hyperparameter \
iteration -- everything happens server-side in one API call.
- Only `train_model()` when changing features or preprocessing. Use `refit_model()` for \
everything else.
- Use `feature_params` to tune multiple features with different settings in ONE refit call. \
This avoids repeated data loads. Tune numeric features with max_depth/min_leaf_size. \
Tune categorical features with weight/tail_sensitivity (depth has little effect on categoricals).

### Evaluation Rules
- Compare train vs test metrics. Gap >5-8% = overfitting. Reduce max_depth or increase min_leaf_size.
- Goal: minimise splits while maintaining AUC. Fewer splits = less overfitting = more explainable.
- Primary metric: AUC for classifiers, R2 for regressors. Accuracy is misleading with imbalanced classes.
- Any single feature >40% importance = investigate for data leakage.
- Present feature contributions in original units, not scaled values.

### Available Skills
Pin a skill resource to your project for domain-specific workflow guidance. \
Available skills can be discovered via the MCP resources panel.
"""

# Initialize the shared FastMCP server instance
mcp = FastMCP(
    name="Xplainable",
    version=__version__,
    auth=auth_provider,
    website_url="https://xplainable.io",
    icons=[
        Icon(
            src="https://xplainable.io/assets/xplainable-icon.png",
            mimeType="image/png",
        ),
    ],
    instructions=INSTRUCTIONS,
)

# Register bundled skills as MCP resources
from .skills import register_skill_resources
register_skill_resources(mcp)
