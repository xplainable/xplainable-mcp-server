# MCP Evals Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task.

**Goal:** Build the `evals/` harness from `docs/plans/2026-09-01-mcp-evals-design.md`: pydantic-ai agent drives the MCP server through analyst workflows; pydantic-evals scores stage outcomes, semantic sanity, and step efficiency; results persist as JSON for cross-run comparison.

**Architecture:** `evals/` top-level package (not shipped in wheel). Local target = in-process `MCPToolset(mcp)` on the fully-registered server singleton; hosted target = OAuth streamable-http. Tool sequence extracted from `result.all_messages()` (same data as OTel span tree, no logfire dependency — `span_tree` can be added later). Artifact ledger = before/after diff of the eval team's platform state; teardown via xplainable-client delete methods.

**Tech Stack:** pydantic-ai >=2.37, pydantic-evals >=2.37, matplotlib, fastmcp (already pinned), xplainable-client >=1.16.1.

**Env:** `/Users/jtuppack/projects/xplainable-mcp-server/xplainable-mcp-env/bin/python` (py3.13). Worktree: `.worktrees/mcp-evals`, branch `feature/mcp-evals`.

**Key API facts (verified 2026-09-01, pydantic.dev/docs/ai):**
- `from pydantic_ai.mcp import MCPToolset` — first arg polymorphic: FastMCP server object (in-process), URL string (streamable-http), or fastmcp transport. Kwargs: `auth=` (bearer str, `'oauth'`, or httpx.Auth), `headers=`, `tool_error_behavior='retry'`.
- `Agent('anthropic:claude-sonnet-4-6', toolsets=[toolset], system_prompt=...)`; run with `usage_limits=UsageLimits(request_limit=..., tool_calls_limit=...)`; `UsageLimitExceeded` on breach; lifecycle `async with agent:`.
- litellm proxy: `from pydantic_ai.providers.litellm import LiteLLMProvider` or `OpenAIChatModel(name, provider=OpenAIProvider(base_url=..., api_key=...))`.
- pydantic-evals 2.x: `Dataset(name=..., cases=[...], evaluators=[...])` (name required, kwargs-only); `Case(name=..., inputs=..., metadata=...)`; custom evaluator = `@dataclass` subclass of `Evaluator`, `evaluate(ctx: EvaluatorContext)` may return a **dict of named results** (bool→assertion, float→score, str→label); `report = await dataset.evaluate(task)`; `report.averages()`, `report.print()`, `report.cases[i].assertions/scores/labels`.
- Server import gotcha: `xplainable_mcp.server` calls `load_config()` + `sys.exit(1)` at import if `XPLAINABLE_API_KEY`/`AUTH0_DOMAIN` unset — set env BEFORE import (pattern in `tests/conftest.py`).
- Client teardown methods: `client.datasets.delete_dataset(dataset_id)`, `client.deployments.delete_deployment(deployment_id)`, `client.preprocessing.delete_preprocessor(preprocessor_id)` / `delete_version(version_id)`, `client.optimisers.delete_optimiser(optimiser_id)` / `delete_optimiser_version(optimiser_id, version_id)`. **No model/report delete on the client** — models accumulate on the eval team (accepted; follow-up: raw `BaseClient.delete` endpoint).

**Prerequisites (manual, before Task 12):** "MCP Evals" platform team created + valid API key in `evals/.env` (`XPLAINABLE_API_KEY`, `XPLAINABLE_TEAM_ID`, `ANTHROPIC_API_KEY`). Current repo `.env` key is 401/expired.

---

### Task 1: Scaffolding — pyproject extra, gitignore, package skeleton

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `evals/__init__.py`, `evals/harness/__init__.py`, `evals/scenarios/__init__.py`, `evals/evaluators/__init__.py`, `evals/reporting/__init__.py`, `evals/tests/__init__.py` (all empty)

**Step 1: Add the `evals` extra** to `[project.optional-dependencies]`:

```toml
evals = [
    "pydantic-ai>=2.37.0",
    "pydantic-evals>=2.37.0",
    "matplotlib>=3.8.0",
]
```

