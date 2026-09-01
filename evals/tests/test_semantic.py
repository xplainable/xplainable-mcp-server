"""Semantic detector + efficiency metric tests.

Detectors encode real silent failures from a live telco-churn transcript:
an optimiser run whose 20 prescriptions all prescribed identical lever
values, prescriptions flipping immutable features (Gender), zero total
cost spent despite costed levers, and probabilities pinned at the bounds.

Prescription rows use the REAL shapes returned by the platform optimiser
run (see evals/evaluators/semantic.py module docstring for pointers):
- batch rows: {"optimal_features": {...}, "prediction": f, "total_cost": f}
- counterfactual rows: {"feature_changes": {feat: {"from": a, "to": b}},
  "total_cost": f, ...}
Polarity: every detector returns True when the failure IS detected.
"""

from pydantic_evals.evaluators import EvaluatorContext
from pydantic_evals.otel.span_tree import SpanTree

from evals.evaluators.semantic import (
    EfficiencyEvaluator,
    SemanticEvaluator,
    _probabilities,
)
from evals.harness.models import RunOutcome, ToolCall

DETECTORS = {
    "degenerate_prescriptions",
    "zero_cost_prescriptions",
    "immutable_drift",
    "saturated_probabilities",
}


def make_ctx(outcome: RunOutcome) -> EvaluatorContext:
    return EvaluatorContext(
        name="case",
        inputs=None,
        metadata=None,
        expected_output=None,
        output=outcome,
        duration=0.0,
        _span_tree=SpanTree(),
        attributes={},
        metrics={},
    )


def cost_config_call() -> ToolCall:
    """Real cost-config location: create_optimiser_version's data.cost_structure
    (xplainable_client optimisers.py create_optimiser_version docstring)."""
    return ToolCall(
        name="optimisers_create_optimiser_version",
        args={
            "optimiser_id": "opt-1",
            "data": {
                "objective": "budget",
                "budget": 100.0,
                "cost_structure": {
                    "MonthlyCharges": {"per_unit": 1.0},
                    "Contract": {"Two year": 50.0},
                },
            },
        },
    )


def counterfactual_row(monthly_from: float, monthly_to: float, cost: float) -> dict:
    return {
        "found": True,
        "prediction": 0.12,
        "total_cost": cost,
        "feature_changes": {
            "MonthlyCharges": {"from": monthly_from, "to": monthly_to},
        },
    }


def healthy_outcome() -> RunOutcome:
    """Varied prescriptions, costs configured and spent, mixed probabilities."""
    return RunOutcome(
        final_text="Optimised retention offers for 3 customers.",
        tool_calls=[
            ToolCall(name="datasets_list_team_datasets", args={}),
            cost_config_call(),
            ToolCall(name="optimisers_run_optimiser", args={"optimiser_id": "opt-1"}),
        ],
        predictions=[{"proba": 0.72}, {"proba": 0.31}, {"proba": 0.55}],
        prescriptions=[
            counterfactual_row(89.0, 60.0, 29.0),
            counterfactual_row(75.5, 70.0, 5.5),
            counterfactual_row(99.9, 45.0, 54.9),
        ],
    )


class TestDegeneratePrescriptions:
    def test_transcript_case_20_identical_rows(self):
        """The live failure: 20 prescriptions, per-customer "from" values vary
        but every customer is prescribed the SAME lever targets."""
        rows = [
            {
                "prediction": 0.05,
                "total_cost": 50.0,
                "feature_changes": {
                    "Contract": {"from": "Month-to-month", "to": "Two year"},
                    "MonthlyCharges": {"from": 20.0 + i, "to": 29.0},
                },
            }
            for i in range(20)
        ]
        outcome = RunOutcome(final_text="", prescriptions=rows)
        result = SemanticEvaluator().evaluate(make_ctx(outcome))
        assert result["degenerate_prescriptions"] is True

    def test_identical_full_optimal_features_rows(self):
        """Batch shape (grid_optimizer optimize): identical full rows."""
        row = {
            "optimal_features": {"MonthlyCharges": 29.0, "Contract": "Two year"},
            "prediction": 0.05,
            "total_cost": 50.0,
        }
        outcome = RunOutcome(final_text="", prescriptions=[dict(row) for _ in range(5)])
        result = SemanticEvaluator().evaluate(make_ctx(outcome))
        assert result["degenerate_prescriptions"] is True

    def test_varied_rows_not_flagged(self):
        result = SemanticEvaluator().evaluate(make_ctx(healthy_outcome()))
        assert result["degenerate_prescriptions"] is False

    def test_single_row_not_flagged(self):
        outcome = RunOutcome(
            final_text="", prescriptions=[counterfactual_row(89.0, 60.0, 29.0)]
        )
        result = SemanticEvaluator().evaluate(make_ctx(outcome))
        assert result["degenerate_prescriptions"] is False


