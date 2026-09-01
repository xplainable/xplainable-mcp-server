"""Scenarios + dataset wiring: case expansion, per-case evaluators, task closure.

The task closure is tested with a monkeypatched run_case and a stub session —
no network, no agent. build_dataset is pure case expansion, tested directly.
"""
import asyncio

import pytest
from pydantic_evals import Dataset

from evals.evaluators.semantic import EfficiencyEvaluator, SemanticEvaluator
from evals.evaluators.stages import StageEvaluator
from evals.harness import runner_dataset
from evals.harness.models import CreatedArtifacts, RunConfig, RunOutcome, Stage
from evals.harness.runner_dataset import FIXTURES_DIR, build_dataset, build_task
from evals.scenarios.telco_churn import ALL, TELCO_FULL, TELCO_MINIMAL


# ------------------------------------------------------------- scenarios

def test_full_scenario_covers_all_stages():
    assert TELCO_FULL.expected_stages == list(Stage)
    assert TELCO_FULL.name == "telco_churn_full"


def test_minimal_scenario_covers_core_pipeline_only():
    assert TELCO_MINIMAL.expected_stages == [
        Stage.DATA_PREP, Stage.PERSIST_PREP, Stage.TRAIN,
        Stage.DEPLOY, Stage.PREDICT,
    ]


def test_scenario_fixtures_exist_on_disk():
    for scenario in ALL.values():
        assert (FIXTURES_DIR / scenario.fixture).is_file(), scenario.fixture


def test_scenario_prompts_are_dataset_name_templates():
    # The task closure formats {dataset_name} with the per-case unique name.
    for scenario in ALL.values():
        assert "{dataset_name}" in scenario.prompt
        assert scenario.dataset_name == "telco_eval"
        assert scenario.immutable_features == ["gender", "customerID", "tenure"]


def test_all_registry_maps_name_to_scenario():
    assert ALL == {
        "telco_churn_full": TELCO_FULL,
        "telco_churn_minimal": TELCO_MINIMAL,
    }


# --------------------------------------------------------- case expansion

def test_build_dataset_expands_k_repeats_per_scenario():
    ds = build_dataset([TELCO_FULL, TELCO_MINIMAL], RunConfig(k=2))
    assert isinstance(ds, Dataset)
    assert [c.name for c in ds.cases] == [
        "telco_churn_full[0]", "telco_churn_full[1]",
        "telco_churn_minimal[0]", "telco_churn_minimal[1]",
    ]
    assert [c.metadata for c in ds.cases] == [
        {"repeat": 0}, {"repeat": 1}, {"repeat": 0}, {"repeat": 1},
    ]
    assert ds.cases[0].inputs is TELCO_FULL
    assert ds.cases[3].inputs is TELCO_MINIMAL


def test_build_dataset_attaches_scenario_evaluators_per_case():
    # Stage/Semantic evaluators are scenario-parametrised -> per-case;
    # Efficiency is scenario-independent -> dataset-level.
    ds = build_dataset([TELCO_MINIMAL], RunConfig(k=1))
    per_case = list(ds.cases[0].evaluators)
    stage = next(e for e in per_case if isinstance(e, StageEvaluator))
    semantic = next(e for e in per_case if isinstance(e, SemanticEvaluator))
    assert stage.expected_stages == TELCO_MINIMAL.expected_stages
    assert semantic.immutable_features == TELCO_MINIMAL.immutable_features
    assert any(isinstance(e, EfficiencyEvaluator) for e in ds.evaluators)
    assert not any(isinstance(e, EfficiencyEvaluator) for e in per_case)


def test_build_dataset_is_named_after_run_label():
    ds = build_dataset([TELCO_MINIMAL], RunConfig(k=1, label="baseline"))
    assert ds.name == "baseline"


# ------------------------------------------------------------ task closure

class _StubSession:
    def __init__(self, upload_raises=False):
        self.upload_raises = upload_raises
        self.uploads = []          # (path, name) per upload_fixture call
        self.torn_down = []        # CreatedArtifacts per teardown call

    def upload_fixture(self, path, name):
        if self.upload_raises:
            raise ConnectionError("upload boom")
        self.uploads.append((path, name))
        return f"fixture-ds-{len(self.uploads)}"

    def teardown(self, created):
        self.torn_down.append(created)
        return [f"model:{m}" for m in created.models]


def _stub_run_case(outcome=None, raises=None):
    calls = []

    async def run_case(scenario, config, toolset, session):
        calls.append(scenario)
        if raises is not None:
            raise raises
        return outcome if outcome is not None else RunOutcome(final_text="ok")

    return run_case, calls


