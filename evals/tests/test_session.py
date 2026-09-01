"""EvalSession: artifact ledger (before/after diff) and teardown.

Mocks mirror the real xplainable-client API:
- datasets.list_team_datasets(team_id=None) -> List[DatasetInfo] (id in
  `dataset_id` or `id`, both Optional)
- models.list_team_models() -> List[ModelInfo] (`model_id`), no delete method
- preprocessing.list_preprocessors(team_id=None) -> List[PreprocessorInfo] (`id`)
- deployments.list_deployments(team_id=None) -> List[DeploymentInfo]
  (`deployment_id`)
- optimisers.list_optimisers(model_id) -> List[Dict] (`id`) — model-scoped
- datasets.upload_dataset_file(file_path, name, description=None, team_id=None)
  -> DatasetUploadResponse (`dataset_id`)
"""
from unittest.mock import MagicMock

import pytest
from xplainable_client.client.py_models.datasets import (
    DatasetInfo,
    DatasetUploadResponse,
)
from xplainable_client.client.py_models.deployments import DeploymentInfo
from xplainable_client.client.py_models.models import ModelInfo
from xplainable_client.client.py_models.preprocessing import PreprocessorInfo

from evals.harness.models import CreatedArtifacts
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
    c.datasets.list_team_datasets.return_value = [_dataset(i) for i in datasets]
    c.models.list_team_models.return_value = [ModelInfo(model_id=i) for i in models]
    c.preprocessing.list_preprocessors.return_value = [_preprocessor(i) for i in preprocessors]
    c.deployments.list_deployments.return_value = [_deployment(i) for i in deployments]
    # Real API is model-scoped (list_optimisers(model_id) -> List[Dict]).
    c.optimisers.list_optimisers.return_value = [{"id": i} for i in optimisers]
    return c


def test_diff_reports_only_new_artifacts():
    client = _client(datasets=["d1"], models=["m1"])
    session = EvalSession(client, team_id="t1")
    session.snapshot()
    client.datasets.list_team_datasets.return_value = [_dataset("d1"), _dataset("d2")]
    client.models.list_team_models.return_value = [
        ModelInfo(model_id="m1"), ModelInfo(model_id="m2"),
    ]
    created = session.diff()
    assert created.datasets == ["d2"]
    assert created.models == ["m2"]
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


def test_teardown_deletes_deletables_and_skips_models():
    client = _client()
    session = EvalSession(client, team_id="t1")
    created = CreatedArtifacts(
        datasets=["d2"], models=["m2"], preprocessors=["p2"],
        deployments=["dep2"], optimisers=["o2"],
    )
    leftovers = session.teardown(created)
    client.deployments.delete_deployment.assert_called_once_with("dep2")
    client.optimisers.delete_optimiser.assert_called_once_with("o2")
    client.preprocessing.delete_preprocessor.assert_called_once_with("p2")
    client.datasets.delete_dataset.assert_called_once_with("d2")
    assert leftovers == ["model:m2"]  # models have no client delete


def test_teardown_continues_past_delete_failures():
    client = _client()
    client.deployments.delete_deployment.side_effect = RuntimeError("boom")
    session = EvalSession(client, team_id="t1")
    created = CreatedArtifacts(deployments=["dep2"], datasets=["d2"])
    leftovers = session.teardown(created)
    client.datasets.delete_dataset.assert_called_once_with("d2")
    assert "deployment:dep2" in leftovers
