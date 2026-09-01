"""CLI tests for evals/run.py: arg parsing, cross-product, filenames.

The async main is exercised in the live run (Task 12); here we TDD the
pure pieces (build_configs, result_path, parse_args) plus a --help smoke
test that proves module import does not require server env.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.harness.models import RunConfig
from evals.run import build_configs, parse_args, result_path

REPO_ROOT = Path(__file__).resolve().parents[2]


# --- parse_args ------------------------------------------------------------

def test_parse_args_defaults():
    args = parse_args([])
    assert args.model is None
    assert args.prompt is None
    assert args.target == "local"
    assert args.scenario is None
    assert args.k == 3
    assert args.label == "run"


def test_parse_args_repeatable_flags():
    args = parse_args([
        "--model", "anthropic:claude-sonnet-4-6",
        "--model", "openai:gpt-5",
        "--prompt", "default",
        "--prompt", "terse",
        "--target", "hosted",
        "--scenario", "telco_churn_minimal",
        "-k", "1",
        "--label", "smoke",
    ])
    assert args.model == ["anthropic:claude-sonnet-4-6", "openai:gpt-5"]
    assert args.prompt == ["default", "terse"]
    assert args.target == "hosted"
    assert args.scenario == ["telco_churn_minimal"]
    assert args.k == 1
    assert args.label == "smoke"


def test_parse_args_rejects_bad_target():
    with pytest.raises(SystemExit):
        parse_args(["--target", "staging"])


def test_parse_args_rejects_unknown_scenario(capsys):
    with pytest.raises(SystemExit):
        parse_args(["--scenario", "nope"])
    err = capsys.readouterr().err
    assert "telco_churn_full" in err  # error lists valid names
    assert "telco_churn_minimal" in err


# --- build_configs ---------------------------------------------------------

def test_build_configs_cross_product():
    args = parse_args([
        "--model", "anthropic:claude-sonnet-4-6",
        "--model", "openai:gpt-5",
        "--prompt", "default",
        "--prompt", "terse",
        "--target", "hosted",
        "--scenario", "telco_churn_minimal",
        "-k", "2",
        "--label", "ab",
    ])
    configs = build_configs(args)
    assert len(configs) == 4
    cells = {(c.model, c.prompt_id) for c in configs}
    assert cells == {
        ("anthropic:claude-sonnet-4-6", "default"),
        ("anthropic:claude-sonnet-4-6", "terse"),
        ("openai:gpt-5", "default"),
        ("openai:gpt-5", "terse"),
    }
    for c in configs:
        assert isinstance(c, RunConfig)
        assert c.target == "hosted"
        assert c.scenarios == ["telco_churn_minimal"]
        assert c.k == 2
        assert c.label == "ab"


def test_build_configs_defaults_single_cell():
    configs = build_configs(parse_args([]))
    assert len(configs) == 1
    default = RunConfig()
    assert configs[0].model == default.model
    assert configs[0].prompt_id == default.prompt_id
    assert configs[0].scenarios is None  # None = all scenarios


# --- result_path -----------------------------------------------------------

def test_result_path_sanitises_and_is_informative(tmp_path):
    config = RunConfig(model="anthropic:claude/sonnet-4-6", prompt_id="terse",
                       label="ab")
    path = result_path(config, timestamp="20260901T120000Z",
                       results_dir=tmp_path)
    assert path.parent == tmp_path
    assert ":" not in path.name and "/" not in path.name
    assert path.name == "ab_anthropic-claude-sonnet-4-6_terse_20260901T120000Z.json"


def test_result_path_defaults_to_results_dir():
    path = result_path(RunConfig(), timestamp="20260901T120000Z")
    assert path.parent == REPO_ROOT / "evals" / "results"
    assert path.suffix == ".json"


def test_result_path_generates_timestamp():
    a = result_path(RunConfig())
    assert a.name.endswith("Z.json")


# --- RunConfig.k validation (controller amendment 1) -----------------------

@pytest.mark.parametrize("k", [0, -1])
def test_run_config_rejects_nonpositive_k(k):
    with pytest.raises(ValidationError):
        RunConfig(k=k)


# --- --help smoke: must not require server env -----------------------------

def test_help_runs_without_xplainable_env():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("XPLAINABLE", "AUTH0"))}
    proc = subprocess.run(
        [sys.executable, "-m", "evals.run", "--help"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "usage" in proc.stdout.lower()
    assert "--model" in proc.stdout