async def test_task_uploads_unique_dataset_name_and_formats_prompt(monkeypatch):
    stub, calls = _stub_run_case()
    monkeypatch.setattr(runner_dataset, "run_case", stub)
    session = _StubSession()
    task, _ = build_task(RunConfig(), toolset=object(), session=session)

    await task(TELCO_MINIMAL)
    await task(TELCO_MINIMAL)

    names = [name for _, name in session.uploads]
    assert len(names) == 2 and names[0] != names[1]  # no collision across repeats
    for name in names:
        assert name.startswith("telco_eval-") and name != "telco_eval"
    # Uploads use the real fixture path.
    assert session.uploads[0][0] == str(FIXTURES_DIR / "telco_churn_500.csv")

    # run_case saw the FORMATTED prompt referencing the uploaded name.
    for scenario, name in zip(calls, names):
        assert "{dataset_name}" not in scenario.prompt
        assert f"'{name}'" in scenario.prompt
        assert scenario.dataset_name == name
    # The module-level scenario object is never mutated.
    assert "{dataset_name}" in TELCO_MINIMAL.prompt
    assert TELCO_MINIMAL.dataset_name == "telco_eval"


async def test_task_returns_outcome_and_tears_down_fixture_and_created(monkeypatch):
    outcome = RunOutcome(
        final_text="done",
        created=CreatedArtifacts(models=["m1"], datasets=["agent-ds"]),
    )
    stub, _ = _stub_run_case(outcome=outcome)
    monkeypatch.setattr(runner_dataset, "run_case", stub)
    session = _StubSession()
    task, leftovers = build_task(RunConfig(), toolset=object(), session=session)

    result = await task(TELCO_MINIMAL)

    assert result is outcome
    assert len(session.torn_down) == 1
    torn = session.torn_down[0]
    assert set(torn.datasets) == {"agent-ds", "fixture-ds-1"}  # fixture included
    assert torn.models == ["m1"]
    assert leftovers == ["model:m1"]  # teardown returns accumulated


async def test_task_tears_down_even_when_run_case_raises(monkeypatch):
    stub, _ = _stub_run_case(raises=RuntimeError("agent exploded"))
    monkeypatch.setattr(runner_dataset, "run_case", stub)
    session = _StubSession()
    task, leftovers = build_task(RunConfig(), toolset=object(), session=session)

    with pytest.raises(RuntimeError, match="agent exploded"):
        await task(TELCO_MINIMAL)

    # Fixture dataset was uploaded before the failure -> still cleaned up.
    assert len(session.torn_down) == 1
    assert session.torn_down[0].datasets == ["fixture-ds-1"]
    assert leftovers == []


async def test_task_upload_failure_still_runs_teardown(monkeypatch):
    stub, calls = _stub_run_case()
    monkeypatch.setattr(runner_dataset, "run_case", stub)
    session = _StubSession(upload_raises=True)
    task, _ = build_task(RunConfig(), toolset=object(), session=session)

    with pytest.raises(ConnectionError):
        await task(TELCO_MINIMAL)

    assert calls == []  # agent never ran
    assert len(session.torn_down) == 1
    assert session.torn_down[0] == CreatedArtifacts()  # nothing to delete


async def test_leftovers_accumulate_across_cases(monkeypatch):
    outcome = RunOutcome(final_text="ok", created=CreatedArtifacts(models=["m1"]))
    stub, _ = _stub_run_case(outcome=outcome)
    monkeypatch.setattr(runner_dataset, "run_case", stub)
    session = _StubSession()
    task, leftovers = build_task(RunConfig(), toolset=object(), session=session)

    await task(TELCO_MINIMAL)
    await task(TELCO_FULL)

    assert leftovers == ["model:m1", "model:m1"]


async def test_task_serialises_concurrent_cases(monkeypatch):
    # pydantic-evals evaluates cases CONCURRENTLY by default, but the task
    # closure shares one EvalSession whose single _snapshot slot corrupts
    # overlapping cases (baseline overwrite; cross-case artifact deletion).
    # The task must serialise: a case's upload must not start until the
    # previous case's teardown has completed.
    events = []

    async def yielding_run_case(scenario, config, toolset, session):
        await asyncio.sleep(0)  # yield so an unlocked second case interleaves
        return RunOutcome(final_text="ok")

    monkeypatch.setattr(runner_dataset, "run_case", yielding_run_case)

    class _RecordingSession(_StubSession):
        def upload_fixture(self, path, name):
            events.append("upload")
            return super().upload_fixture(path, name)

        def teardown(self, created):
            events.append("teardown")
            return super().teardown(created)

    session = _RecordingSession()
    task, _ = build_task(RunConfig(), toolset=object(), session=session)

    await asyncio.gather(task(TELCO_MINIMAL), task(TELCO_FULL))

    assert events == ["upload", "teardown", "upload", "teardown"]
