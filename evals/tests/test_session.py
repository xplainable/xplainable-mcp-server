"""EvalSession: artifact ledger (before/after diff) and teardown.

Sub-client mocks are autospecced from the real xplainable-client classes,
so method renames or signature changes fail these tests. Return values are
the real pydantic response models:
- datasets.list_team_datasets(team_id=None) -> List[DatasetInfo] (id in
  `dataset_id` or `id`, both Optional)
- models.list_team_models() -> List[ModelInfo] (`model_id`); no delete_model
  wrapper — teardown uses the inherited BaseClient `delete(endpoint)` accessor
- preprocessing.list_preprocessors(team_id=None) -> List[PreprocessorInfo] (`id`)
- deployments.list_deployments(team_id=None) -> List[DeploymentInfo]
  (`deployment_id`)
- optimisers.list_optimisers(model_id) -> List[Dict] (`id`) — model-scoped
- datasets.upload_dataset_file(file_path, name, description=None, team_id=None)
  -> DatasetUploadResponse (`dataset_id`)
"""
from unittest.mock import MagicMock, create_autospec

import pytest
from xplainable_client.client.datasets import DatasetsClient
from xplainable_client.client.deployments import DeploymentsClient
from xplainable_client.client.models import ModelsClient
from xplainable_client.client.optimisers import OptimisersClient
from xplainable_client.client.preprocessing import PreprocessingClient
from xplainable_client.client.py_models.datasets import (
    DatasetInfo,
    DatasetUploadResponse,
)
from xplainable_client.client.py_models.deployments import DeploymentInfo
from xplainable_client.client.py_models.models import ModelInfo, ModelVersion
from xplainable_client.client.py_models.preprocessing import PreprocessorInfo

from evals.harness.models import CreatedArtifacts, RunOutcome
from evals.harness.session import EvalSession


def _dataset(i):
    return DatasetInfo(dataset_id=i, name=f"name-{i}")


def _preprocessor(i):
    return PreprocessorInfo(id=i, name=f"name-{i}", created_by="u1", created="2026-01-01")


def _deployment(i):
    return DeploymentInfo(
        deployment_id=i, model_id="m1", version_id="v1",
        created_by="u1", created="2026-01-01T00:00:00", active=True,
    )


def _client(datasets=(), models=(), preprocessors=(), deployments=(), optimisers=()):
    c = MagicMock()
    c.datasets = create_autospec(DatasetsClient, instance=True)
    c.models = create_autospec(ModelsClient, instance=True)
    c.preprocessing = create_autospec(PreprocessingClient, instance=True)
    c.deployments = create_autospec(DeploymentsClient, instance=True)
    c.optimisers = create_autospec(OptimisersClient, instance=True)
    c.datasets.list_team_datasets.return_value = [_dataset(i) for i in datasets]
    c.models.list_team_models.return_value = [ModelInfo(model_id=i) for i in models]
    c.preprocessing.list_preprocessors.return_value = [_preprocessor(i) for i in preprocessors]
    c.deployments.list_deployments.return_value = [_deployment(i) for i in deployments]
    # Real API is model-scoped (list_optimisers(model_id) -> List[Dict]).
    c.optimisers.list_optimisers.return_value = [{"id": i} for i in optimisers]
    return c


def test_diff_reports_only_new_artifacts():
    client = _client(
        datasets=["d1"], models=["m1"], preprocessors=["p1"],
        deployments=["dep1"], optimisers=["o1"],
    )
    session = EvalSession(client, team_id="t1")
    session.snapshot()
    client.datasets.list_team_datasets.return_value = [_dataset("d1"), _dataset("d2")]
    client.models.list_team_models.return_value = [
        ModelInfo(model_id="m1"), ModelInfo(model_id="m2"),
    ]
    client.preprocessing.list_preprocessors.return_value = [
        _preprocessor("p1"), _preprocessor("p2"),
    ]
    client.deployments.list_deployments.return_value = [
        _deployment("dep1"), _deployment("dep2"),
    ]
    client.optimisers.list_optimisers.return_value = [{"id": "o1"}, {"id": "o2"}]
    created = session.diff()
    assert created.datasets == ["d2"]
    assert created.models == ["m2"]
    assert created.preprocessors == ["p2"]
    assert created.deployments == ["dep2"]
    assert created.optimisers == ["o2"]
    # list-scoping: team-scoped list methods get the session team_id
    client.datasets.list_team_datasets.assert_called_with(team_id="t1")
    client.preprocessing.list_preprocessors.assert_called_with(team_id="t1")
    client.deployments.list_deployments.assert_called_with(team_id="t1")


