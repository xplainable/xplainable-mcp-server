# MCP Evals Framework — Design

**Date:** 2026-09-01
**Status:** Approved (brainstormed section-by-section)
**Goal:** Regression evals for the hosted/local MCP server as tools, models, and prompts change. Catch both hard failures (stage skipped, tool errored out) and silent semantic failures (trained on raw data, degenerate prescriptions) across the full analyst workflow.

## Decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Agent + eval stack | **pydantic-ai + pydantic-evals** | One ecosystem; step counts/traces free via OTel span-tree evaluators; MCP toolset support built in. mcp-use dropped — would add a second agent framework for no capability gain. |
| Target | **Parametrised; local in-process default** | Local = fast, free, deterministic auth (API key). Hosted (OAuth, mcp.xplainable.io) behind a flag for release verification. |
| Location | **`evals/` top-level in this repo** | Not shipped in the wheel; deps in `[project.optional-dependencies] evals` extra. Evals pin to the surface this repo deploys. |
| Test artifacts | **Dedicated "MCP Evals" platform team + harness-side teardown** | Deletion stays off the MCP surface (write surface is non-destructive). Harness tears down via xplainable-client delete methods directly. Avoids the Demo Team deployment quota (10/10). |

## Architecture

```
evals/
  run.py                 # entrypoint: cross-products RunConfig, writes result JSONs
  harness/
    runner.py            # pydantic-evals Dataset/Case wiring, k-repeat logic
    targets.py           # local (in-process, API key) / hosted (OAuth) MCP targets
    session.py           # artifact ledger + teardown via xplainable-client
  scenarios/             # scenario defs: prompt + dataset fixture + expected stages
  evaluators/            # stage evaluators + semantic detectors (span-tree based)
  prompts/               # named prompt variants (markdown, referenced by id)
  reporting/             # console/comparison tables, plots
  results/               # append-only run JSONs (gitignored)
```

**Per-case flow:** pydantic-evals task builds a pydantic-ai `Agent` with the MCP server as a toolset → agent runs the scenario prompt → OTel spans capture the tool-call sequence → evaluators score the span tree + platform state → session ledger records every created artifact (datasets, models, deployments, optimisers) and tears them down after scoring.

**Two LLM surfaces, deliberately separate:**
1. **Agent-under-test model** — harness-side, fully parametrised.
2. **Autotrain's internal LLM** — server-side env var, part of the system under test. NOT propagated through the harness. To eval a new autotrain model: redeploy autotrain; the run record's SHA/env stamp captures what was live.

## Scenarios and stage evaluators

A **scenario** = prompt + dataset fixture + declarative list of expected stages. Canonical stage enum:

`EXPLORE → SELECT_LABEL → DATA_PREP → FEATURE_ENG → PERSIST_PREP → TRAIN → DEPLOY → PREDICT → REPORT → OPTIMISE`

**Evaluators assert outcomes, not tool names** (surface contract tests already pin the tool list):
- `DATA_PREP`/`FEATURE_ENG`: preprocessor version exists with non-trivial spec.
- `TRAIN`: passes **only if engineered columns appear in the trained model's features** — the exact regression that motivated this initiative (agent trained raw; also the autotrain silent-failure #180/#181).
- `DEPLOY`: active deployment for the trained version.
- `PREDICT`: inline `inference_predict` returns probabilities for held-out rows.
- `REPORT`: a report URL is returned to the user.
- `OPTIMISE`: run on transformed data → `status: success` with prescriptions; run on raw data → structured `feature_not_found` error surfaced (loud-failure check).

**Semantic detectors** (named boolean flags, from the telco transcript's silent failures):
- Degenerate prescriptions — identical global optimum prescribed for all rows.
- `total_cost == 0` while costed levers were prescribed (cost-weight units mismatch).
- Immutable-feature drift — prescriptions changing Gender/tenure-like columns.
- Saturated probabilities — all outputs pinned at bounds.

**Scenario composition:** `telco_churn_full` (all stages) and `telco_churn_minimal` (train→deploy→predict) first; structured so new scenarios are a fixture + stage list.

## Metrics, scoring, comparison

**Per-case:** stage pass/fail; **step count** (total tool calls — transcript baseline: 33 incl. 3 wasted); **wasted calls** (errored calls, tracked separately — recovering from one structured error is fine, burning 5 guessing is drift); **semantic flags** (named booleans, not folded into one score).

**pass@k:** each (scenario × model × prompt) cell runs k times (default 3). Report per-stage pass rate (pinpoints where flakiness lives) and full-flow pass@k (≥1 run completed every stage cleanly).

**Persistence:** every run writes `evals/results/<timestamp>-<label>.json`: config (model, prompt id, target, k, git SHAs of mcp-server + xplainable-client), per-case metrics, span summaries. Append-only — comparisons never re-run old configs.

**Reporting:** pydantic-evals console table for the current run; a comparison table that loads N result JSONs and diffs stage pass rates / mean steps / semantic flags ("did the new client version regress" view). Plots (matplotlib, two only): stage pass-rate bars by config, step-count distributions.

## Parametrisation and CI

`RunConfig` (CLI flags or TOML):
- **model** — pydantic-ai model string (`anthropic:claude-sonnet-4-6`, `openai:gpt-5`, …). Unsupported providers via `litellm proxy` (OpenAI-compatible endpoint → `openai:<name>` + base_url) — litellm rotation without a harness dependency.
- **prompt** — id referencing `evals/prompts/*.md`.
- **target** — `local` (default) | `hosted`.
- **scenarios / k** — subset filter, repeat count.

`run.py` cross-products the axes; one result JSON per cell.

**CI:** `smoke` marker on 2-3 cheap cases (surface loads; one train-flow scenario k=1; one structured-error recovery) runs on PRs against the local target with a pinned model. Full matrix is manual/on-demand (costs money, needs the eval team's API key).

## Prerequisites

- Dedicated "MCP Evals" platform team + valid API key (current `.env` key is 401/expired).
- `evals/results/` gitignored.
