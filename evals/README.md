# MCP server evals

Regression evals for the [xplainable MCP server](../README.md)'s 43-tool
surface. An LLM agent (pydantic-ai) drives end-to-end ML flows — upload
data, preprocess, train, deploy, predict — through the MCP tools, and each
run is scored with pydantic-evals: stage assertions (did the expected
stages happen), semantic detectors (did known failure modes fire), and
efficiency metrics.

## Setup

You need an [xplainable](https://platform.xplainable.io) account: create an
API key there, and note the team id of a team you can safely trash (see the
warning below). From the repo root (Python 3.10+; we test on 3.13):

```bash
pip install -e '.[evals]'
```

Create `evals/.env`:

```
XPLAINABLE_API_KEY=...     # from platform.xplainable.io
XPLAINABLE_TEAM_ID=...     # a DEDICATED eval team — see warning below
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

Runs cost real LLM money. Ballpark: `telco_churn_minimal` is a few cents to
tens of cents per attempt; `telco_churn_full` came back at roughly $2 per
attempt on `openrouter:z-ai/glm-5.3` (self-reported by the harness's cost
capture). Keep `-k` low while iterating.

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

OpenRouter models get per-request USD cost capture automatically (the
harness enables OpenRouter's usage accounting); other providers report
token counts but `cost_usd` stays `null`.

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
     "tool_calls": [{"name": "train_model", "error": false, "error_text": null}],
     "usage": {"input_tokens": 512340, "output_tokens": 18220, "cost_usd": 1.91}}
  ],
  "leftovers": ["model:123", "..."]
}
```

Per-case diagnostics: `error` (RunOutcome error string or null),
`usage_limit_hit`, `tool_calls` (name + error marker + error_text only, no args) —
enough to see why `completed: false` happened without a rerun — and `usage`
(token totals plus provider-reported cost; `cost_usd` is `null` when the
provider does not report one).

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
- **`cost`** — total USD across cases that reported a cost; `-` for result
  files that predate cost capture (they stay comparable on everything else).

With `--png-dir`, also emits `pass_at_k.png`, `stage_pass.png`,
`step_count_hist.png` and `call_timeline.png`. The timeline draws one
strip per case — every tool call in order, gray for success, red for
errors, dark for the run's most-called tool (named in the legend) — so
budget sinks like polling loops show up as a smear that no summary
statistic conveys. Cases from result files that predate tool-call
capture render as empty strips.

## Smoke tests

```bash
pytest evals/tests -m smoke
```

- `test_local_toolset_exposes_43_tools` always runs: local target lists the
  43-tool surface in-process with a dummy API key (no LLM, no platform).
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
  `test_targets.py::test_local_toolset_exposes_43_tools` (and this README).
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

- All artifact kinds are torn down, including models (via the raw
  `/v1/models/{model_id}` route; the client has no delete_model wrapper)
  and reports (via `reports.delete_report`, client >=1.17.0). Anything
  teardown could not delete is logged in the result's `leftovers` list.
- The hosted target is currently broken: pydantic-ai 2.37 passes a
  `verify=` kwarg that fastmcp 2.14.7's `StreamableHttpTransport` does not
  accept (`TypeError` at connect). All live validation used `--target local`
  (in-process server against the live platform API). When it works, hosted
  needs OAuth browser consent on first run (token cached under
  `/tmp/xp-mcp-oauth`).
- Optimiser cost blind spot: persisted optimisation config is invisible to
  the semantic detectors.
