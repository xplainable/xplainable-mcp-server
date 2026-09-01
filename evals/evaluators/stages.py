"""Outcome-based stage evaluators.

One evaluator, parametrised by expected stages, returning {stage.value: bool}.
Every check inspects *outcomes* on the RunOutcome (platform artifacts, args,
final text) — never "did the agent call tool X" — with two justified
exceptions: EXPLORE and SELECT_LABEL are agent-behaviour stages with no
platform artifact.

Read/write tool classification is derived programmatically from the
xplainable-client @mcp_tool registry (the same source the server uses to
build its tool surface), not hand-maintained lists.
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Union

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from evals.harness.models import RunOutcome, Stage, ToolCall


def _registry_tool_sets() -> Tuple[Set[str], Set[str]]:
    """(read_tools, write_tools) from the installed client's @mcp_tool registry."""
    from xplainable_mcp.runtime_tools import derive_tool_name, iter_registry_entries

    reads: Set[str] = set()
    writes: Set[str] = set()
    for entry in iter_registry_entries():
        name = derive_tool_name(entry)
        if entry["category"].value == "read":
            reads.add(name)
        else:
            writes.add(name)
    return reads, writes


_REGISTRY_READS, _REGISTRY_WRITES = _registry_tool_sets()

# Server-native tools live outside the registry. Docs readers and team getters
# are read-style; nothing outside the registry ever counts as a write
# (select_team / set_active_team are neutral for EXPLORE purposes).
_SERVER_NATIVE_READS = {
    "docs_list_pages",
    "docs_get_page",
    "docs_search",
    "list_user_teams",
}

READ_TOOLS: Set[str] = _REGISTRY_READS | _SERVER_NATIVE_READS
WRITE_TOOLS: Set[str] = set(_REGISTRY_WRITES)

# Training tools, derived from the registry: write tools whose name suggests
# fitting a model (models_train_model, models_refit_model).
TRAIN_TOOLS: Set[str] = {
    name for name in _REGISTRY_WRITES if "train" in name or "refit" in name
}
PREDICT_TOOLS: Set[str] = {name for name in _REGISTRY_READS if "predict" in name}


def _successful(call: ToolCall) -> bool:
    return not call.error


def _check_explore(out: RunOutcome, label: str) -> bool:
    """>=1 successful read call before the first write call (or anywhere, if no write)."""
    for call in out.tool_calls:
        if call.name in WRITE_TOOLS:
            return False  # hit a write before any successful read
        if call.name in READ_TOOLS and _successful(call):
            return True
    return False


def _check_select_label(out: RunOutcome, label: str) -> bool:
    if label.lower() in out.final_text.lower():
        return True
    return any(
        call.name in TRAIN_TOOLS and label in json.dumps(call.args)
        for call in out.tool_calls
    )


def _check_prep(out: RunOutcome, label: str) -> bool:
    return any(out.preprocessor_steps.get(pid, 0) > 0 for pid in out.created.preprocessors)


def _check_persist_prep(out: RunOutcome, label: str) -> bool:
    return bool(out.created.preprocessors)


def _check_train(out: RunOutcome, label: str) -> bool:
    """Model created AND trained on transformed data (train args reference a
    created preprocessor id) — the motivating trained-on-raw regression."""
    if not out.created.models:
        return False
    return any(
        call.name in TRAIN_TOOLS
        and _successful(call)
        and any(pid in json.dumps(call.args) for pid in out.created.preprocessors)
        for call in out.tool_calls
    )


def _check_deploy(out: RunOutcome, label: str) -> bool:
    return any(out.deployment_active.get(did) is True for did in out.created.deployments)


def _check_predict(out: RunOutcome, label: str) -> bool:
    if out.predictions:
        return True
    return any(
        call.name in PREDICT_TOOLS and _successful(call) and call.args.get("records")
        for call in out.tool_calls
    )


def _check_report(out: RunOutcome, label: str) -> bool:
    return bool(out.report_urls)


def _check_optimise(out: RunOutcome, label: str) -> bool:
    return bool(out.prescriptions)


_STAGE_CHECKS = {
    Stage.EXPLORE: _check_explore,
    Stage.SELECT_LABEL: _check_select_label,
    Stage.DATA_PREP: _check_prep,
    Stage.FEATURE_ENG: _check_prep,
    Stage.PERSIST_PREP: _check_persist_prep,
    Stage.TRAIN: _check_train,
    Stage.DEPLOY: _check_deploy,
    Stage.PREDICT: _check_predict,
    Stage.REPORT: _check_report,
    Stage.OPTIMISE: _check_optimise,
}


@dataclass
class StageEvaluator(Evaluator):
    """Per-stage pass/fail for a scenario's expected stages.

    Returns {stage.value: bool}; bool values become assertions in
    pydantic-evals. Stages not in expected_stages are omitted.
    """

    expected_stages: List[Union[Stage, str]]
    label_column: str = "Churn"

    def evaluate(self, ctx: EvaluatorContext) -> Dict[str, bool]:
        out: RunOutcome = ctx.output
        stages = [Stage(s) for s in self.expected_stages]
        return {
            stage.value: _STAGE_CHECKS[stage](out, self.label_column)
            for stage in stages
        }
