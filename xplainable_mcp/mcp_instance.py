"""
Shared MCP instance for the Xplainable MCP Server.

This module provides a single FastMCP instance that is shared across
all tool modules to ensure proper registration.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from fastmcp import FastMCP
from mcp.types import Icon
from . import __version__

load_dotenv()


def resolve_include_tags(env_value: Optional[str]) -> Optional[set]:
    """Resolve FastMCP include_tags from XPLAINABLE_ADVANCED_TOOLS.

    Truthy values ("1", "true", "yes") disable tag filtering (return None)
    so the full tool surface is registered. Anything else restricts the
    server to the curated surface: tools tagged "workflow" or "curated".
    """
    if (env_value or "").strip().lower() in ("1", "true", "yes"):
        return None  # advanced: full surface
    return {"workflow", "curated"}


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

## Primary Training Workflow (XGM v2)

Model training runs server-side on Xplainable's agentic pipeline — never \
train locally unless explicitly asked to use the legacy v1 path.

1. Upload the dataset (datasets tools), then summarize it to obtain a run_id.
2. `agentic_start_run(model_name=..., run_id=...)` — defaults to \
algorithm="xgm" (v2) and auto_mode=True.
3. Poll `agentic_get_run_state(run_id)` until status is 'completed' \
(runs take ~10 minutes; if 'waiting_input', answer via \
`agentic_get_pending_decision` + `agentic_submit_decision`).
4. Optionally create and run prescriptive optimisers (optimisers tools: \
create policy -> create version -> run).
5. Deploy and test inference (deployments tools).

Legacy v1 (`models_train_model`, `models_refit_model`) trains locally in \
the MCP host and remains available for the opensource workflow; the rules \
below apply mainly to that path.

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
    include_tags=resolve_include_tags(os.getenv("XPLAINABLE_ADVANCED_TOOLS")),
)

# Register bundled skills as MCP resources
from .skills import register_skill_resources
register_skill_resources(mcp)
