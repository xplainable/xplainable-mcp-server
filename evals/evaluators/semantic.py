"""Semantic failure detectors + efficiency metrics.

Detectors encode real *silent* failures observed in a live telco-churn
transcript: an optimiser run whose 20 prescriptions all prescribed identical
lever values, prescriptions flipping immutable features (Gender), zero total
cost spent despite costed levers, and predicted probabilities pinned at the
bounds.

Polarity: every detector returns True when the failure IS detected
(True = bad). Task 11 reporting inverts for display.

Assumed prescription row shapes (extraction is tolerant, but designed
against the real platform responses):

- ``run_optimiser`` returns ``{run_id, batch_id, result}`` where ``result``
  is the XGM envelope ``{'status': 'success', 'results': [...]}``
  (xplainable_client/client/optimisers.py::run_optimiser;
  xplainable_gm/core/agents/interfaces.py::optimize_batch). Each batch
  result row carries ``optimal_features`` (FULL original-unit row),
  ``prediction`` and ``total_cost``
  (xplainable_gm/core/optimization/grid_optimizer.py::optimize, ~line 818).
- Counterfactual-style rows carry ``feature_changes``
  (``{feature: {"from": old, "to": new}}`` for features that MOVED) plus
  ``total_cost`` (grid_optimizer.py::counterfactual, ~line 1520).
- Cost configuration lives in ``cost_structure``: either in
  ``create_optimiser_version``'s ``data`` (optimisers.py, recognised batch
  keys) or per-run in ``run_optimiser``'s ``params``. A model's *persisted*
  optimization_config may also carry costs, which tool-call args cannot see
  — a documented blind spot: no cost_structure in any optimiser call args
  means zero_cost_prescriptions stays False (no evidence of costed levers).
"""

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Union

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from evals.harness.models import RunOutcome, ToolCall

# Keys whose dict value maps ONLY the features that changed.
_CHANGE_KEYS = ("feature_changes", "changes", "prescribed_changes", "levers")
# Keys whose dict value is the FULL prescribed row (includes immutables).
_FULL_ROW_KEYS = ("optimal_features", "counterfactual_features")
_COST_KEYS = ("total_cost", "cost", "cost_spent")
_PROB_KEY_TOKENS = ("proba", "score")  # "probability" contains "proba"


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _change_mapping(row) -> Optional[Dict]:
    """The raw changed-features mapping from a row, or None if absent."""
    if not isinstance(row, dict):
        return None
    for key in _CHANGE_KEYS:
        value = row.get(key)
        if isinstance(value, dict):
            return value
    return None


def _prescribed_changes(row) -> Dict:
    """{feature: prescribed value} for a prescription row.

    Prefers an explicit change mapping (``{"from": a, "to": b}`` values are
    collapsed to ``b``); falls back to the full prescribed row
    (optimal_features / counterfactual_features). Empty dict if neither.
    """
    mapping = _change_mapping(row)
    if mapping is not None:
        return {
            feature: value["to"] if isinstance(value, dict) and "to" in value else value
            for feature, value in mapping.items()
        }
    if isinstance(row, dict):
        for key in _FULL_ROW_KEYS:
            value = row.get(key)
            if isinstance(value, dict):
                return dict(value)
    return {}


def _cost_spent(row) -> Optional[float]:
    """The cost this prescription spent, or None if the row carries none."""
    if not isinstance(row, dict):
        return None
    for key in _COST_KEYS:
        value = row.get(key)
        if _is_number(value):
            return float(value)
    selected = row.get("selected")  # pareto rows nest under "selected"
    if isinstance(selected, dict):
        return _cost_spent(selected)
    return None


def _values_for_key(obj, key: str) -> Iterator:
    """Yield every value stored under `key` anywhere in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield v
            yield from _values_for_key(v, key)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            yield from _values_for_key(item, key)


def _costs_configured(tool_calls: Iterable[ToolCall]) -> bool:
    """True if any optimiser call's args carry a non-empty cost_structure."""
    return any(
        bool(value)
        for call in tool_calls
        if "optimis" in call.name.lower()
        for value in _values_for_key(call.args, "cost_structure")
    )


