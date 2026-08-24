# Design: Server-Side Training Primitive & Workflow Decomposition

## Context

The MCP server currently funnels training through the 9 `workflow_*` tools (client v1.8.0 workflow layer, synced at `1f4f620`). Three of those tools — `train_model`, `wait_for_update`, `decide` — delegate orchestration to the server-side agentic pipeline, reducing Claude to a relay: start run → poll → forward pending decisions → poll. As models get smarter this is a ceiling: Claude cannot reorder, skip, or iterate between steps.

Two constraints frame this design:

1. **Non-negotiable:** training executes server-side (autotrain has the `xplainable_gm` deps), never locally in the MCP host.
2. **The agentic pipeline stays as-is** — it is the primary engine behind the platform web UI.

The insight: the pipeline conflates *where compute runs* with *who decides what happens next*. We decompose by extracting a training primitive both orchestrators (the web UI's pipeline agent, and Claude) can call. This is the server-side twin of the original `feat/mcp-workflow-design` doc (May 2026, `3a7c2c4`), which proposed granular tools but local training.

## Part 1: The training primitive

**New endpoint — `POST /v1/models/v2/train`.** API proxies to autotrain (same pattern as the agentic proxy routes in `api/src/endpoints/api_endpoints/agentic.py`); the fit executes in autotrain.

Request:

```json
{
  "dataset_id": "...",
  "target_column": "churn",
  "model_name": "Telco Churn",
  "model_description": "",
  "feature_columns": null,
  "drop_columns": ["customer_id"],
  "preprocessor_version_id": null,
  "params": {"max_depth": 8, "min_info_gain": 0.0001},
  "test_size": 0.2,
  "seed": 42
}
```

Response (synchronous, generous timeout — precedent: `refit_model`; XGM fits in seconds-to-a-minute):

```json
{
  "model_id": "...", "version_id": "...", "run_id": "...",
  "train_metrics": {}, "test_metrics": {},
  "feature_importances": [],
  "n_train": 5600, "n_test": 1400
}
```

Internally: load dataset by ID (reuse the existing staging loader, no run state machine), apply fitted preprocessor if given, drop/filter columns, split, fit via the shared training core, persist via the existing `POST /models/v2/create` callback (auto-creates `run_id`, so charts/reports keep working).

Sync-only for now; no async job variant until a dataset proves too big (YAGNI).

Combined with existing `refit_model`, Claude gets both loops: **cheap param iteration** (refit) and **structural iteration** (retrain with different features/preprocessing).

## Part 2: One training core, two orchestrators (xplainable-autotrain)

Extract a service-level function — `app/services/train/core.py::train_v2(frame, target, params, ...) -> TrainResult` — out of the current split across `model_tools.py::auto_train_v2_tool()` and `Manager.auto_train_v2()` (manager.py:974). Pure compute: prepared DataFrame + config in, blob + artifacts out. No Redis, no run state, no LLM calls.

Also extract `prepare_training_frame()` (load → preprocess → filter features → drop high-cardinality) from the `MODEL_TRAINING` handler (`model_training.py:117-290`), since the endpoint needs identical logic.

Two callers:

1. The new `/train` endpoint.
2. The pipeline's `MODEL_TRAINING` handler — keeps its decision-card/approval logic, delegates frame prep + fitting to the shared core.

Guarantee: a model trained by Claude via MCP and one trained through the web UI pipeline are bit-identical for the same inputs. The pipeline itself (phases, gates, chat, SSE, Redis state, crash-safe resume) is untouched — this is an extraction, not a rewrite.

## Part 3: Client + MCP surface

**Client:** add `models.train_model(...)` with `@mcp_tool(category=WRITE, curated=True)`. Central source of truth preserved — the sync picks it up.

**Fate of `workflow_*` tools:** only the agentic trio (`train_model`, `wait_for_update`, `decide`) embody the second-agent problem. The other six (`deploy_model`, `optimise_model`, `explain_model`, `predict`, `create_report`, `list_assets`) are mechanical compounds — idempotent ladders and digests that take no judgment away from Claude. Keep them; the rollup was right there.

Curated surface becomes two explicit modes:

- **Direct mode (new primary):** `list_assets` → dataset preview → preprocessing tools (promote `preprocessing_create_preprocessor_from_spec` + preview to curated; currently 0/12 curated) → `train_model` → profile/feature-info/evaluation reads → `refit_model` → `workflow_deploy_model` → optimise/predict/report.
- **Guided mode (kept, demoted):** the agentic trio, re-documented as "hands-off: runs the same pipeline that powers the platform UI".

**Prompt engineering:** rewrite server `INSTRUCTIONS` (mcp_instance.py) around the iteration loop — *analyze → preprocess → train → inspect train/test gap → refit or restructure → deploy* — instead of the polling loop. The bundled skills (`xplainable-best-practices.md`, etc.) already teach this loop and get reconnected to a surface that can execute it.

Curated count: ~28 → ~34.

## Part 4: Technical debt cleanup

In scope for this project:

1. **MCP sync codegen fragility (highest value).** Repeated corruption (`7aef6de`, `ee9d7c0`, `95378fd`); live drift (server 101 tools vs client registry 93). Replace checked-in generated files with **runtime tool generation from the `@mcp_tool` registry** — introspect the installed client, register FastMCP tools dynamically. Kills the corruption class and drift; the sync PR becomes a version bump.
2. **Client-side blocking loops.** `create_report` (300s poll) returns a `job_id` + curated `get_job_status` read instead. `wait_for_update` keeps polling — that is its purpose in guided mode.

Small opportunistic fixes:

3. **Gate-config duplication:** `BIG_THREE_GATES` (client) vs `DEFAULT_REQUIRE_APPROVAL` (autotrain, 7 phases). Server default becomes authoritative; client passes overrides only.
4. **Hardcoded inference URL** (`workflow.py:33`, prod-only) — derive from session config.
5. **Status vocabulary:** API `"done"` vs workflow-masked `"completed"` — standardise at the API.

Deferred (tracking notes only): dual proxy prefixes (`/v1/agentic` vs `/v1/autotrain/agentic`), magic-name optimiser reuse (`workflow_optimise_model`), v1 legacy training path removal.

## Part 5: Rollout & verification

Sequencing (each independently shippable, `feature → main`):

1. **autotrain:** extract `train_v2()` + `prepare_training_frame()`; handler delegates. Verify existing pipeline E2E trains identically.
2. **autotrain:** add `/train` endpoint on the shared core.
3. **api:** proxy route `POST /v1/models/v2/train` with auth.
4. **client:** `models.train_model()` (curated), `create_report` job split, gate-config cleanup, inference URL fix. Version bump.
5. **mcp-server:** runtime tool generation, curated surface changes, INSTRUCTIONS + skills rewrite.

Verification gates:

- **Parity:** same dataset via web UI pipeline and via `/train` → identical model blob/metrics.
- **E2E via MCP only:** telco-churn rerun, server-side — preprocess → train → inspect gap → refit → deploy → predict → report, driven from Claude Desktop with the churn skill.
- **Regression:** full web UI agentic run with gates still works.
- **Surface check:** default curated ~34; advanced surface unchanged.

Success measure: a user with a CSV and a sentence of intent gets a trained, deployed, explained model with Claude visibly reasoning through each decision — no black box, no local compute.
