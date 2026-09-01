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