class TestZeroCostPrescriptions:
    def zero_cost_rows(self):
        return [counterfactual_row(80.0 + i, 80.0 + i, 0.0) for i in range(3)]

    def test_zero_spend_with_costs_configured(self):
        outcome = RunOutcome(
            final_text="",
            tool_calls=[cost_config_call()],
            prescriptions=self.zero_cost_rows(),
        )
        result = SemanticEvaluator().evaluate(make_ctx(outcome))
        assert result["zero_cost_prescriptions"] is True

    def test_zero_spend_without_cost_config_is_not_a_failure(self):
        outcome = RunOutcome(
            final_text="",
            tool_calls=[
                ToolCall(name="optimisers_run_optimiser", args={"optimiser_id": "opt-1"}),
            ],
            prescriptions=self.zero_cost_rows(),
        )
        result = SemanticEvaluator().evaluate(make_ctx(outcome))
        assert result["zero_cost_prescriptions"] is False

    def test_nonzero_spend_not_flagged(self):
        result = SemanticEvaluator().evaluate(make_ctx(healthy_outcome()))
        assert result["zero_cost_prescriptions"] is False

    def test_cost_structure_in_run_params_counts_as_configured(self):
        """cost_structure may also arrive per-run via run params
        (optimisers.py run_optimiser params / interfaces.py optimize_batch)."""
        outcome = RunOutcome(
            final_text="",
            tool_calls=[
                ToolCall(
                    name="optimisers_run_optimiser",
                    args={
                        "optimiser_id": "opt-1",
                        "params": {"cost_structure": {"MonthlyCharges": {"per_unit": 1.0}}},
                    },
                ),
            ],
            prescriptions=self.zero_cost_rows(),
        )
        result = SemanticEvaluator().evaluate(make_ctx(outcome))
        assert result["zero_cost_prescriptions"] is True


class TestImmutableDrift:
    def test_gender_flip_case_insensitive(self):
        """The live failure: a prescription flipped Gender; scenario declares
        the feature lowercase."""
        outcome = RunOutcome(
            final_text="",
            prescriptions=[
                {
                    "prediction": 0.1,
                    "total_cost": 10.0,
                    "feature_changes": {
                        "Gender": {"from": "Male", "to": "Female"},
                        "MonthlyCharges": {"from": 80.0, "to": 60.0},
                    },
                },
            ],
        )
        ev = SemanticEvaluator(immutable_features=["gender", "tenure"])
        result = ev.evaluate(make_ctx(outcome))
        assert result["immutable_drift"] is True

    def test_no_drift_when_immutables_untouched(self):
        ev = SemanticEvaluator(immutable_features=["gender", "tenure"])
        result = ev.evaluate(make_ctx(healthy_outcome()))
        assert result["immutable_drift"] is False

    def test_unchanged_immutable_in_change_mapping_not_flagged(self):
        """from == to is not a change (mirrors grid_optimizer str comparison)."""
        outcome = RunOutcome(
            final_text="",
            prescriptions=[
                {
                    "feature_changes": {"Gender": {"from": "Male", "to": "Male"}},
                    "total_cost": 0.0,
                },
            ],
        )
        ev = SemanticEvaluator(immutable_features=["Gender"])
        result = ev.evaluate(make_ctx(outcome))
        assert result["immutable_drift"] is False

    def test_full_row_shape_does_not_false_positive(self):
        """optimal_features carries the FULL row incl. immutables; presence
        alone is not drift (no baseline to compare against)."""
        outcome = RunOutcome(
            final_text="",
            prescriptions=[
                {
                    "optimal_features": {"Gender": "Male", "MonthlyCharges": 60.0},
                    "prediction": 0.1,
                    "total_cost": 20.0,
                },
            ],
        )
        ev = SemanticEvaluator(immutable_features=["gender"])
        result = ev.evaluate(make_ctx(outcome))
        assert result["immutable_drift"] is False

    def test_no_immutables_declared_never_flags(self):
        outcome = RunOutcome(
            final_text="",
            prescriptions=[
                {"feature_changes": {"Gender": {"from": "Male", "to": "Female"}}},
            ],
        )
        result = SemanticEvaluator().evaluate(make_ctx(outcome))
        assert result["immutable_drift"] is False


