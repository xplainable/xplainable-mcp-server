# MCP server evals

Regression evals for the MCP server's 42-tool surface. An LLM agent
(pydantic-ai) drives end-to-end ML flows — upload data, preprocess, train,
deploy, predict — through the MCP tools, and each run is scored with
pydantic-evals: stage assertions (did the expected stages happen), semantic
detectors (did known failure modes fire), and efficiency metrics.

## Setup

In the server environment:

```bash
pip install -e '.[evals]'
```

Create `evals/.env`:

```
XPLAINABLE_API_KEY=...     # key for the eval team
XPLAINABLE_TEAM_ID=...     # dedicated "MCP Evals" team
ANTHROPIC_API_KEY=...      # or creds for whichever --model you use
```

**Use a dedicated eval team.** Evals create AND DELETE datasets, models,
deployments, and reports. Never point `XPLAINABLE_TEAM_ID` at a team you
work in.

## Running

```bash
python -m evals.run --scenario telco_churn_minimal -k 1 --label first-live
```

Config axes:

- `--model` — pydantic-ai model id, repeatable (default `anthropic:claude-sonnet-4-6`)
- `--prompt` — prompt id, repeatable; prompts live in `evals/prompts/*.md`
  (prompt_id = filename stem, default `default`)
- `--target` — `local` (in-process server) or `hosted` (mcp.xplainable.io)
- `--scenario` — repeatable, default all; `-k` — repeats per scenario (default 3)
- `--label` — result filename prefix

`--model` x `--prompt` forms a cross-product; each cell runs serially and
writes one results JSON to `evals/results/`
(`{label}_{model}_{prompt}_{timestamp}.json`).

## Results format

```json
{
  "label": "first-live",
  "timestamp": "...",
  "config": {"model": "...", "prompt_id": "...", "target": "local", "k": 1},
  "git": {"mcp_server": "<sha>", "xplainable_client": "<version>"},
  "cases": [
    {"name": "telco_churn_minimal[0]",
     "assertions": {"train": true, "...": true},
     "scores": {"step_count": 12, "wasted_calls": 0},
     "labels": {},
     "duration": 84.2,
     "error": null,
     "usage_limit_hit": false,
     "tool_calls": [{"name": "train_model", "error": false}]}
  ],
  "leftovers": ["model:123", "..."]
}
```

Per-case diagnostics: `error` (RunOutcome error string or null),
`usage_limit_hit`, and `tool_calls` (name + error marker only, no args) —
enough to see why `completed: false` happened without a rerun.

## Comparing runs

```bash
python -m evals.reporting.compare results/a.json results/b.json [--png-dir DIR]
```

One summary row per result file:

- **pass@k** — cases are grouped per scenario (repeat suffix `[i]` stripped);
  a group passes if at least one repeat has ALL its expected stage
  assertions True.
- **stage columns** — per-stage pass rate over the cases that expect that
  stage (missing stage key = not expected, never a failure).
- **`flags:*` columns** — semantic detector firing counts. True = failure
  detected, so any non-zero count is bad.
- mean `step_count` / `wasted_calls`.

With `--png-dir`, also emits `stage_pass.png` and `step_count_hist.png`.

## Smoke tests

```bash
pytest evals/tests -m smoke
```

- `test_local_toolset_exposes_42_tools` always runs: local target lists the
  42-tool surface in-process with a dummy API key (no LLM, no platform).
- `test_live_minimal` runs `telco_churn_minimal` at k=1 end-to-end; it
  skips unless `XPLAINABLE_TEAM_ID`, `ANTHROPIC_API_KEY` and a real
  `XPLAINABLE_API_KEY` are set. These must be exported in the shell:
  `evals/.env` is only read by `python -m evals.run`, not by pytest.

## Known limitations

- Models ARE deleted in teardown (via the raw `/v1/models/{model_id}` route;
  the client has no delete_model wrapper). Reports are still not torn down;
  anything teardown could not delete is logged in the result's `leftovers`
  list.
- The hosted target needs OAuth browser consent on first run (token cached
  under `/tmp/xp-mcp-oauth`).
- Runs cost real LLM money — keep `-k` low while iterating.
- Optimiser cost blind spot: persisted optimisation config is invisible to
  the semantic detectors.
