"""
Shared MCP instance for the Xplainable MCP Server.

This module provides a single FastMCP instance that is shared across
all tool modules to ensure proper registration.
"""

import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from mcp.types import Icon
from . import __version__
from .branding import XPLAINABLE_ICON_URL, apply_consent_branding

load_dotenv()

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
        apply_consent_branding()

INSTRUCTIONS = """\
Xplainable trains inherently explainable ML models server-side. You are the \
orchestrator: analyse the data, decide the preprocessing and features, \
train, inspect, and iterate. Compute always runs on the Xplainable \
platform — never train locally.

If a tool returns 'No team selected', an active team must be set first \
(select_team / set_active_team, or the XPLAINABLE_TEAM_ID environment \
variable).

## The Iterate Loop

1. `datasets_list_team_datasets` / `models_list_team_models` / \
`deployments_list_deployments` — see the team's assets.
2. `datasets_preview_dataset_json(dataset_id)` — inspect columns, types, \
and sample rows. Decide the target column, columns to drop (IDs, leakage), \
and whether preprocessing is needed.
3. (Optional) preprocessing: `preprocessing_list_available_transformers` → \
`preprocessing_create_preprocessor_from_spec(name, spec, sample_data)` → \
`preprocessing_preview_from_data(version_id, sample_data)` to verify the \
transformed output before training.
4. `models_train_model(dataset_id, target_column, model_name, ...)` — \
synchronous server-side training (may take up to a couple of minutes). \
Returns model_id, version_id, train/test metrics, and feature importances.
5. Inspect: compare train vs test metrics (a large gap = overfitting). Use \
`models_get_feature_info(version_id)` for feature health and \
`gpt_explain_model` for the importance/profile digest.
6. Iterate:
   - Hyperparameter tuning → `models_refit_model` (cheap, same structure).
   - Different features / preprocessing / target → `models_train_model` again.
   Narrate what you changed and why; show the user the metric movement.
7. `deployments_deploy(version_id)` — deploy once satisfied (then \
`deployments_activate_deployment`).
8. Act on the model:
   - `inference_predict` — score rows against a deployment.
   - `optimisers_run_optimiser` — prescriptive optimisation toward an \
objective (create one first via `optimisers_create_optimiser`).
   - `reports_create_report` — starts report generation and returns a \
job_id; poll `reports_get_job_status(job_id)` until status is 'done' \
(or 'error').

Read tools (datasets_*, models_*, deployments_*, optimisers_*, \
preprocessing_*) are available for inspecting assets at any point.

## Available Skills

Pin a skill resource to your project for domain-specific workflow guidance. \
Available skills can be discovered via the MCP resources panel.
"""

# Initialize the shared FastMCP server instance
mcp = FastMCP(
    name="Xplainable",
    version=__version__,
    auth=auth_provider,
    website_url="https://www.xplainable.io",
    icons=[
        Icon(
            src=XPLAINABLE_ICON_URL,
            mimeType="image/svg+xml",
        ),
    ],
    instructions=INSTRUCTIONS,
)

# Register bundled skills as MCP resources
from .skills import register_skill_resources
register_skill_resources(mcp)