def _probabilities(predictions: Iterable) -> List[float]:
    """Tolerant probability extraction from prediction rows.

    Numeric values in [0, 1] under keys containing "proba"/"probability"/
    "score" (searched recursively), or bare numbers for non-dict rows.
    A matching key propagates into container values, so multiclass shapes
    like ``{"proba": {"Yes": 0.7, "No": 0.3}}`` yield each class value.
    Values outside [0, 1] are not probabilities and are excluded.
    """
    probs: List[float] = []

    def visit(obj, key_matches: bool = False):
        if isinstance(obj, dict):
            for key, value in obj.items():
                matches = key_matches or any(
                    tok in key.lower() for tok in _PROB_KEY_TOKENS
                )
                visit(value, matches)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                visit(item, key_matches)
        elif key_matches and _is_number(obj) and 0.0 <= obj <= 1.0:
            probs.append(float(obj))

    for row in predictions:
        if isinstance(row, dict):
            visit(row)
        elif _is_number(row) and 0.0 <= row <= 1.0:
            probs.append(float(row))
    return probs


def _degenerate_prescriptions(prescriptions: List[Dict]) -> bool:
    """All rows prescribe identical lever values (the 20-identical-rows
    failure). Needs >= 2 rows and a non-empty extracted mapping."""
    if len(prescriptions) < 2:
        return False
    mappings = [_prescribed_changes(row) for row in prescriptions]
    first = mappings[0]
    return bool(first) and all(m == first for m in mappings[1:])


def _zero_cost_prescriptions(out: RunOutcome) -> bool:
    """Prescriptions exist, costed levers were configured, yet every row
    that reports a cost spent exactly 0."""
    if not out.prescriptions or not _costs_configured(out.tool_calls):
        return False
    spent = [c for c in map(_cost_spent, out.prescriptions) if c is not None]
    return bool(spent) and all(c == 0.0 for c in spent)


def _immutable_drift(prescriptions: List[Dict], immutable_features: List[str]) -> bool:
    """Any prescription changed a declared-immutable feature.

    Only explicit change mappings can prove drift: a full optimal_features
    row contains immutables by construction (no baseline to compare), so it
    never flags. from == to is not a change (string comparison mirrors
    grid_optimizer.py::counterfactual)."""
    immutable = {name.lower() for name in immutable_features}
    if not immutable:
        return False
    for row in prescriptions:
        mapping = _change_mapping(row)
        if not mapping:
            continue
        for feature, value in mapping.items():
            if feature.lower() not in immutable:
                continue
            if isinstance(value, dict) and "from" in value and "to" in value:
                if str(value["from"]) != str(value["to"]):
                    return True
            else:
                return True
    return False


def _saturated_probabilities(predictions: List[Dict]) -> bool:
    """All extracted probabilities pinned at bounds (<0.01 or >0.99).
    Empty predictions -> False (no evidence)."""
    probs = _probabilities(predictions)
    return bool(probs) and all(p < 0.01 or p > 0.99 for p in probs)


@dataclass
class SemanticEvaluator(Evaluator):
    """Four boolean failure detectors; True = failure detected (bad).

    Scenario metadata (immutable_features) lives on the evaluator instance,
    mirroring StageEvaluator's label_column pattern.
    """

    immutable_features: List[str] = field(default_factory=list)

    def evaluate(self, ctx: EvaluatorContext) -> Dict[str, bool]:
        out: RunOutcome = ctx.output
        return {
            "degenerate_prescriptions": _degenerate_prescriptions(out.prescriptions),
            "zero_cost_prescriptions": _zero_cost_prescriptions(out),
            "immutable_drift": _immutable_drift(
                out.prescriptions, self.immutable_features
            ),
            "saturated_probabilities": _saturated_probabilities(out.predictions),
        }


@dataclass
class EfficiencyEvaluator(Evaluator):
    """Transcript efficiency: int values become scores, completed becomes
    an assertion (pydantic-evals downcasts bool before int)."""

    def evaluate(self, ctx: EvaluatorContext) -> Dict[str, Union[bool, int]]:
        out: RunOutcome = ctx.output
        return {
            "step_count": len(out.tool_calls),
            "wasted_calls": sum(1 for call in out.tool_calls if call.error),
            "completed": not out.usage_limit_hit and out.error is None,
        }
