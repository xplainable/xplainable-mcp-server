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
OPENROUTER_API_KEY=...     # only needed for --model openrouter:...
```

**Use a dedicated eval team.** Evals create AND DELETE datasets, models,
deployments, and reports. Never point `XPLAINABLE_TEAM_ID` at a team you
work in. **One run at a time per team:** teardown deletes everything created
after its pre-run snapshot, so two simultaneous runs against the same team
would delete each other's artifacts.

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

### Testing other models via OpenRouter

pydantic-ai supports OpenRouter natively — no harness changes needed. Set
`OPENROUTER_API_KEY` in `evals/.env` and pass
`--model openrouter:<vendor>/<model>`:

```bash
python -m evals.run --model openrouter:openai/gpt-5.2 \
                    --model anthropic:claude-sonnet-4-6 \
                    --scenario telco_churn_minimal -k 1 --label model-shootout
```

Prefer native `anthropic:` ids for Claude models (direct API, no
provider-routing variance); use `openrouter:` for everything else.

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
     "tool_calls": [{"name": "train_model", "error": false, "error_text": null}]}
  ],
  "leftovers": ["model:123", "..."]
}
```

Per-case diagnostics: `error` (RunOutcome error string or null),
`usage_limit_hit`, and `tool_calls` (name + error marker + error_text only, no args) —
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

## When the tool surface changes

The harness derives its tool knowledge from the client's `@mcp_tool`
registry (the same source the server uses), so adding an endpoint + client
wrapper usually needs almost nothing here:

- **Automatic:** the local target exposes the new tool immediately;
  read/write classification comes from the decorator's `category`; the
  train/predict tool sets are name-derived; stage evaluators check platform
  outcomes, not tool names — existing assertions don't break.
- **Always:** bump the count in
  `test_targets.py::test_local_toolset_exposes_42_tools` (and this README).
  It fails on every surface change by design — a tripwire so the surface
  never changes silently.
- **If the tool creates a new artifact type** (not a
  dataset/model/preprocessor/deployment/optimiser): extend the session
  ledger's snapshot + teardown (`evals/harness/session.py`), or the new
  artifacts leak past teardown into `leftovers`.
- **If it represents a new workflow stage** you want evaluated: add a
  `Stage` enum value, a check in `_STAGE_CHECKS`
  (`evals/evaluators/stages.py`), and a scenario that expects it — existing
  scenarios never exercise tools their prompts don't ask for.

## Known limitations

- Models ARE deleted in teardown (via the raw `/v1/models/{model_id}` route;
  the client has no delete_model wrapper). Reports are still not torn down;
  anything teardown could not delete is logged in the result's `leftovers`
  list.
- The hosted target is currently broken: pydantic-ai 2.37 passes a
  `verify=` kwarg that fastmcp 2.14.7's `StreamableHttpTransport` does not
  accept (`TypeError` at connect). All live validation used `--target local`
  (in-process server against the live platform API). When it works, hosted
  needs OAuth browser consent on first run (token cached under
  `/tmp/xp-mcp-oauth`).
- Runs cost real LLM money — keep `-k` low while iterating.
- Optimiser cost blind spot: persisted optimisation config is invisible to
  the semantic detectors.
