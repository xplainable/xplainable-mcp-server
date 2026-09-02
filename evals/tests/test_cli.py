"""CLI tests for evals/run.py: arg parsing, cross-product, filenames.

The async main is exercised in the live run (Task 12); here we TDD the
pure pieces (build_configs, result_path, parse_args) plus a --help smoke
test that proves module import does not require server env.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.harness.models import RunConfig
from evals.run import build_configs, main, parse_args, result_path

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
                       label="ab:v1/x")
    path = result_path(config, timestamp="20260901T120000Z",
                       results_dir=tmp_path)
    assert path.parent == tmp_path
    assert ":" not in path.name and "/" not in path.name
    assert path.name == "ab-v1-x_anthropic-claude-sonnet-4-6_terse_20260901T120000Z.json"


def test_result_path_defaults_to_results_dir():
    path = result_path(RunConfig(), timestamp="20260901T120000Z")
    assert path.parent == REPO_ROOT / "evals" / "results"
    assert path.suffix == ".json"


def test_result_path_generates_timestamp():
    a = result_path(RunConfig())
    assert re.search(r"_\d{8}T\d{6}Z\.json$", a.name)


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
    # -k, --target, --label all advertise their defaults (issue 4).
    assert "(default: local)" in proc.stdout
    assert "(default: 3)" in proc.stdout
    assert "(default: run)" in proc.stdout


# --- main() pre-flight: env + prompt validation before any cell ------------

@pytest.fixture
def no_dotenv(monkeypatch, tmp_path):
    """Point main()'s load_dotenv at an empty dir so a real evals/.env
    cannot repopulate env vars the test deleted."""
    monkeypatch.setattr("evals.run.EVALS_DIR", tmp_path)


@pytest.fixture
def run_cell_calls(monkeypatch):
    """Record run_cell invocations; pre-flight failures must leave this empty."""
    calls = []

    async def _recorder(config):
        calls.append(config)
        return Path("/dev/null")

    monkeypatch.setattr("evals.run.run_cell", _recorder)
    return calls


def test_main_missing_api_key_fast_fails(monkeypatch, capsys, no_dotenv,
                                         run_cell_calls):
    monkeypatch.delenv("XPLAINABLE_API_KEY", raising=False)
    monkeypatch.setenv("XPLAINABLE_TEAM_ID", "team-1")
    assert main([]) == 1
    err = capsys.readouterr().err
    assert "Set XPLAINABLE_API_KEY in evals/.env" in err
    assert "Traceback" not in err
    assert run_cell_calls == []


def test_main_missing_team_id_fast_fails(monkeypatch, capsys, no_dotenv,
                                         run_cell_calls):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "test-api-key")
    monkeypatch.delenv("XPLAINABLE_TEAM_ID", raising=False)
    assert main([]) == 1
    err = capsys.readouterr().err
    assert "Set XPLAINABLE_TEAM_ID (eval team) in evals/.env" in err
    assert "Traceback" not in err
    assert run_cell_calls == []


def test_main_unknown_prompt_fast_fails(monkeypatch, capsys, no_dotenv,
                                        run_cell_calls):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "test-api-key")
    monkeypatch.setenv("XPLAINABLE_TEAM_ID", "team-1")
    assert main(["--prompt", "defualt"]) == 1
    err = capsys.readouterr().err
    assert "defualt" in err
    assert "default" in err  # lists available prompt ids
    assert run_cell_calls == []


# --- prepare_env: hermetic env pinning before server-stack import ----------

def test_prepare_env_pins_hostname_to_default_host(monkeypatch, no_dotenv):
    """Neither var set: both resolve to the production platform host."""
    from evals.run import prepare_env
    monkeypatch.delenv("XPLAINABLE_HOST", raising=False)
    monkeypatch.delenv("XPLAINABLE_HOSTNAME", raising=False)
    prepare_env()
    assert os.environ["XPLAINABLE_HOST"] == "https://platform.xplainable.io"
    assert os.environ["XPLAINABLE_HOSTNAME"] == "https://platform.xplainable.io"


def test_prepare_env_respects_exported_host(monkeypatch, no_dotenv):
    """An explicitly exported XPLAINABLE_HOST is the user-facing knob."""
    from evals.run import prepare_env
    monkeypatch.setenv("XPLAINABLE_HOST", "https://example.test")
    monkeypatch.delenv("XPLAINABLE_HOSTNAME", raising=False)
    prepare_env()
    assert os.environ["XPLAINABLE_HOST"] == "https://example.test"
    assert os.environ["XPLAINABLE_HOSTNAME"] == "https://example.test"


def test_prepare_env_forces_write_tools_on(monkeypatch, no_dotenv):
    """Evals require write tools even if ambient env disabled them."""
    from evals.run import prepare_env
    monkeypatch.setenv("ENABLE_WRITE_TOOLS", "false")
    prepare_env()
    assert os.environ["ENABLE_WRITE_TOOLS"] == "true"


def test_prepare_env_overrides_leaked_hostname(monkeypatch, no_dotenv):
    """Guard against the parent-repo .env leak: a pre-existing localhost
    XPLAINABLE_HOSTNAME (derived var) must be overridden by the resolved
    XPLAINABLE_HOST — single-host assumption."""
    from evals.run import prepare_env
    monkeypatch.setenv("XPLAINABLE_HOSTNAME", "http://localhost:8000")
    monkeypatch.delenv("XPLAINABLE_HOST", raising=False)
    prepare_env()
    assert os.environ["XPLAINABLE_HOSTNAME"] == "https://platform.xplainable.io"
