"""Smoke tests: `pytest evals/tests -m smoke`.

Two tiers:
- test_local_toolset_lists_42_tools: always runnable — the local target
  serves the full 42-tool surface in-process with a dummy
  XPLAINABLE_API_KEY (pinned by conftest). No LLM, no live platform.
- test_live_minimal: the REAL end-to-end path (telco_churn_minimal, k=1)
  against the live platform with a real model. Skipped unless both
  XPLAINABLE_TEAM_ID and ANTHROPIC_API_KEY are set: it costs real LLM
  money and creates/deletes artifacts in the eval team.
"""
import os

import pytest

pytestmark = pytest.mark.smoke


async def test_local_toolset_lists_42_tools():
    from evals.harness.targets import get_toolset

    toolset = get_toolset("local")
    async with toolset:
        tools = await toolset.list_tools()
    assert len(tools) == 42


@pytest.mark.skipif(
    not os.environ.get("XPLAINABLE_TEAM_ID"),
    reason="live smoke needs XPLAINABLE_TEAM_ID (dedicated eval team)",
)
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live smoke needs ANTHROPIC_API_KEY (runs cost real LLM money)",
)
async def test_live_minimal():
    """One telco_churn_minimal case end-to-end.

    Mirrors evals.run.run_cell's orchestration but writes no results JSON.
    Assertions stay minimal (report produced, one case per scenario,
    leftovers accumulator returned) — live quirks get debugged at the gate.
    """
    # Lazy: these transitively import xplainable_mcp.server (env-gated).
    from xplainable_client.client.client import XplainableClient

    from evals.harness.models import RunConfig
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

    assert len(report.cases) == 1       # one case per scenario at k=1
    assert isinstance(leftovers, list)  # leftover accumulator returned