class TestSaturatedProbabilities:
    def test_all_pinned(self):
        outcome = RunOutcome(
            final_text="",
            predictions=[{"proba": 0.999}, {"probability": 0.0001}, {"score": 0.9950}],
        )
        result = SemanticEvaluator().evaluate(make_ctx(outcome))
        assert result["saturated_probabilities"] is True

    def test_healthy_mixed_not_flagged(self):
        result = SemanticEvaluator().evaluate(make_ctx(healthy_outcome()))
        assert result["saturated_probabilities"] is False

    def test_empty_predictions_is_no_evidence(self):
        result = SemanticEvaluator().evaluate(make_ctx(RunOutcome(final_text="")))
        assert result["saturated_probabilities"] is False

    def test_bare_floats_supported_by_extraction(self):
        assert _probabilities([0.999, 0.005]) == [0.999, 0.005]

    def test_non_probability_scores_excluded(self):
        """A 'score' of 150 is not a probability; must not count as pinned."""
        assert _probabilities([{"score": 150.0}]) == []


class TestEmptyPrescriptions:
    def test_all_prescription_detectors_false(self):
        outcome = RunOutcome(final_text="", tool_calls=[cost_config_call()])
        result = SemanticEvaluator(immutable_features=["gender"]).evaluate(
            make_ctx(outcome)
        )
        assert result["degenerate_prescriptions"] is False
        assert result["zero_cost_prescriptions"] is False
        assert result["immutable_drift"] is False


class TestSemanticResultShape:
    def test_exactly_the_four_detectors_all_bool(self):
        result = SemanticEvaluator().evaluate(make_ctx(healthy_outcome()))
        assert set(result) == DETECTORS
        assert all(type(v) is bool for v in result.values())


class TestEfficiencyEvaluator:
    def test_counts_with_errored_calls(self):
        outcome = RunOutcome(
            final_text="done",
            tool_calls=[
                ToolCall(name="datasets_list_team_datasets", args={}),
                ToolCall(name="models_train_model", args={}, error=True),
                ToolCall(name="models_train_model", args={}),
                ToolCall(name="inference_predict", args={}, error=True),
                ToolCall(name="inference_predict", args={}),
            ],
        )
        result = EfficiencyEvaluator().evaluate(make_ctx(outcome))
        assert result == {"step_count": 5, "wasted_calls": 2, "completed": True}
        # ints (not bools) so pydantic-evals downcasts them into scores
        assert type(result["step_count"]) is int
        assert type(result["wasted_calls"]) is int
        assert type(result["completed"]) is bool

    def test_usage_limit_means_not_completed(self):
        outcome = RunOutcome(final_text="", usage_limit_hit=True)
        result = EfficiencyEvaluator().evaluate(make_ctx(outcome))
        assert result == {"step_count": 0, "wasted_calls": 0, "completed": False}

    def test_error_means_not_completed(self):
        outcome = RunOutcome(final_text="", error="boom")
        result = EfficiencyEvaluator().evaluate(make_ctx(outcome))
        assert result["completed"] is False
