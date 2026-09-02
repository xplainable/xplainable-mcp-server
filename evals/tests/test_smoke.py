"""Smoke tests: `pytest evals/tests -m smoke`.

Two tiers:
- test_targets.py::test_local_toolset_exposes_43_tools (also marked smoke):
  always runnable — the local target serves the full 43-tool surface
  in-process with a dummy XPLAINABLE_API_KEY (pinned by conftest). No LLM,
  no live platform.
- test_live_minimal: the REAL end-to-end path (telco_churn_minimal, k=1)
  against the live platform with a real model. Skipped unless
  XPLAINABLE_TEAM_ID, ANTHROPIC_API_KEY and a REAL XPLAINABLE_API_KEY are
  all exported in the shell: it costs real LLM money and creates/deletes
  artifacts in the eval team. (evals/.env is only read by
  `python -m evals.run`, never by pytest — and conftest pins the dummy
  "test-api-key", which must not reach the live platform.)
"""
import os

import pytest

pytestmark = pytest.mark.smoke


@pytest.mark.skipif(
    not os.environ.get("XPLAINABLE_TEAM_ID"),
    reason="live smoke needs XPLAINABLE_TEAM_ID (dedicated eval team)",
)
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live smoke needs ANTHROPIC_API_KEY (runs cost real LLM money)",
)
@pytest.mark.skipif(
    os.environ.get("XPLAINABLE_API_KEY") in (None, "test-api-key"),
    reason=(
        "live smoke needs a real XPLAINABLE_API_KEY exported in the shell "
        "(evals/.env is not read by pytest; conftest's 'test-api-key' "
        "sentinel counts as absent)"
    ),
)
async def test_live_minimal():
    """One telco_churn_minimal case end-to-end.

    Mirrors evals.run.run_cell's orchestration but writes no results JSON.
    Prints the report and leftovers for the operator, then asserts the run
    actually worked: run_case captures agent errors into outcome.error and
    stage failures land as report assertions (never exceptions), so a green
    evaluate() proves nothing by itself.
    """
    # Pin host/write-tools BEFORE the server-stack imports below: those
    # modules call bare load_dotenv(), which walks up and can adopt the
    # stale parent-repo .env (localhost XPLAINABLE_HOSTNAME, write tools
    # off). Safe here: prepare_env's load_dotenv(evals/.env) uses the
    # default override=False, so real exported creds (required by the skip
    # guards above) always win; conftest's "test-api-key" sentinel is a
    # setdefault, and sentinel runs are already skipped by the guards.
    from evals.run import prepare_env
    prepare_env()

    # Lazy: these transitively import xplainable_mcp.server (env-gated).
    from xplainable_client.client.client import XplainableClient

    from evals.harness.models import RunConfig, Stage
    from evals.harness.runner_dataset import build_dataset, build_task
    from evals.harness.session import EvalSession
    from evals.harness.targets import get_toolset
    from evals.scenarios.telco_churn import TELCO_MINIMAL

    team_id = os.environ["XPLAINABLE_TEAM_ID"]
    client = XplainableClient(
        api_key=os.environ["XPLAINABLE_API_KEY"],
        hostname=os.environ.get("XPLAINABLE_HOST", "https://platform.xplainable.io"),
        team_id=team_id,
    )
    session = EvalSession(client, team_id=team_id)
    toolset = get_toolset("local")

    config = RunConfig(scenarios=[TELCO_MINIMAL.name], k=1, label="smoke")
    dataset = build_dataset([TELCO_MINIMAL], config)
    task, leftovers = build_task(config, toolset, session)
    # max_concurrency=1 is a hard requirement: cases share one EvalSession.
    report = await dataset.evaluate(task, max_concurrency=1)

    report.print()                       # operator-visible stage results
    print(f"leftovers: {leftovers}")     # artifacts teardown could not delete

    assert len(report.cases) == 1       # one case per scenario at k=1
    assert isinstance(leftovers, list)  # leftover accumulator returned

    # Same access pattern as runner_dataset.write_result: assertion results
    # unwrap to {name: bool}. Polarity split mirrors reporting.compare:
    # Stage keys and `completed` must be True; everything else is a semantic
    # detector where True = failure detected.
    assertions = {k: r.value for k, r in report.cases[0].assertions.items()}
    stage_keys = {stage.value for stage in Stage}
    stages = {k: v for k, v in assertions.items() if k in stage_keys}
    detectors = {
        k: v for k, v in assertions.items()
        if k not in stage_keys and k != "completed"
    }
    assert stages, f"no stage assertions on the case: {assertions}"
    failed_stages = [k for k, v in stages.items() if not v]
    assert not failed_stages, f"stages failed: {failed_stages}"
    assert assertions.get("completed") is True, (
        "run did not complete (agent error or usage limit)"
    )
    fired = [k for k, v in detectors.items() if v]
    assert not fired, f"semantic failure detectors fired: {fired}"