**Step 2: Add pytest marker** under `[tool.pytest.ini_options]` (leave `testpaths = ["tests"]` — evals tests run explicitly via `pytest evals/tests`):

```toml
markers = ["smoke: cheap eval cases safe for CI (requires live API key + model key)"]
```

**Step 3: Append to `.gitignore`:**

```
evals/results/
evals/.env
```

**Step 4: Create the empty `__init__.py` files.**

**Step 5: Install deps:**

Run: `xplainable-mcp-env/bin/pip install 'pydantic-ai>=2.37.0' 'pydantic-evals>=2.37.0' 'matplotlib>=3.8.0'`
Expected: installs cleanly alongside fastmcp 2.14.7 (both are pydantic>=2 compatible). If pip resolves a fastmcp conflict, note versions and stop — discuss before forcing.

**Step 6: Verify imports:**

Run: `xplainable-mcp-env/bin/python -c "from pydantic_ai.mcp import MCPToolset; from pydantic_evals import Dataset, Case; print('ok')"`
Expected: `ok`

**Step 7: Verify existing tests still pass:** `xplainable-mcp-env/bin/python -m pytest tests/ -q` → 38 passed.

**Step 8: Commit** — `chore: evals extra + package skeleton`

---

### Task 2: Core models — Stage enum, ToolCall, RunOutcome, Scenario, RunConfig

**Files:**
- Create: `evals/harness/models.py`
- Test: `evals/tests/test_models.py`

**Step 1: Write failing tests:**

```python
"""Core eval models: stages, tool-call records, run outcomes, scenarios."""
import pytest
from pydantic import ValidationError

from evals.harness.models import (
    Stage, ToolCall, RunOutcome, Scenario, RunConfig,
)


def test_stage_enum_covers_full_analyst_flow():
    assert [s.name for s in Stage] == [
        "EXPLORE", "SELECT_LABEL", "DATA_PREP", "FEATURE_ENG",
        "PERSIST_PREP", "TRAIN", "DEPLOY", "PREDICT", "REPORT", "OPTIMISE",
    ]


def test_tool_call_records_error_flag():
    tc = ToolCall(name="autotrain_train_model", args={"dataset_id": "x"}, error=True)
    assert tc.error is True


def test_run_outcome_defaults_are_empty():
    out = RunOutcome(final_text="done")
    assert out.tool_calls == []
    assert out.created.datasets == []
    assert out.model_features == {}
    assert out.report_urls == []


def test_scenario_requires_expected_stages():
    with pytest.raises(ValidationError):
        Scenario(name="s", prompt="p", fixture="f.csv", expected_stages=[])


def test_run_config_defaults():
    cfg = RunConfig()
    assert cfg.model == "anthropic:claude-sonnet-4-6"
    assert cfg.prompt_id == "default"
    assert cfg.target == "local"
    assert cfg.k == 3
```

**Step 2:** Run `xplainable-mcp-env/bin/python -m pytest evals/tests/test_models.py -q` → FAIL (module missing).

**Step 3: Implement `evals/harness/models.py`:**

