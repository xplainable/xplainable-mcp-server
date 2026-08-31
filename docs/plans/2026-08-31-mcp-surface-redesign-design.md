# MCP Tool-Surface Redesign — Design

**Date:** 2026-08-31
**Status:** Approved (brainstormed + validated section-by-section)
**Repos:** xplainable-client, xplainable-mcp-server

## Problem

The current surface wraps the ML process into workflow rails (9 `workflow_*`
tools + 3-tier tag filtering + `_coach` guidance). Result: agent capability
regression — "it used to flow nicely through the process even with all the
tools, now it's hit and miss (doesn't dataprep/feature engineer anymore)."

Diagnosis: **the tool list is the affordance.** Hiding preprocessing tools
behind a promotion set deleted the standing suggestion to do data prep. The
workflow step ordering defines "the process" and data prep isn't a step.
Deep cause: two granularities fighting (1:1 SDK-method tools vs workflow
composites) instead of one task-level surface.

No external consumers — only team testing against hosted MCP. Free to break
everything.

## Decision: one flat surface, client-owned

- **~36 task-level tools**, all always visible. No tiers, no env vars, no
  server-side overlays. The `@mcp_tool` decorator in xplainable-client is
  the *entire* curation mechanism: decorated = exposed.
- Primitives where the agent orchestrates; composites only where atomicity
  is genuinely needed. `models.train_model` is already the right composite
  (synchronous server-side train with `preprocessor_version_id`,
  `drop_columns`, etc.) — the agentic HITL run machinery goes.
- Guidance moves to **failure time, in-band**: the structured-error
  `suggestion` field (shipped 2026-08-31, client 1.14.0) replaces `_coach`.
  Docstrings carry the affordance at browse time.
- Category collapses to **read | write**, mapped to MCP
  `readOnlyHint`/`destructiveHint` annotations.
- Accepted trade: surface changes require a client release + pin bump.

## The tool list (36)

| Stage | Tools |
|---|---|
| Data (5) | list_team_datasets, get_dataset_info, preview_dataset_json, upload_dataset, summarize_by_dataset_id |
| Preprocessing (7) | list_available_transformers, list_preprocessors, get_preprocessor, create_preprocessor_from_spec, preview_from_data, add_version_from_spec, check_signature |
| Training (6) | train_model (models client, sync), refit_model, list_team_models, list_model_versions, get_model, link_preprocessor |
| Evaluation (4) | get_model_evaluation, get_model_profile, get_feature_info, explain_model (GPT) |
| Deployment (6) | deploy, list_deployments, activate_deployment, deactivate_deployment, generate_deploy_key, get_deployment_payload |
| Inference (1) | predict |
| Optimisation (4) | list_optimisers, create_optimiser, create_optimiser_version, run_optimiser |
| Reporting (2) | create_report, get_job_status |
| Admin (1) | ping_gateway |

Plus 4 server-native (mcp-server repo): list_user_teams, set_active_team,
select_team stay; `workflow_get_run_charts`, `get_workflows`, `list_tools`
are deleted (agentic machinery / rails docs / redundant with MCP protocol).

**Cut:** the whole workflow.py client (train_model, wait_for_update, decide,
list_assets, deploy_model, optimise_model, explain_model wrapper, predict
wrapper, create_report wrapper, get_run_charts); agentic primitives
(start_run, get_run_state, get_phases, get_pending_decision,
submit_decision, send_chat, skip_phase, retrain, cancel_run); all 14
monitor tools (no agent use case yet); load_dataset / load_classifier /
load_regressor (return Python objects/DataFrames); stream_predictions;
delete_* destructive tools; misc reads (version info, deploy-key counts,
run reads); create_report_sync; ReportsClient.available_widgets;
health_check / ping_server (ping_gateway covers it).

## What gets deleted vs kept

**xplainable-client:**
- `mcp_markers.py`: decorator simplifies to `mcp_tool(category)` with
  category ∈ {read, write}. Delete `step`, `depends_on`, `curated`,
  MCPCategory's other members, and the dead codegen
  (`generate_mcp_tool_code`, `export_mcp_tools_to_file`,
  `scan_client_for_mcp_tools`, `_format_type_hint`).
- Delete `workflow.py` entirely (incl. `_coach`).
- Re-tag: only the 36 tools above carry `@mcp_tool`; strip it everywhere
  else.

**xplainable-mcp-server:**
- `mcp_instance.py`: delete `resolve_include_tags` + both env vars; no
  include_tags filtering.
- `runtime_tools.py`: delete `GUIDED_TOOLS`, `CURATED_PROMOTIONS`,
  `compute_tags` overlay logic. **Keep** runtime generation from the
  registry, the thread-offload wrapper, and structured-error → ToolError
  (`[CODE] msg — Suggestion: …`) surfacing. Add
  readOnlyHint/destructiveHint from category.
- `server.py`: delete `workflow_get_run_charts`, `get_workflows`,
  `list_tools`; keep the 3 team tools.

## Testing

- Client: registry test asserting the exact 36-tool surface (name +
  category) — the surface becomes an explicit, versioned contract.
- MCP server: update unit tests for tag/tier removal; tool-count and
  annotation assertions.
- Follow-up (separate conversation): regression evals with mcp-use +
  pydantic-eval against this new surface.
