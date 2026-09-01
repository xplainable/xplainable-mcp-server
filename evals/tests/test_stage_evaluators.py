"""Stage evaluator tests: outcome-based pass/fail per workflow stage.

Uses a real pydantic-evals EvaluatorContext (constructible with an empty
SpanTree) so we exercise the actual evaluator protocol, not a stub.
"""

from evals.evaluators.stages import (
    PREDICT_TOOLS,
    READ_TOOLS,
    TRAIN_TOOLS,
    WRITE_TOOLS,
    StageEvaluator,
)
from evals.harness.models import CreatedArtifacts, RunOutcome, Stage, ToolCall
from evals.tests.helpers import make_ctx

ALL_STAGES = list(Stage)


def full_pass_outcome() -> RunOutcome:
    return RunOutcome(
        final_text="I trained a model to predict Churn and deployed it.",
        tool_calls=[
            ToolCall(name="datasets_list_team_datasets", args={}),
            ToolCall(name="datasets_preview_dataset_json", args={"dataset_id": "ds-1"}),
            ToolCall(
                name="preprocessing_create_preprocessor_from_spec",
                args={"spec": {"steps": ["fill_missing"]}},
            ),
            ToolCall(
                name="models_train_model",
                args={
                    "dataset_id": "ds-1",
                    "target_column": "Churn",
                    # LIVE shape: train takes only the *version* id, which is an
                    # independent key never containing the preprocessor id.
                    "preprocessor_version_id": "ppv-9",
                },
            ),
            ToolCall(name="deployments_deploy", args={"model_id": "m-1"}),
            ToolCall(
                name="inference_predict",
                args={"records": [{"tenure": 3}], "model_id": "m-1"},
            ),
        ],
        created=CreatedArtifacts(
            models=["m-1"],
            preprocessors=["pp-1"],
            deployments=["d-1"],
        ),
        deployment_active={"d-1": True},
        preprocessor_steps={"pp-1": 3},
        preprocessor_versions={"pp-1": ["ppv-9"]},
        predictions=[{"score": 0.7}],
        prescriptions=[{"action": "discount"}],
        report_urls=["https://app.xplainable.io/reports/r-1"],
    )


class TestReadWriteSets:
    """Read/write classification is derived from the client registry."""

    def test_registry_reads_and_writes(self):
        assert "datasets_list_team_datasets" in READ_TOOLS
        assert "models_get_model" in READ_TOOLS
        assert "models_train_model" in WRITE_TOOLS
        assert "deployments_deploy" in WRITE_TOOLS

    def test_server_native_docs_and_team_getters_are_reads(self):
        assert "docs_list_pages" in READ_TOOLS
        assert "docs_get_page" in READ_TOOLS
        assert "docs_search" in READ_TOOLS
        assert "list_user_teams" in READ_TOOLS

    def test_nothing_outside_registry_is_a_write(self):
        assert "select_team" not in WRITE_TOOLS
        assert "set_active_team" not in WRITE_TOOLS
        assert "docs_search" not in WRITE_TOOLS

    def test_train_and_predict_sets_match_registry_exactly(self):
        """Drift guard: the name-based heuristics must yield exactly these
        tools; a registry change that breaks them should fail loudly here."""
        assert TRAIN_TOOLS == {"models_train_model", "models_refit_model"}
        assert PREDICT_TOOLS == {"inference_predict"}


