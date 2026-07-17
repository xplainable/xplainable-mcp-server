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
Xplainable trains inherently explainable ML models server-side. Everything \
you need for the end-to-end journey is covered by the workflow_* tools — \
prefer them over any other tool.

If a tool returns 'No team selected', an active team must be set first \
(select_team / set_active_team, or the XPLAINABLE_TEAM_ID environment \
variable).

## The Workflow Loop

1. `workflow_list_assets` — see the team's datasets, models, and \
deployments. Find the dataset to model (or confirm a model already exists).
2. `workflow_train_model(dataset_id, goal, model_name)` — starts a \
server-side agentic training run and returns a run_id.
3. Loop: `workflow_wait_for_update(run_id, since_event, timeout)` — \
long-polls the run and returns new events. Narrate progress to the user as \
events arrive. If it reports a pending_decision, relay the question and \
options to the user, then submit their answer with \
`workflow_decide(run_id, approve=... | choice=... | custom=...)`. The run \
pauses at exactly two gates: label selection and training approval. Repeat \
until the run completes (typically ~10 minutes end-to-end).
4. `workflow_deploy_model(model_id)` — deploys the trained model after \
the run completes (deployment is a separate call, not a gate in the run).
5. Act on the model:
   - `workflow_optimise_model` — prescriptive optimisation toward an objective.
   - `workflow_predict` — score rows with the trained model (no \
deployment needed).
   - `workflow_explain_model` — feature-importance and profile digest.
   - `workflow_create_report` — generate a shareable platform report.

Read-oriented tools (datasets_*, models_*, deployments_*, optimisers_*, \
runs_*, agentic_*) are available for inspecting assets in more detail \
between workflow steps.

## Advanced Tool Surface

By default this server exposes the curated workflow surface (28 tools). \
Set the environment variable `XPLAINABLE_ADVANCED_TOOLS` to `1`, `true`, or \
`yes` to expose the full surface (~104 tools) including write/admin tools \
for preprocessing, monitors, GPT reports, inference, and low-level agentic \
run control.

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
    include_tags=resolve_include_tags(os.getenv("XPLAINABLE_ADVANCED_TOOLS")),
)

# Register bundled skills as MCP resources
from .skills import register_skill_resources
register_skill_resources(mcp)