```python
"""Core data models for the MCP eval harness."""
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Stage(str, Enum):
    EXPLORE = "explore"
    SELECT_LABEL = "select_label"
    DATA_PREP = "data_prep"
    FEATURE_ENG = "feature_eng"
    PERSIST_PREP = "persist_prep"
    TRAIN = "train"
    DEPLOY = "deploy"
    PREDICT = "predict"
    REPORT = "report"
    OPTIMISE = "optimise"


class ToolCall(BaseModel):
    name: str
    args: Dict = Field(default_factory=dict)
    error: bool = False


class CreatedArtifacts(BaseModel):
    """Ids created during a run (before/after diff of the eval team)."""
    datasets: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    preprocessors: List[str] = Field(default_factory=list)
    deployments: List[str] = Field(default_factory=list)
    optimisers: List[str] = Field(default_factory=list)


class RunOutcome(BaseModel):
    """Everything evaluators need: agent transcript facts + platform state."""
    final_text: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    created: CreatedArtifacts = Field(default_factory=CreatedArtifacts)
    model_features: Dict[str, List[str]] = Field(default_factory=dict)  # model_id -> feature names
    deployment_active: Dict[str, bool] = Field(default_factory=dict)    # deployment_id -> active
    preprocessor_steps: Dict[str, int] = Field(default_factory=dict)    # preprocessor_id -> n pipeline steps
    predictions: List[Dict] = Field(default_factory=list)
    prescriptions: List[Dict] = Field(default_factory=list)
    report_urls: List[str] = Field(default_factory=list)
    usage_limit_hit: bool = False
    error: Optional[str] = None


class Scenario(BaseModel):
    name: str
    prompt: str                     # user prompt (may reference dataset name)
    fixture: str                    # CSV path relative to evals/scenarios/fixtures/
    expected_stages: List[Stage] = Field(min_length=1)
    immutable_features: List[str] = Field(default_factory=list)  # for semantic drift check
    dataset_name: str = "eval_dataset"


class RunConfig(BaseModel):
    model: str = "anthropic:claude-sonnet-4-6"
    prompt_id: str = "default"
    target: Literal["local", "hosted"] = "local"
    scenarios: Optional[List[str]] = None   # None = all
    k: int = 3
    label: str = "run"
    tool_calls_limit: int = 80
    request_limit: int = 60
```

**Step 4:** Re-run tests → PASS. Also `pytest tests/ -q` still 38 passed.

**Step 5: Commit** — `feat(evals): core models (Stage, RunOutcome, Scenario, RunConfig)`

---

### Task 3: Telco churn fixture

**Files:**
- Create: `evals/scenarios/fixtures/telco_churn_500.csv`
- Create: `scripts/make_eval_fixture.py`

**Step 1: Write `scripts/make_eval_fixture.py`:**

```python
"""Build the committed telco-churn eval fixture (500-row seeded sample).

Source: IBM Telco Customer Churn (public sample dataset).
"""
import pandas as pd

URL = ("https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/"
       "master/data/Telco-Customer-Churn.csv")
OUT = "evals/scenarios/fixtures/telco_churn_500.csv"

df = pd.read_csv(URL)
# TotalCharges has blank strings in the raw data — keep them; data prep is
# part of what the agent under eval is supposed to handle.
sample = df.sample(n=500, random_state=42).reset_index(drop=True)
sample.to_csv(OUT, index=False)
print(f"wrote {OUT}: {sample.shape}")
```

**Step 2:** Run it: `xplainable-mcp-env/bin/python scripts/make_eval_fixture.py`
Expected: `wrote evals/scenarios/fixtures/telco_churn_500.csv: (500, 21)`

**Step 3: Sanity check** — `head -2` shows `customerID,gender,...,Churn` header; file ~50KB (fine to commit).

**Step 4: Commit** — `feat(evals): telco churn fixture (500-row seeded IBM sample) + generator script`

---

### Task 4: Targets — local in-process and hosted toolsets

**Files:**
- Create: `evals/harness/targets.py`
- Test: `evals/tests/test_targets.py`

**Step 1: Write failing test** (in-memory target lists the 42-tool surface; mirrors `tests/conftest.py` env pinning):

```python
"""Local target must expose the full 42-tool surface in-process."""
import os

os.environ.setdefault("XPLAINABLE_API_KEY", "test-api-key")
os.environ["ENABLE_WRITE_TOOLS"] = "true"

from evals.harness.targets import local_toolset  # noqa: E402


async def test_local_toolset_exposes_42_tools():
    toolset = local_toolset()
    async with toolset:
        tools = await toolset.list_tools()
    assert len(tools) == 42
```

Note: verify the exact way to enumerate tools on `MCPToolset` at implementation time — if `list_tools()` isn't public, assert via `fastmcp.Client(mcp)` that the underlying server has 42 tools and that `local_toolset()` returns an `MCPToolset` wrapping it.

**Step 2:** Run → FAIL (module missing).

**Step 3: Implement `evals/harness/targets.py`:**