class TestStageEvaluator:
    def test_full_pass(self):
        ev = StageEvaluator(expected_stages=ALL_STAGES)
        result = ev.evaluate(make_ctx(full_pass_outcome()))
        assert result == {stage.value: True for stage in Stage}

    def test_trained_raw_regression(self):
        """Model created but no preprocessor referenced: TRAIN must fail."""
        outcome = RunOutcome(
            final_text="Trained a model on Churn.",
            tool_calls=[
                ToolCall(name="datasets_preview_dataset_json", args={"dataset_id": "ds-1"}),
                ToolCall(
                    name="models_train_model",
                    args={"dataset_id": "ds-1", "target_column": "Churn"},
                ),
            ],
            created=CreatedArtifacts(models=["m-1"]),
        )
        result = StageEvaluator(expected_stages=ALL_STAGES).evaluate(make_ctx(outcome))
        assert result[Stage.TRAIN.value] is False
        assert result[Stage.DATA_PREP.value] is False
        assert result[Stage.PERSIST_PREP.value] is False
        # explore + select_label still pass on this transcript
        assert result[Stage.EXPLORE.value] is True
        assert result[Stage.SELECT_LABEL.value] is True

    def test_train_fails_when_version_arg_matches_no_created_preprocessor(self):
        """Train call references a version id belonging to no created preprocessor."""
        outcome = RunOutcome(
            final_text="done",
            tool_calls=[
                ToolCall(
                    name="models_train_model",
                    args={"preprocessor_version_id": "ppv-other", "target_column": "Churn"},
                ),
            ],
            created=CreatedArtifacts(models=["m-1"], preprocessors=["pp-1"]),
            preprocessor_versions={"pp-1": ["ppv-9"]},
        )
        result = StageEvaluator(expected_stages=[Stage.TRAIN]).evaluate(make_ctx(outcome))
        assert result == {Stage.TRAIN.value: False}

    def test_train_fails_on_id_prefix_false_positive(self):
        """"ppv-1" is a substring of "ppv-12" but a different id: TRAIN must fail."""
        outcome = RunOutcome(
            final_text="done",
            tool_calls=[
                ToolCall(
                    name="models_train_model",
                    args={"preprocessor_version_id": "ppv-12", "target_column": "Churn"},
                ),
            ],
            created=CreatedArtifacts(models=["m-1"], preprocessors=["pp-1"]),
            preprocessor_versions={"pp-1": ["ppv-1"]},
        )
        result = StageEvaluator(expected_stages=[Stage.TRAIN]).evaluate(make_ctx(outcome))
        assert result == {Stage.TRAIN.value: False}

    def test_train_requires_successful_train_call_referencing_preprocessor(self):
        """Preprocessor exists but the train call that referenced it errored."""
        outcome = RunOutcome(
            final_text="done",
            tool_calls=[
                ToolCall(
                    name="models_train_model",
                    args={"preprocessor_version_id": "pp-1", "target_column": "Churn"},
                    error=True,
                ),
            ],
            created=CreatedArtifacts(models=["m-1"], preprocessors=["pp-1"]),
        )
        result = StageEvaluator(expected_stages=[Stage.TRAIN]).evaluate(make_ctx(outcome))
        assert result == {Stage.TRAIN.value: False}

    def test_deploy_inactive(self):
        outcome = full_pass_outcome()
        outcome.deployment_active = {"d-1": False}
        result = StageEvaluator(expected_stages=ALL_STAGES).evaluate(make_ctx(outcome))
        assert result[Stage.DEPLOY.value] is False

    def test_report_missing(self):
        outcome = full_pass_outcome()
        outcome.report_urls = []
        result = StageEvaluator(expected_stages=ALL_STAGES).evaluate(make_ctx(outcome))
        assert result[Stage.REPORT.value] is False

    def test_explore_fails_when_first_call_is_a_write(self):
        outcome = full_pass_outcome()
        outcome.tool_calls = [
            ToolCall(name="models_train_model", args={"target_column": "Churn"}),
            ToolCall(name="datasets_list_team_datasets", args={}),
        ]
        result = StageEvaluator(expected_stages=[Stage.EXPLORE]).evaluate(make_ctx(outcome))
        assert result == {Stage.EXPLORE.value: False}

    def test_explore_errored_read_does_not_count(self):
        outcome = RunOutcome(
            final_text="",
            tool_calls=[
                ToolCall(name="datasets_list_team_datasets", args={}, error=True),
            ],
        )
        result = StageEvaluator(expected_stages=[Stage.EXPLORE]).evaluate(make_ctx(outcome))
        assert result == {Stage.EXPLORE.value: False}

    def test_explore_passes_with_reads_and_no_writes(self):
        outcome = RunOutcome(
            final_text="",
            tool_calls=[
                ToolCall(name="select_team", args={"team_id": "t-1"}),  # neutral
                ToolCall(name="docs_search", args={"query": "train"}),
            ],
        )
        result = StageEvaluator(expected_stages=[Stage.EXPLORE]).evaluate(make_ctx(outcome))
        assert result == {Stage.EXPLORE.value: True}

    def test_select_label_via_train_args_only(self):
        outcome = RunOutcome(
            final_text="All done.",  # no label mention
            tool_calls=[
                ToolCall(
                    name="models_train_model",
                    args={"dataset_id": "ds-1", "target_column": "Churn"},
                ),
            ],
        )
        result = StageEvaluator(expected_stages=[Stage.SELECT_LABEL]).evaluate(
            make_ctx(outcome)
        )
        assert result == {Stage.SELECT_LABEL.value: True}

    def test_select_label_fails_without_mention_or_target(self):
        outcome = RunOutcome(final_text="All done.")
        result = StageEvaluator(expected_stages=[Stage.SELECT_LABEL]).evaluate(
            make_ctx(outcome)
        )
        assert result == {Stage.SELECT_LABEL.value: False}

    def test_predict_via_successful_call_with_records(self):
        outcome = RunOutcome(
            final_text="",
            tool_calls=[
                ToolCall(
                    name="inference_predict",
                    args={"records": [{"tenure": 1}], "model_id": "m-1"},
                ),
            ],
            predictions=[],  # runner extracted nothing, but the call succeeded
        )
        result = StageEvaluator(expected_stages=[Stage.PREDICT]).evaluate(make_ctx(outcome))
        assert result == {Stage.PREDICT.value: True}

    def test_predict_fails_on_errored_call_with_empty_records(self):
        outcome = RunOutcome(
            final_text="",
            tool_calls=[
                ToolCall(name="inference_predict", args={"records": []}),
                ToolCall(name="inference_predict", args={"records": [{"a": 1}]}, error=True),
            ],
        )
        result = StageEvaluator(expected_stages=[Stage.PREDICT]).evaluate(make_ctx(outcome))
        assert result == {Stage.PREDICT.value: False}

    def test_only_expected_stages_in_result(self):
        """Unexpected stages are omitted; string stage values are accepted."""
        ev = StageEvaluator(expected_stages=["explore", "train"])
        result = ev.evaluate(make_ctx(full_pass_outcome()))
        assert set(result) == {"explore", "train"}
        assert result == {"explore": True, "train": True}

    def test_custom_label_column(self):
        outcome = RunOutcome(final_text="The target is Attrition.")
        ev = StageEvaluator(expected_stages=[Stage.SELECT_LABEL], label_column="Attrition")
        assert ev.evaluate(make_ctx(outcome)) == {Stage.SELECT_LABEL.value: True}
