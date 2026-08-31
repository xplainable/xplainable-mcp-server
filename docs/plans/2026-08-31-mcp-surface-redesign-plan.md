# MCP Surface Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Replace the 3-tier workflow-wrapped MCP surface with one flat, client-owned surface of 36 task-level tools.

**Architecture:** The `@mcp_tool(category)` decorator in xplainable-client becomes the entire curation mechanism (category ∈ {read, write} → MCP readOnlyHint/destructiveHint). The mcp-server keeps runtime generation + thread-offload + structured-error surfacing, and loses all tier/tag/overlay logic. See `2026-08-31-mcp-surface-redesign-design.md` for the approved design and full rationale.

**Tech Stack:** Python; client repo (`/Users/jtuppack/projects/xplainable-client`, venv `.venv`, py3.11, flow feature→main); mcp repo (`/Users/jtuppack/projects/xplainable-mcp-server`, venv `xplainable-mcp-env`, py3.13, fastmcp 2.14.7, flow feature→main).

**Branches:** `feat/flat-surface` off `main` in BOTH repos. mcp-server tests run against the local client: `pip install -e ../xplainable-client` into `xplainable-mcp-env` (remember the pin bump to the released client happens at ship time, not in this plan).

---

## The 36-tool contract (single source of truth for Tasks 2–4)

Per client file — **keep** (with new category) / **strip decorator** (method stays, decorator goes):

| File | Keep as `read` | Keep as `write` | Strip |
|---|---|---|---|
| agentic.py | — | — | all 9 (get_pending_decision, get_phases, get_run_state, cancel_run, retrain, send_chat, skip_phase, start_run, submit_decision) |
| autotrain.py | summarize_by_dataset_id | — | — |
| datasets.py | list_team_datasets, get_dataset_info, preview_dataset_json | upload_dataset | list_datasets, load_dataset, delete_dataset |
| deployments.py | list_deployments, get_deployment_payload | deploy, activate_deployment, deactivate_deployment, generate_deploy_key | get_active_team_deploy_keys_count, list_deploy_keys, delete_deployment, revoke_deploy_key |
| misc.py | ping_gateway | — | health_check, ping_server, get_model_info, get_organisation_usage, get_version_info, load_classifier, load_regressor |
| models.py | list_team_models, list_model_versions, get_model, get_model_evaluation, get_model_profile, get_feature_info | train_model, refit_model, link_preprocessor | list_model_version_partitions |
| monitors.py | — | — | all 14 |
| optimisers.py | list_optimisers | run_optimiser, create_optimiser, create_optimiser_version | get_optimiser_run, get_optimiser_version, list_optimiser_versions, delete_optimiser, delete_optimiser_version |
| preprocessing.py | list_available_transformers, list_preprocessors, get_preprocessor, preview_from_data, check_signature | create_preprocessor_from_spec, add_version_from_spec | get_version, fit_version_from_data, delete_preprocessor, delete_version, update_version_from_spec |
| reports.py | get_job_status | create_report | available_widgets, create_report_sync |
| runs.py | — | — | get_run, create_run |
| gpt.py | explain_model | — | generate_documentation, generate_report |
| inference.py | predict | — | stream_predictions |
| workflow.py | — | — | **delete the whole file** |

Totals: 22 read + 14 write = 36.

---

### Task 1: Client — simplify mcp_markers.py

**Files:**
- Modify: `xplainable_client/client/utils/mcp_markers.py`
- Test: `tests/` (find existing marker tests via `grep -rl mcp_markers tests/`)

Branch first: `cd /Users/jtuppack/projects/xplainable-client && git checkout main && git pull && git checkout -b feat/flat-surface`

**Step 1:** Write failing test `tests/test_mcp_registry.py::test_decorator_minimal_metadata`: decorate a dummy function with `@mcp_tool(category=MCPCategory.READ)`, assert registry entry has `category`, `function`, `signature`, `docstring`, `parameters` and does NOT have `step`/`depends_on`/`curated` keys. Assert `MCPCategory` has exactly READ and WRITE members. Run: `.venv/bin/python -m pytest tests/test_mcp_registry.py -q` → FAIL.

**Step 2:** Implement: `MCPCategory` → only `READ = "read"` / `WRITE = "write"`; `mcp_tool(category)` drops `step`, `depends_on`, `curated` params and registry keys; delete `generate_mcp_tool_code`, `export_mcp_tools_to_file`, `scan_client_for_mcp_tools`, `_format_type_hint` (dead codegen). NOTE: this temporarily breaks every existing decorator call site — expected until Tasks 2–3.

**Step 3:** Run the new test file only (full suite broken until Task 3) → PASS. Commit: `feat: collapse mcp_tool decorator to category-only (read/write)`.

