"""Results JSON: write_result serialises an EvaluationReport + run metadata.

The report is produced by a REAL pydantic-evals Dataset.evaluate over a stub
task (no network) so the test pins the real ReportCase shape write_result
consumes (assertions/scores/labels as EvaluationResult, task_duration).
"""
import json
import re
from datetime import datetime

from evals.harness import runner_dataset
from evals.harness.models import RunConfig, RunOutcome, Stage, ToolCall
from evals.harness.runner_dataset import build_dataset, write_result
from evals.scenarios.telco_churn import TELCO_MINIMAL


async def _stub_task(scenario):
    return RunOutcome(final_text=f"trained on {scenario.dataset_name}")


async def _make_report():
    dataset = build_dataset([TELCO_MINIMAL], RunConfig(k=2))
    return await dataset.evaluate(_stub_task, progress=False)


async def test_write_result_shape_round_trips(tmp_path):
    report = await _make_report()
    config = RunConfig(k=2, label="baseline", model="anthropic:claude-sonnet-4-6")
    path = tmp_path / "results" / "baseline.json"

    payload = write_result(report, config, path, leftovers=["model:m1"])

    on_disk = json.loads(path.read_text())
    assert on_disk == payload  # returned payload IS what was written

    assert on_disk["label"] == "baseline"
    assert on_disk["config"] == {
        "model": "anthropic:claude-sonnet-4-6",
        "prompt_id": "default",
        "target": "local",
        "k": 2,
    }
    assert on_disk["leftovers"] == ["model:m1"]

    # Timezone-aware UTC ISO timestamp.
    ts = datetime.fromisoformat(on_disk["timestamp"])
    assert ts.utcoffset() is not None and ts.utcoffset().total_seconds() == 0

    # Git provenance: this worktree's HEAD sha + installed client version.
    assert re.fullmatch(r"[0-9a-f]{40}", on_disk["git"]["mcp_server"])
    assert re.fullmatch(r"\d+\.\d+.*", on_disk["git"]["xplainable_client"])

    assert [c["name"] for c in on_disk["cases"]] == [
        "telco_churn_minimal[0]", "telco_churn_minimal[1]",
    ]
    for case in on_disk["cases"]:
        # Stage checks + semantic detectors + `completed` are assertions.
        assert case["assertions"][Stage.TRAIN.value] is False  # stub did nothing
        assert case["assertions"]["degenerate_prescriptions"] is False
        assert case["assertions"]["completed"] is True
        # Efficiency ints are scores.
        assert case["scores"]["step_count"] == 0
        assert case["scores"]["wasted_calls"] == 0
        assert isinstance(case["labels"], dict)
        assert isinstance(case["duration"], float)


async def test_write_result_tolerates_missing_git_and_client(tmp_path, monkeypatch):
    # Provenance lookups must never sink a results write: no git binary /
    # uninstalled client degrade to "unknown", not an exception.
    report = await _make_report()

    def boom(*args, **kwargs):
        raise FileNotFoundError("not available")

    monkeypatch.setattr(runner_dataset.subprocess, "run", boom)
    monkeypatch.setattr(runner_dataset.importlib.metadata, "version", boom)

    payload = write_result(report, RunConfig(k=2), tmp_path / "r.json")

    assert payload["git"] == {"mcp_server": "unknown", "xplainable_client": "unknown"}


async def test_write_result_defaults_leftovers_to_empty(tmp_path):
    report = await _make_report()
    payload = write_result(report, RunConfig(k=2), tmp_path / "r.json")
    assert payload["leftovers"] == []


async def test_write_result_persists_case_diagnostics(tmp_path):
    # A failed/limited case must be diagnosable from the JSON alone:
    # error, usage_limit_hit, and minimal tool-call info (name + error
    # marker ONLY — no args, which can be huge / contain data rows).
    async def failing_task(scenario):
        return RunOutcome(
            final_text="",
            error="boom",
            usage_limit_hit=True,
            tool_calls=[
                ToolCall(name="x", args={"huge": "payload"}, error=True,
                         error_text="[E42] boom — Suggestion: fix it"),
                ToolCall(name="y", error=False),
            ],
        )

    dataset = build_dataset([TELCO_MINIMAL], RunConfig(k=1))
    report = await dataset.evaluate(failing_task, progress=False)

    payload = write_result(report, RunConfig(k=1), tmp_path / "r.json")

    (case,) = json.loads((tmp_path / "r.json").read_text())["cases"]
    assert case["error"] == "boom"
    assert case["usage_limit_hit"] is True
    assert case["tool_calls"] == [
        {"name": "x", "error": True,
         "error_text": "[E42] boom — Suggestion: fix it"},
        {"name": "y", "error": False, "error_text": None},
    ]
    assert payload["cases"][0]["tool_calls"] == case["tool_calls"]


async def test_write_result_healthy_case_diagnostics_are_empty(tmp_path):
    report = await _make_report()  # stub task: no error, no tool calls
    payload = write_result(report, RunConfig(k=2), tmp_path / "r.json")
    for case in json.loads((tmp_path / "r.json").read_text())["cases"]:
        assert case["error"] is None
        assert case["usage_limit_hit"] is False
        assert case["tool_calls"] == []
    assert payload["cases"][0]["error"] is None


async def test_write_result_persists_usage(tmp_path):
    async def task(scenario):
        return RunOutcome(final_text="ok", input_tokens=1200,
                          output_tokens=340, cost_usd=0.0123)

    dataset = build_dataset([TELCO_MINIMAL], RunConfig(k=1))
    report = await dataset.evaluate(task, progress=False)
    payload = write_result(report, RunConfig(k=1), tmp_path / "r.json")

    (case,) = json.loads((tmp_path / "r.json").read_text())["cases"]
    assert case["usage"] == {
        "input_tokens": 1200, "output_tokens": 340, "cost_usd": 0.0123,
    }
    assert payload["cases"][0]["usage"] == case["usage"]


async def test_write_result_usage_defaults_when_untracked(tmp_path):
    report = await _make_report()  # stub outcomes carry no usage
    payload = write_result(report, RunConfig(k=2), tmp_path / "r.json")
    for case in payload["cases"]:
        assert case["usage"] == {
            "input_tokens": 0, "output_tokens": 0, "cost_usd": None,
        }