def test_diff_reports_new_optimisers_across_models():
    client = _client(models=["m1"])
    session = EvalSession(client, team_id="t1")
    session.snapshot()
    client.optimisers.list_optimisers.return_value = [{"id": "o1"}]
    created = session.diff()
    assert created.optimisers == ["o1"]
    client.optimisers.list_optimisers.assert_called_with("m1")


def test_diff_before_snapshot_raises():
    session = EvalSession(_client(), team_id="t1")
    with pytest.raises(RuntimeError):
        session.diff()


def test_upload_fixture_returns_new_dataset_id(tmp_path):
    client = _client()
    client.datasets.upload_dataset_file.return_value = DatasetUploadResponse(
        dataset_id="d-new"
    )
    fixture = tmp_path / "telco.csv"
    fixture.write_text("a,b\n1,2\n")
    session = EvalSession(client, team_id="t1")
    dataset_id = session.upload_fixture(str(fixture), name="eval_dataset")
    client.datasets.upload_dataset_file.assert_called_once_with(
        file_path=str(fixture), name="eval_dataset", team_id="t1"
    )
    assert dataset_id == "d-new"


def test_teardown_deletes_all_kinds_including_models():
    client = _client()
    session = EvalSession(client, team_id="t1")
    created = CreatedArtifacts(
        datasets=["d2"], models=["m2"], preprocessors=["p2"],
        deployments=["dep2"], optimisers=["o2"],
    )
    leftovers = session.teardown(created)
    client.deployments.delete_deployment.assert_called_once_with("dep2")
    client.optimisers.delete_optimiser.assert_called_once_with("o2")
    # No delete_model wrapper in the client; teardown uses the BaseClient
    # raw HTTP accessor with the real API route (verified live).
    client.models.delete.assert_called_once_with("/v1/models/m2")
    client.preprocessing.delete_preprocessor.assert_called_once_with("p2")
    client.datasets.delete_dataset.assert_called_once_with("d2")
    assert leftovers == []


def test_teardown_continues_past_delete_failures():
    client = _client()
    client.deployments.delete_deployment.side_effect = RuntimeError("boom")
    session = EvalSession(client, team_id="t1")
    created = CreatedArtifacts(deployments=["dep2"], datasets=["d2"])
    leftovers = session.teardown(created)
    client.datasets.delete_dataset.assert_called_once_with("d2")
    assert "deployment:dep2 (RuntimeError: boom)" in leftovers


def test_teardown_model_delete_failure_goes_to_leftovers():
    client = _client()
    client.models.delete.side_effect = RuntimeError("boom")
    session = EvalSession(client, team_id="t1")
    created = CreatedArtifacts(models=["m2"], datasets=["d2"], deployments=["dep2"])
    leftovers = session.teardown(created)
    # Other kinds are still deleted despite the model failure.
    client.deployments.delete_deployment.assert_called_once_with("dep2")
    client.datasets.delete_dataset.assert_called_once_with("d2")
    assert leftovers == ["model:m2 (RuntimeError: boom)"]


def test_teardown_deletes_deployments_before_models_before_preprocessors():
    # Dependency chain: deployments reference model versions, model versions
    # reference preprocessor versions — safe order is dep -> model -> pp.
    client = _client()
    order = []
    client.deployments.delete_deployment.side_effect = (
        lambda i: order.append(("deployment", i))
    )
    client.models.delete.side_effect = lambda route: order.append(("model", route))
    client.preprocessing.delete_preprocessor.side_effect = (
        lambda i: order.append(("preprocessor", i))
    )
    session = EvalSession(client, team_id="t1")
    created = CreatedArtifacts(
        models=["m2"], preprocessors=["p2"], deployments=["dep2"]
    )
    session.teardown(created)
    assert [kind for kind, _ in order] == ["deployment", "model", "preprocessor"]


