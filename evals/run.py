"""Eval run entrypoint: model x prompt cross-product over the scenario set.

Usage: python -m evals.run --model anthropic:claude-sonnet-4-6 --prompt default

Each (model, prompt) cell becomes one RunConfig, evaluated serially
(max_concurrency=1 — the shared EvalSession is not overlap-safe, see
runner_dataset.build_task) and written to its own JSON in evals/results/.

Import structure: module top only pulls argparse-safe pieces (models,
scenario registry — pure pydantic). Everything that transitively imports
xplainable_mcp.server (targets/session/runner_dataset) is imported lazily
inside the per-cell coroutine, AFTER load_dotenv(evals/.env) has run in
main(), so `--help` works without XPLAINABLE_API_KEY set.
"""
import argparse
import asyncio
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from evals.harness.models import RunConfig
from evals.scenarios.telco_churn import ALL

EVALS_DIR = Path(__file__).parent
# Same location as evals.harness.runner.PROMPTS_DIR, computed directly so
# module top stays free of server-stack imports (runner pulls pydantic_ai).
PROMPTS_DIR = EVALS_DIR / "prompts"
RESULTS_DIR = EVALS_DIR / "results"
_DEFAULTS = RunConfig()


def prepare_env() -> None:
    """Make the eval env hermetic before any server-stack import.

    xplainable_mcp modules call bare load_dotenv() at import, which walks
    up and can adopt a stale parent-repo .env (localhost host, write tools
    off). Pin everything the server reads so evals/.env + these defaults
    are authoritative regardless of parent .env files.

    XPLAINABLE_HOST is the user-facing knob and is respected if exported.
    XPLAINABLE_HOSTNAME (read by the server's client_manager) is a derived
    var and is always overridden with the resolved host — single-host
    assumption: evals talk to exactly one platform, so a pre-existing
    HOSTNAME (e.g. leaked from a parent .env already loaded by an earlier
    server import in this process) must not diverge from HOST.
    """
    from dotenv import load_dotenv  # before any server-stack import
    load_dotenv(EVALS_DIR / ".env")
    host = os.environ.get("XPLAINABLE_HOST", "https://platform.xplainable.io")
    os.environ["XPLAINABLE_HOST"] = host
    os.environ["XPLAINABLE_HOSTNAME"] = host   # server's client_manager reads this
    os.environ["ENABLE_WRITE_TOOLS"] = "true"  # evals require write tools


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="evals.run",
        description="Run MCP agent evals over a model x prompt cross-product.",
    )
    parser.add_argument("--model", action="append",
                        help=f"pydantic-ai model id, repeatable "
                             f"(default: {_DEFAULTS.model})")
    parser.add_argument("--prompt", action="append",
                        help=f"prompt id in evals/prompts/, repeatable "
                             f"(default: {_DEFAULTS.prompt_id})")
    parser.add_argument("--target", choices=["local", "hosted"],
                        default=_DEFAULTS.target,
                        help=f"MCP target (default: {_DEFAULTS.target})")
    parser.add_argument("--scenario", action="append", choices=sorted(ALL),
                        help="scenario name, repeatable (default: all)")
    parser.add_argument("-k", type=int, default=_DEFAULTS.k,
                        help=f"repeats per scenario (default: {_DEFAULTS.k})")
    parser.add_argument("--label", default=_DEFAULTS.label,
                        help=f"result filename prefix "
                             f"(default: {_DEFAULTS.label})")
    return parser.parse_args(argv)


def build_configs(args: argparse.Namespace) -> List[RunConfig]:
    """One RunConfig per (model, prompt) cell of the cross-product."""
    models = args.model or [_DEFAULTS.model]
    prompts = args.prompt or [_DEFAULTS.prompt_id]
    return [
        RunConfig(model=model, prompt_id=prompt_id, target=args.target,
                  scenarios=args.scenario, k=args.k, label=args.label)
        for model in models
        for prompt_id in prompts
    ]


def result_path(config: RunConfig, timestamp: Optional[str] = None,
                results_dir: Path = RESULTS_DIR) -> Path:
    """Unique, informative filename per cell: label_model_prompt_timestamp."""
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model = config.model.replace(":", "-").replace("/", "-")
    label = config.label.replace(":", "-").replace("/", "-")
    return results_dir / f"{label}_{model}_{config.prompt_id}_{ts}.json"


async def run_cell(config: RunConfig) -> Path:
    """Evaluate one (model, prompt) cell and write its results JSON."""
    # Lazy: these transitively import xplainable_mcp.server (env-gated).
    from xplainable_client.client.client import XplainableClient

    from evals.harness.runner_dataset import build_dataset, build_task, write_result
    from evals.harness.session import EvalSession
    from evals.harness.targets import get_toolset

    # Env presence is validated once in main() before any cell runs.
    team_id = os.environ["XPLAINABLE_TEAM_ID"]
    client = XplainableClient(
        api_key=os.environ["XPLAINABLE_API_KEY"],
        hostname=os.environ.get("XPLAINABLE_HOST", "https://platform.xplainable.io"),
        team_id=team_id,
    )
    session = EvalSession(client, team_id=team_id)
    toolset = get_toolset(config.target)

    scenarios = [ALL[name] for name in (config.scenarios or sorted(ALL))]
    dataset = build_dataset(scenarios, config)
    task, leftovers = build_task(config, toolset, session)
    # max_concurrency=1 is a hard requirement: cases share one EvalSession.
    report = await dataset.evaluate(task, max_concurrency=1)
    report.print()
    path = result_path(config)
    write_result(report, config, path, leftovers=leftovers)
    return path


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    prepare_env()

    # Pre-flight: fail once, before any cell, with a friendly message —
    # not once per cell with a traceback.
    for var, message in [
        ("XPLAINABLE_API_KEY", "Set XPLAINABLE_API_KEY in evals/.env"),
        ("XPLAINABLE_TEAM_ID", "Set XPLAINABLE_TEAM_ID (eval team) in evals/.env"),
    ]:
        if not os.environ.get(var):
            print(message, file=sys.stderr)
            return 1
    unknown = [p for p in (args.prompt or [_DEFAULTS.prompt_id])
               if not (PROMPTS_DIR / f"{p}.md").exists()]
    if unknown:
        available = sorted(p.stem for p in PROMPTS_DIR.glob("*.md"))
        print(f"unknown prompt(s): {', '.join(unknown)} — "
              f"available: {', '.join(available)}", file=sys.stderr)
        return 1

    failed = []
    for config in build_configs(args):
        cell = f"{config.model} x {config.prompt_id}"
        print(f"\n=== cell: {cell} (target={config.target}, k={config.k}) ===")
        try:
            path = asyncio.run(run_cell(config))
            print(f"wrote {path}")
        except Exception:  # noqa: BLE001 — one failing cell must not kill the rest
            traceback.print_exc()
            print(f"cell FAILED: {cell}", file=sys.stderr)
            failed.append(cell)
    if failed:
        print(f"\n{len(failed)} cell(s) failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
