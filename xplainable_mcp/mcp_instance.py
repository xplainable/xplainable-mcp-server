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


def _truthy(env_value: Optional[str]) -> bool:
    return (env_value or "").strip().lower() in ("1", "true", "yes")


def resolve_include_tags(advanced: Optional[str], guided: Optional[str]) -> Optional[set]:
    """Resolve FastMCP include_tags for the three-tier tool surface.

    - default: direct mode — curated tools only (~33)
    - XPLAINABLE_GUIDED_TOOLS truthy: adds the guided agentic trio (~36)
    - XPLAINABLE_ADVANCED_TOOLS truthy: no filtering — full surface (~105)

    Note: "workflow" must never be in the default set — the guided trio
    keeps its "workflow" category tag, so including it would leak the
    trio back into the direct surface.
    """
    if _truthy(advanced):
        return None  # advanced: full surface
    if _truthy(guided):
        return {"curated", "guided"}
    return {"curated"}


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
Xplainable trains inherently explainable ML models server-side. You are the \
orchestrator: analyse the data, decide the preprocessing and features, \
train, inspect, and iterate. Compute always runs on the Xplainable \
platform — never train locally.

If a tool returns 'No team selected', an active team must be set first \
(select_team / set_active_team, or the XPLAINABLE_TEAM_ID environment \
variable).

## The Iterate Loop

1. `workflow_list_assets` — see the team's datasets, models, and deployments.
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
`workflow_explain_model` for the importance/profile digest.
6. Iterate:
   - Hyperparameter tuning → `models_refit_model` (cheap, same structure).
   - Different features / preprocessing / target → `models_train_model` again.
   Narrate what you changed and why; show the user the metric movement.
7. `workflow_deploy_model(model_id)` — deploy once satisfied.
8. Act on the model:
   - `workflow_predict` — score rows (no deployment needed).
   - `workflow_optimise_model` — prescriptive optimisation toward an objective.
   - `workflow_create_report` — starts report generation and returns a \
job_id; poll `reports_get_job_status(job_id)` until status is 'done' \
(or 'error').

Read tools (datasets_*, models_*, deployments_*, optimisers_*, runs_*, \
agentic_*, misc_get_organisation_usage) are available for inspecting \
assets at any point.

## Guided Mode (opt-in)

Set `XPLAINABLE_GUIDED_TOOLS=1` to expose workflow_train_model / \
workflow_wait_for_update / workflow_decide: a hands-off run of the same \
agentic pipeline that powers the Xplainable platform UI. Prefer the direct \
loop above when available — it keeps you in control of every decision.

## Advanced Tool Surface

Set `XPLAINABLE_ADVANCED_TOOLS=1` to expose the full surface (~105 tools) \
including write/admin tools for monitors, GPT reports, inference, and \
low-level agentic run control.

## Available Skills

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
    include_tags=resolve_include_tags(
        os.getenv("XPLAINABLE_ADVANCED_TOOLS"),
        os.getenv("XPLAINABLE_GUIDED_TOOLS"),
    ),
)

# Register bundled skills as MCP resources
from .skills import register_skill_resources
register_skill_resources(mcp)