# ---------------------------------------------------------------- inspect
# Real accessors used by inspect() (verified against xplainable-client):
# - models.list_model_versions(model_id) -> List[ModelVersion] (version_number)
# - models.get_feature_info(version_id) -> {partition: [{"feature": ...}, ...]}
# - deployments.list_deployments(team_id) -> List[DeploymentInfo] (.active)
# - preprocessing has NO list-versions wrapper; inspect uses the BaseClient
#   raw accessor preprocessing.get("/v1/preprocessors/{preprocessor_id}/versions",
#   preprocessor_id=...) -> list of version dicts with spec {"version","steps"}.

def _model_version(version_id, n):
    return ModelVersion(
        version_id=version_id, model_id="m1", version_number=n,
        created="2026-01-01T00:00:00", xplainable_version="3.0", python_version="3.13",
    )


def _outcome(**created):
    return RunOutcome(final_text="", created=CreatedArtifacts(**created))


def test_inspect_fetches_model_features_from_latest_version():
    client = _client()
    client.models.list_model_versions.return_value = [
        _model_version("v1", 1), _model_version("v2", 2),
    ]
    client.models.get_feature_info.return_value = {
        "__dataset__": [{"feature": "tenure"}, {"feature": "contract"}],
    }
    outcome = _outcome(models=["m1"])
    EvalSession(client, team_id="t1").inspect(outcome)
    client.models.list_model_versions.assert_called_once_with("m1")
    client.models.get_feature_info.assert_called_once_with("v2")  # latest version
    assert outcome.model_features == {"m1": ["tenure", "contract"]}


def test_inspect_sets_deployment_active_flags():
    client = _client()
    active = _deployment("dep1")
    inactive = _deployment("dep2")
    inactive.active = False
    client.deployments.list_deployments.return_value = [active, inactive]
    outcome = _outcome(deployments=["dep1", "dep2"])
    EvalSession(client, team_id="t1").inspect(outcome)
    client.deployments.list_deployments.assert_called_once_with(team_id="t1")
    assert outcome.deployment_active == {"dep1": True, "dep2": False}


def test_inspect_counts_preprocessor_steps_from_latest_version_spec():
    client = _client()
    # Version dicts are PreprocessorVersion.model_dump(): id key is "id"
    # (xplainable-api database_models.PreprocessorVersion, __primarykey__="id").
    client.preprocessing.get.return_value = [
        {"id": "ppv-1", "created": "2026-01-01",
         "spec": {"version": "2.0", "steps": [{"id": "a"}]}},
        {"id": "ppv-2", "created": "2026-01-02",
         "spec": {"version": "2.0", "steps": [{"id": "a"}, {"id": "b"}]}},
    ]
    outcome = _outcome(preprocessors=["p1"])
    EvalSession(client, team_id="t1").inspect(outcome)
    client.preprocessing.get.assert_called_once_with(
        "/v1/preprocessors/{preprocessor_id}/versions", preprocessor_id="p1"
    )
    assert outcome.preprocessor_steps == {"p1": 2}
    # Live train args carry only the version id — evaluators need this mapping.
    assert outcome.preprocessor_versions == {"p1": ["ppv-1", "ppv-2"]}


def test_inspect_swallows_fetch_failures_leaving_keys_absent():
    client = _client()
    client.models.list_model_versions.side_effect = RuntimeError("api down")
    client.deployments.list_deployments.side_effect = RuntimeError("api down")
    client.preprocessing.get.side_effect = RuntimeError("api down")
    outcome = _outcome(models=["m1"], deployments=["dep1"], preprocessors=["p1"])
    EvalSession(client, team_id="t1").inspect(outcome)  # must not raise
    assert outcome.model_features == {}
    assert outcome.deployment_active == {}
    assert outcome.preprocessor_steps == {}