### Task 2: Client — delete workflow.py and unwire it

**Files:**
- Delete: `xplainable_client/client/workflow.py`
- Modify: `xplainable_client/client/client.py` (remove WorkflowClient import/instantiation/property)
- Check: `grep -rn "workflow" xplainable_client/ tests/ --include='*.py' -il` — remove/update every reference (tests of workflow client get deleted)

**Steps:** grep for references → delete file → unwire client.py → delete workflow tests → commit `feat: remove workflow client (rails replaced by flat primitive surface)`.

### Task 3: Client — re-tag every module per the contract table

**Files:** the 13 client modules in the table.

**Steps:** For each file: update kept decorators to `@mcp_tool(category=MCPCategory.READ)` or `WRITE` (removing step/depends_on/curated args), remove decorator lines (and now-unused imports) from stripped methods. Method bodies untouched. Then verify import works: `.venv/bin/python -c "import xplainable_client.client.client"`. Commit: `feat: re-tag client surface to 36 flat task-level tools`.

### Task 4: Client — surface contract test

**Files:**
- Create/extend: `tests/test_mcp_registry.py`

**Step 1:** Write `test_surface_is_exactly_36_tools`: import `xplainable_client.client.client`, build `{short_name: category}` from `_MCP_REGISTRY`, assert equality against the literal 36-entry dict from the table (this is the versioned contract — a failure here means the surface changed). Run → PASS (if FAIL, fix Task 3 tagging, not the test).

**Step 2:** Full suite: `.venv/bin/python -m pytest tests/ -q`. Fix any fallout (imports of deleted functions, workflow references). Commit: `test: pin the 36-tool MCP surface contract`.

### Task 5: MCP server — delete tier logic

**Files:**
- Modify: `xplainable_mcp/mcp_instance.py` (delete `resolve_include_tags`, `XPLAINABLE_ADVANCED_TOOLS`/`XPLAINABLE_GUIDED_TOOLS` reads, any `include_tags=` passed to FastMCP)
- Test: existing tests referencing tiers (`grep -rn "include_tags\|ADVANCED_TOOLS\|GUIDED_TOOLS" tests/ xplainable_mcp/`)

Branch first: `cd /Users/jtuppack/projects/xplainable-mcp-server && git checkout main && git pull && git checkout -b feat/flat-surface`. Then `xplainable-mcp-env/bin/pip install -e ../xplainable-client` (or the env's actual pip path — verify with `which python` inside the env).

**Steps:** TDD — update/delete tier tests first, implement, run mcp test suite. Commit: `feat: remove 3-tier tag filtering — one flat surface`.

### Task 6: MCP server — runtime_tools.py overlays out, annotations in

**Files:**
- Modify: `xplainable_mcp/runtime_tools.py`

**Steps:**
1. Failing test: registered tool built from a `read` registry entry carries `readOnlyHint=True`; `write` carries `destructiveHint=True` (fastmcp `ToolAnnotations`); no tool has `curated`/`workflow` tags.
2. Implement: delete `GUIDED_TOOLS`, `CURATED_PROMOTIONS`, `compute_tags` overlay logic; map category → annotations at registration. KEEP `_build_wrapper` (thread offload + `[CODE] msg — Suggestion: …` ToolError formatting) untouched.
3. Run suite → PASS. Commit: `feat: category-driven MCP annotations, overlays removed`.

### Task 7: MCP server — server.py cleanup

**Files:**
- Modify: `xplainable_mcp/server.py`

**Steps:** delete `workflow_get_run_charts`, `get_workflows`, `list_tools` (and helpers only they use, e.g. `_first_doc_line` if unreferenced); keep `list_user_teams`/`set_active_team`/`select_team`, simplifying their tags (plain `{"admin"}` or none — tags no longer filter). Check skills/resources for references to deleted tools (`grep -rn "get_workflows\|get_run_charts\|list_tools" xplainable_mcp/`). Update tests. Commit: `feat: drop workflow chart/docs/introspection tools`.

### Task 8: Integration verification

**Steps:**
1. Full mcp suite: `pytest` in `xplainable-mcp-env` → all pass.
2. Boot check: start the server locally (env vars from `.env`/README), list tools via fastmcp client or `python -c` harness → assert exactly 36 + 3 team tools = 39, spot-check annotations and that `preprocessing_*` tools are visible.
3. Full client suite again (guard against cross-task drift).
4. Commit any test-harness additions.

### Task 9: Final review

Dispatch final code reviewer over both branches (`git diff main...feat/flat-surface` in each repo). Then superpowers:finishing-a-development-branch — note ship order: client PR/merge → PyPI release (1.15.0) → mcp pin bump, same sequencing as the 1.14.0 roll (wait a few minutes after publish before pin-bump push to dodge the PyPI propagation race).