```python
"""Eval targets: where the agent's MCP toolset points."""
import os

from pydantic_ai.mcp import MCPToolset

HOSTED_URL = "https://mcp.xplainable.io/mcp"


def local_toolset() -> MCPToolset:
    """In-process server. Env (XPLAINABLE_API_KEY etc.) must be set first —
    xplainable_mcp.server exits at import time without it."""
    if not os.environ.get("XPLAINABLE_API_KEY"):
        raise RuntimeError("Set XPLAINABLE_API_KEY before using the local target")
    from xplainable_mcp.server import mcp  # deferred: import-time config check
    return MCPToolset(mcp)


def hosted_toolset() -> MCPToolset:
    """Hosted server via OAuth (browser consent on first run, token cached)."""
    from fastmcp.client.auth.oauth import OAuth
    from key_value.aio.stores.disk import DiskStore

    auth = OAuth(HOSTED_URL, token_storage=DiskStore(directory="/tmp/xp-mcp-oauth"))
    return MCPToolset(HOSTED_URL, auth=auth)


def get_toolset(target: str) -> MCPToolset:
    return {"local": local_toolset, "hosted": hosted_toolset}[target]()
```

**Step 4:** Run → PASS.

**Step 5: Commit** — `feat(evals): local in-process and hosted OAuth targets`

---

### Task 5: Session — platform snapshot/diff ledger + teardown

**Files:**
- Create: `evals/harness/session.py`
- Test: `evals/tests/test_session.py`

The session brackets each case run: `snapshot()` before, `diff()` after (→ `CreatedArtifacts`), `upload_fixture()` for setup, `teardown(created)` deletes everything deletable (models/reports have no client delete — skipped, logged).

