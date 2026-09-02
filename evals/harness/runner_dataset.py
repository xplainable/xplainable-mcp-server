"""Dataset wiring: scenarios -> pydantic-evals Dataset + task + results JSON.

Design choices (pinned against pydantic-evals 2.37.0):
- Per-case evaluators: Case(...) accepts an `evaluators` tuple, so the
  scenario-parametrised StageEvaluator/SemanticEvaluator attach per case;
  the scenario-independent EfficiencyEvaluator sits at dataset level.
- Leftovers plumbing: build_task returns (task, leftovers) where leftovers
  is a mutable list the task closure extends after each case's teardown —
  the caller evaluates the dataset, then passes the list to write_result.
  (Chosen over threading it through build_dataset: the Dataset is pure case
  expansion and separately testable; leftovers belong to task execution.)
- Fixture cleanup: upload_fixture runs BEFORE run_case (whose snapshot()
  then includes the fixture in the baseline, so diff() excludes it) — the
  task adds the fixture dataset id to the teardown ledger explicitly, in a
  `finally` so failed cases still clean up.
"""
import asyncio
import importlib.metadata
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, List, Sequence, Tuple, Union
from uuid import uuid4

from pydantic_evals import Case, Dataset
from pydantic_evals.reporting import EvaluationReport

from evals.evaluators.semantic import EfficiencyEvaluator, SemanticEvaluator
from evals.evaluators.stages import StageEvaluator
from evals.harness.models import CreatedArtifacts, RunConfig, RunOutcome, Scenario
from evals.harness.runner import run_case

FIXTURES_DIR = Path(__file__).parent.parent / "scenarios" / "fixtures"


def build_dataset(scenarios: Sequence[Scenario], config: RunConfig) -> Dataset:
    """One Case per (scenario x repeat i of config.k), named "name[i]"."""
    cases = [
        Case(
            name=f"{scenario.name}[{i}]",
            inputs=scenario,
            metadata={"repeat": i},
            evaluators=(
                StageEvaluator(expected_stages=list(scenario.expected_stages)),
                SemanticEvaluator(immutable_features=list(scenario.immutable_features)),
            ),
        )
        for scenario in scenarios
        for i in range(config.k)
    ]
    return Dataset(name=config.label, cases=cases, evaluators=[EfficiencyEvaluator()])


def build_task(
    config: RunConfig, toolset, session
) -> Tuple[Callable[[Scenario], Awaitable[RunOutcome]], List[str]]:
    """(task, leftovers): the async eval task plus its leftover accumulator.

    Per case: upload the fixture under a unique name, format the scenario
    prompt with it, run the agent, and ALWAYS tear down (fixture dataset +
    everything run_case's diff attributed to the run), extending `leftovers`
    with whatever teardown could not delete.

    Cases MUST NOT overlap: pydantic-evals evaluates cases concurrently by
    default, but the closure shares one EvalSession whose single _snapshot
    slot and upload-between-snapshot-and-diff behavior corrupt overlapping
    cases (baseline overwrite; cross-case artifact deletion). Callers MUST
    evaluate with `max_concurrency=1`; as a backstop, the task holds an
    internal lock for the whole case (upload -> run -> teardown), so
    overlapping invocations serialise rather than corrupt.
    """
    leftovers: List[str] = []
    lock = asyncio.Lock()

    async def task(scenario: Scenario) -> RunOutcome:
        async with lock:
            fixture_dataset_id = None
            outcome = None
            try:
                dataset_name = f"{scenario.dataset_name}-{uuid4().hex[:8]}"
                fixture_dataset_id = session.upload_fixture(
                    str(FIXTURES_DIR / scenario.fixture), dataset_name
                )
                live = scenario.model_copy(update={
                    "prompt": scenario.prompt.format(dataset_name=dataset_name),
                    "dataset_name": dataset_name,
                })
                outcome = await run_case(live, config, toolset, session)
                return outcome
            finally:
                # run_case always returns (agent errors land in outcome.error),
                # so outcome is None only if its contract broke mid-flight —
                # any artifacts leaked on that path are not reported here.
                created = outcome.created if outcome is not None else CreatedArtifacts()
                if fixture_dataset_id and str(fixture_dataset_id) not in created.datasets:
                    created = created.model_copy(
                        update={"datasets": [*created.datasets, str(fixture_dataset_id)]}
                    )
                leftovers.extend(session.teardown(created))

    return task, leftovers


def _git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parent, capture_output=True, text=True, check=True,
        )
        return proc.stdout.strip()
    except Exception:  # noqa: BLE001 — provenance must never sink a write
        return "unknown"


def _client_version() -> str:
    try:
        return importlib.metadata.version("xplainable-client")
    except Exception:  # noqa: BLE001 — provenance must never sink a write
        return "unknown"


def _case_diagnostics(output) -> dict:
    """Minimal per-case diagnostics from a ReportCase output (a RunOutcome).

    Tool-call entries carry name + error marker + error text ONLY — args can
    be huge and may contain data rows. Degrades (per this module's provenance convention)
    if the output is not a RunOutcome — defensive: pydantic-evals 2.37 routes
    raised tasks to report.failures, so report.cases outputs should always be
    the task's return value.
    """
    if not isinstance(output, RunOutcome):
        return {
            "error": "unknown", "usage_limit_hit": False, "tool_calls": [],
            "usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": None},
        }
    return {
        "error": output.error,
        "usage_limit_hit": output.usage_limit_hit,
        "tool_calls": [
            {"name": call.name, "error": call.error, "error_text": call.error_text}
            for call in output.tool_calls
        ],
        "usage": {
            "input_tokens": output.input_tokens,
            "output_tokens": output.output_tokens,
            "cost_usd": output.cost_usd,
        },
    }


def write_result(
    report: EvaluationReport, config: RunConfig, path: Union[Path, str], leftovers=None
) -> dict:
    """Serialise an EvaluationReport (+ run metadata) to JSON at `path`.

    EvaluationResult values are unwrapped: assertions -> {name: bool},
    scores -> {name: int|float}, labels -> {name: str}.
    """
    payload = {
        "label": config.label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "model": config.model,
            "prompt_id": config.prompt_id,
            "target": config.target,
            "k": config.k,
        },
        "git": {"mcp_server": _git_sha(), "xplainable_client": _client_version()},
        "cases": [
            {
                "name": case.name,
                "assertions": {k: r.value for k, r in case.assertions.items()},
                "scores": {k: r.value for k, r in case.scores.items()},
                "labels": {k: r.value for k, r in case.labels.items()},
                "duration": case.task_duration,
                **_case_diagnostics(case.output),
            }
            for case in report.cases
        ],
        "leftovers": list(leftovers or []),
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    return payload