**Step 1: Write failing tests** (mock `XplainableClient`; assert diff picks up new ids and teardown calls the right deletes in safe order — deployments before models' preprocessors, dataset last):

```python
"""EvalSession: artifact ledger (before/after diff) and teardown."""
from unittest.mock import MagicMock

from evals.harness.models import CreatedArtifacts
from evals.harness.session import EvalSession


def _client(datasets=(), models=(), preprocessors=(), deployments=(), optimisers=()):
    c = MagicMock()
    c.datasets.list_datasets.return_value = [{"dataset_id": i} for i in datasets]
    c.models.list_models.return_value = [{"model_id": i} for i in models]
    c.preprocessing.list_preprocessors.return_value = [{"preprocessor_id": i} for i in preprocessors]
    c.deployments.list_deployments.return_value = [{"deployment_id": i} for i in deployments]
    c.optimisers.list_optimisers.return_value = [{"optimiser_id": i} for i in optimisers]
    return c


def test_diff_reports_only_new_artifacts():
    client = _client(datasets=["d1"], models=["m1"])
    session = EvalSession(client, team_id="t1")
    session.snapshot()
    client.datasets.list_datasets.return_value = [{"dataset_id": "d1"}, {"dataset_id": "d2"}]
    client.models.list_models.return_value = [{"model_id": "m1"}, {"model_id": "m2"}]
    created = session.diff()
    assert created.datasets == ["d2"]
    assert created.models == ["m2"]


def test_teardown_deletes_deletables_and_skips_models():
    client = _client()
    session = EvalSession(client, team_id="t1")
    created = CreatedArtifacts(
        datasets=["d2"], models=["m2"], preprocessors=["p2"],
        deployments=["dep2"], optimisers=["o2"],
    )
    leftovers = session.teardown(created)
    client.deployments.delete_deployment.assert_called_once_with("dep2")
    client.optimisers.delete_optimiser.assert_called_once_with("o2")
    client.preprocessing.delete_preprocessor.assert_called_once_with("p2")
    client.datasets.delete_dataset.assert_called_once_with("d2")
    assert leftovers == ["model:m2"]  # models have no client delete


def test_teardown_continues_past_delete_failures():
    client = _client()
    client.deployments.delete_deployment.side_effect = RuntimeError("boom")
    session = EvalSession(client, team_id="t1")
    created = CreatedArtifacts(deployments=["dep2"], datasets=["d2"])
    leftovers = session.teardown(created)
    client.datasets.delete_dataset.assert_called_once_with("d2")
    assert "deployment:dep2" in leftovers
```

**Step 2:** Run → FAIL.

**Step 3: Implement `evals/harness/session.py`** — `EvalSession(client, team_id)` with `_list_ids()` helper mapping the five list methods to id-key names; `snapshot()` stores dict of sets; `diff()` returns `CreatedArtifacts` of new ids; `upload_fixture(path, name)` → `client.datasets.upload_dataset_file(path, name, team_id=self.team_id)` returning dataset id; `teardown(created)` deletes in order deployments → optimisers → preprocessors → datasets, try/except each, collecting `leftovers` (failures + models). Verify exact list-method names/response id keys against the client source at implementation time (`list_datasets`/`list_models`/`list_preprocessors`/`list_deployments`/`list_optimisers` — adjust if named differently, and update the test mocks to match).

**Step 4:** Run → PASS.

**Step 5: Commit** — `feat(evals): session ledger with snapshot/diff and best-effort teardown`

---

### Task 6: Runner — agent execution + RunOutcome extraction

**Files:**
- Create: `evals/harness/runner.py`
- Create: `evals/prompts/default.md`
- Test: `evals/tests/test_runner.py`

**Step 1: `evals/prompts/default.md`** (v1 keeps it minimal — an honest baseline; variants come later):

```markdown
You are a data analyst working on the Xplainable platform via its tools.
Complete the user's request end-to-end. Prepare data properly before
training, persist any preprocessing you do, and finish by reporting what
you built with links where available.
```

**Step 2: Write failing tests for the pure extraction logic** (no LLM):

```python
"""Runner extraction: tool calls and report URLs from agent messages."""
from evals.harness.runner import extract_tool_calls, extract_report_urls

# Build minimal fake message objects mirroring pydantic_ai message parts.
# At implementation time, use the real part classes if importable without
# an agent run: from pydantic_ai.messages import ToolCallPart, RetryPromptPart


class _Part:
    def __init__(self, kind, tool_name=None, args=None):
        self.part_kind = kind
        self.tool_name = tool_name
        self.args = args or {}


class _Msg:
    def __init__(self, parts):
        self.parts = parts


def test_extract_tool_calls_marks_retried_calls_as_errors():
    messages = [
        _Msg([_Part("tool-call", "models_list_models", {})]),
        _Msg([_Part("retry-prompt", "models_list_models")]),
        _Msg([_Part("tool-call", "datasets_upload_dataset", {"name": "x"})]),
    ]
    calls = extract_tool_calls(messages)
    assert [c.name for c in calls] == ["models_list_models", "datasets_upload_dataset"]
    assert calls[0].error is True
    assert calls[1].error is False


def test_extract_report_urls():
    text = "Done! Report: https://platform.xplainable.io/reports/abc123 enjoy"
    assert extract_report_urls(text) == ["https://platform.xplainable.io/reports/abc123"]
```

**Step 3:** Run → FAIL.

**Step 4: Implement `evals/harness/runner.py`:**

```python
"""Run one scenario case: agent + MCP toolset -> RunOutcome."""
import re
from pathlib import Path
from typing import List

from pydantic_ai import Agent, UsageLimits, UsageLimitExceeded

from evals.harness.models import RunConfig, RunOutcome, Scenario, ToolCall

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
URL_RE = re.compile(r"https://[^\s)\"']+")


def extract_tool_calls(messages) -> List[ToolCall]:
    calls: List[ToolCall] = []
    errored: set = set()
    for msg in messages:
        for part in getattr(msg, "parts", []):
            kind = getattr(part, "part_kind", "")
            if kind == "tool-call":
                calls.append(ToolCall(name=part.tool_name, args=dict(part.args or {})))
            elif kind == "retry-prompt" and getattr(part, "tool_name", None):
                errored.add(part.tool_name)
    # Mark the earliest un-flagged call per errored tool name.
    for name in errored:
        for c in calls:
            if c.name == name and not c.error:
                c.error = True
                break
    return calls


def extract_report_urls(text: str) -> List[str]:
    return [u for u in URL_RE.findall(text or "") if "/report" in u]


def load_prompt(prompt_id: str) -> str:
    return (PROMPTS_DIR / f"{prompt_id}.md").read_text()


async def run_case(scenario: Scenario, config: RunConfig, toolset, session) -> RunOutcome:
    """Execute one agent run and inspect resulting platform state."""
    session.snapshot()
    agent = Agent(config.model, toolsets=[toolset],
                  system_prompt=load_prompt(config.prompt_id))
    limits = UsageLimits(request_limit=config.request_limit,
                         tool_calls_limit=config.tool_calls_limit)
    final_text, usage_hit, error = "", False, None
    messages = []
    try:
        async with agent:
            result = await agent.run(scenario.prompt, usage_limits=limits)
        final_text = str(result.output)
        messages = result.all_messages()
    except UsageLimitExceeded:
        usage_hit = True
    except Exception as e:  # harness must survive any agent failure
        error = f"{type(e).__name__}: {e}"

    created = session.diff()
    outcome = RunOutcome(
        final_text=final_text,
        tool_calls=extract_tool_calls(messages),
        created=created,
        report_urls=extract_report_urls(final_text),
        usage_limit_hit=usage_hit,
        error=error,
    )
    session.inspect(outcome)   # fills model_features, deployment_active, preprocessor_steps
    return outcome
```

`session.inspect(outcome)` is added to `EvalSession` in this task (TDD it there too, mocked): for each created model → fetch feature names (via `client.models` accessor — verify exact method, e.g. `get_model`/`list_model_versions`); for each deployment → active flag; for each preprocessor → pipeline step count from its latest version spec. Wrap each fetch in try/except (inspection must not kill the run).

**Step 5:** Run extraction tests → PASS. If `part_kind` string values differ in pydantic-ai 2.37 (`'tool-call'`/`'retry-prompt'` are the 1.x names), fix the constants — verify with `python -c "from pydantic_ai.messages import ToolCallPart, RetryPromptPart; print(ToolCallPart.part_kind, RetryPromptPart.part_kind)"`.

**Step 6: Commit** — `feat(evals): runner with tool-call extraction and platform inspection`

---### Task 7: Stage evaluators

**Files:**
- Create: `evals/evaluators/stages.py`
- Test: `evals/tests/test_stage_evaluators.py`

One evaluator class, parametrised by expected stages, returning a dict `{stage.value: bool}` — outcomes only, never tool names (with two justified exceptions: EXPLORE and SELECT_LABEL are agent-behavior stages with no platform artifact).

Stage pass rules (from the design doc):

| Stage | Pass condition on `RunOutcome` |
|---|---|
| EXPLORE | ≥1 successful read tool call before the first write call |
| SELECT_LABEL | final_text mentions the scenario's known label (`Churn`) OR train call args include correct target |
| DATA_PREP / FEATURE_ENG | ≥1 created preprocessor with `preprocessor_steps > 0` |
| PERSIST_PREP | created.preprocessors non-empty |
| TRAIN | created.models non-empty AND a train tool-call's args reference a created preprocessor id (trained on transformed data — the motivating regression) |
| DEPLOY | ≥1 created deployment with `deployment_active[id] is True` |
| PREDICT | predictions non-empty OR a successful predict call with non-empty records args |
| REPORT | report_urls non-empty |
| OPTIMISE | prescriptions non-empty |

**Step 1: Write failing tests** — construct `RunOutcome` fixtures for: full pass; the "trained raw" regression (model created, no preprocessor referenced → TRAIN False even though DATA_PREP False too); deploy-but-inactive; report missing. ~6 focused tests.

**Step 2:** FAIL → **Step 3:** implement `StageEvaluator(Evaluator)` dataclass with `expected_stages: list[str]`, `label_column: str = "Churn"`, `evaluate(ctx) -> dict` checking only expected stages (unexpected stages omitted from the dict). Helper predicates per stage, small and pure.

**Step 4:** PASS → **Step 5: Commit** — `feat(evals): stage evaluators (outcome-based, incl. trained-on-transformed check)`

---

### Task 8: Semantic detectors + efficiency metrics

**Files:**
- Create: `evals/evaluators/semantic.py`
- Test: `evals/tests/test_semantic.py`

**Detectors** (each returns named results in one `SemanticEvaluator` dict; all from the telco transcript's silent failures):
- `degenerate_prescriptions`: True (bad) if all prescription rows prescribe identical lever values.
- `zero_cost_prescriptions`: True if prescriptions exist, costed levers were configured, and total cost spent == 0.
- `immutable_drift`: True if any prescription changes a feature in `scenario.immutable_features` (e.g. gender, tenure).
- `saturated_probabilities`: True if all predicted probabilities are pinned at bounds (<0.01 or >0.99).

**Efficiency** (`EfficiencyEvaluator` dict): `step_count` (int score), `wasted_calls` (int score = calls with `error=True`), `completed` (bool = not usage_limit_hit and error is None).

**Steps:** failing tests with constructed outcomes (degenerate 20-identical-rows case straight from the transcript, healthy varied case, immutable Gender-flip case) → implement → pass → commit `feat(evals): semantic detectors and efficiency metrics`.

---

### Task 9: Scenarios + pydantic-evals wiring + results JSON

**Files:**
- Create: `evals/scenarios/telco_churn.py`
- Create: `evals/harness/runner_dataset.py`
- Test: `evals/tests/test_dataset_wiring.py`, `evals/tests/test_results_json.py`

**Step 1: Scenario definitions** (`evals/scenarios/telco_churn.py`):

```python
from evals.harness.models import Scenario, Stage

TELCO_FULL = Scenario(
    name="telco_churn_full",
    prompt=(
        "Analyse the '{dataset_name}' dataset: explore it, pick the right "
        "churn label, prepare the data and engineer useful features, persist "
        "that preprocessing, train a churn model on the prepared data, deploy "
        "it, score 20 held-out customers, create a report I can open, and "
        "then optimise retention offers for the 20 customers (budget-aware)."
    ),
    fixture="telco_churn_500.csv",
    expected_stages=list(Stage),
    immutable_features=["gender", "customerID", "tenure"],
    dataset_name="telco_eval",
)

TELCO_MINIMAL = Scenario(
    name="telco_churn_minimal",
    prompt=(
        "Train a churn model on the '{dataset_name}' dataset (prepare the "
        "data first), deploy it, and score 5 held-out customers."
    ),
    fixture="telco_churn_500.csv",
    expected_stages=[Stage.DATA_PREP, Stage.PERSIST_PREP, Stage.TRAIN,
                     Stage.DEPLOY, Stage.PREDICT],
    immutable_features=["gender", "customerID", "tenure"],
    dataset_name="telco_eval",
)

ALL = {s.name: s for s in (TELCO_FULL, TELCO_MINIMAL)}
```

**Step 2: Dataset wiring** (`runner_dataset.py`): `build_dataset(scenarios, config) -> Dataset` — one `Case` per (scenario × repeat i of k), `name=f"{scenario.name}[{i}]"`, `inputs=scenario`, `metadata={"repeat": i}`; dataset evaluators = `[StageEvaluator(...), SemanticEvaluator(...), EfficiencyEvaluator()]`; task = closure calling `run_case` with per-case fixture upload (`session.upload_fixture`) before and `session.teardown` after scoring — teardown runs in the task's `finally` so failures still clean up. TDD the case-expansion (k=2, 2 scenarios → 4 cases, names right) with a stubbed task.

**Step 3: Results JSON** — `write_result(report, config, path)` producing:

```json
{
  "label": "...", "timestamp": "...", "config": {"model": "...", "prompt_id": "...", "target": "...", "k": 3},
  "git": {"mcp_server": "<sha>", "xplainable_client": "<installed version>"},
  "cases": [{"name": "...", "assertions": {...}, "scores": {...}, "labels": {...}, "duration": 1.2}],
  "leftovers": ["model:..."]
}
```

Git SHA via `subprocess` `git rev-parse HEAD`; client version via `importlib.metadata.version("xplainable-client")`. TDD: build a fake report object (or minimal real `EvaluationReport` from a stub run), assert JSON shape round-trips.

**Step 4: Commit** — `feat(evals): telco scenarios, dataset wiring with k-repeats, results JSON`

---

### Task 10: run.py CLI

**Files:**
- Create: `evals/run.py`
- Test: `evals/tests/test_cli.py`

argparse (no new dep): `--model` (repeatable), `--prompt` (repeatable), `--target local|hosted`, `--scenario` (repeatable), `-k`, `--label`. Cross-products models × prompts → one `RunConfig` + one result JSON per cell in `evals/results/`, prints the pydantic-evals report table per cell. Loads `evals/.env` via `dotenv` before anything imports the server. TDD `build_configs(args)` cross-product logic only (2 models × 2 prompts → 4 configs); the async main is exercised in Task 12's live run.

Run: `xplainable-mcp-env/bin/python -m evals.run --help` → usage prints.

**Commit** — `feat(evals): run entrypoint with model×prompt cross-product`

---

### Task 11: Reporting — comparison table + plots

**Files:**
- Create: `evals/reporting/compare.py`
- Create: `evals/reporting/plots.py`
- Test: `evals/tests/test_compare.py`

**compare.py:** `load_results(paths) -> list[dict]`; `comparison_rows(results) -> list[dict]` — per result: label, model, prompt_id, per-stage pass rate (mean of stage assertions across cases), full-flow pass@k (any repeat group where all expected stages True), mean step_count, mean wasted_calls, semantic flag counts; `print_comparison(rows)` renders an aligned text table. CLI: `python -m evals.reporting.compare results/a.json results/b.json`. TDD with two synthetic result dicts — regression direction must be visible (b's DATA_PREP rate < a's).

**plots.py:** `stage_pass_bars(results, out_png)` grouped bar chart; `step_count_hist(results, out_png)` distributions. Smoke-TDD: files get created and are non-empty (matplotlib `Agg` backend).

**Commit** — `feat(evals): cross-run comparison table and plots`

---

### Task 12: Live validation (manual gate) + README

**Files:**
- Create: `evals/README.md`
- Create: `evals/tests/test_smoke.py`

**Step 1 (prereq, human):** create "MCP Evals" platform team; put `XPLAINABLE_API_KEY`, `XPLAINABLE_TEAM_ID`, `ANTHROPIC_API_KEY` in `evals/.env` (gitignored).

**Step 2: Smoke test** (`@pytest.mark.smoke`): local target lists 42 tools with dummy key (no LLM, no live platform — always runnable); plus a `test_live_minimal` guarded by `pytest.mark.skipif(not os.environ.get("XPLAINABLE_TEAM_ID"))` that runs `telco_churn_minimal` k=1.

**Step 3: Live run:**

Run: `xplainable-mcp-env/bin/python -m evals.run --scenario telco_churn_minimal -k 1 --label first-live`
Expected: report table prints; `evals/results/*first-live.json` exists; eval team shows no leftover datasets/deployments (models may remain — logged in `leftovers`).

Debug loop here is expected (part names, client list-method names, platform quirks). Use superpowers:systematic-debugging — fix root causes, keep tests updated.

**Step 4: Then full flow once:** `--scenario telco_churn_full -k 1`. Inspect stage results against the known transcript regressions.

**Step 5: `evals/README.md`** — how to run, config axes, results format, comparison workflow, known limitations (models/reports not torn down; hosted needs OAuth browser consent; costs money).

**Step 6: Commit** — `feat(evals): smoke tests, live-run validation, README`

---

### Task 13: Finish

Full test suite (`pytest tests/ evals/tests/ -q`) green → use superpowers:finishing-a-development-branch (PR to main; note main is prod but `evals/` is not shipped in the wheel and CI's validate job is unaffected).

**Deferred (explicitly out of scope, YAGNI):** CI live-smoke wiring (needs repo secrets — decide separately), model/report deletion via raw endpoints, logfire span trees, litellm proxy config docs beyond README note, prompt variants beyond `default`.
