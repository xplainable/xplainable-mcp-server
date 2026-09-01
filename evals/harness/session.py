"""Artifact ledger for eval runs: snapshot/diff of platform state + teardown.

Brackets each eval case: snapshot() before the agent runs, diff() after
(-> CreatedArtifacts of new platform ids), upload_fixture() for setup,
teardown(created) deletes everything deletable. Models have no client delete
method — they are skipped and reported as leftovers.
"""
from typing import Dict, List, Optional, Set

from evals.harness.models import CreatedArtifacts


def _id_of(item, *keys) -> Optional[str]:
    """First non-None id among keys, from a pydantic model or a dict."""
    for key in keys:
        if isinstance(item, dict):
            value = item.get(key)
        else:
            value = getattr(item, key, None)
        if value is not None:
            return str(value)
    return None


class EvalSession:
    """Before/after ledger of platform artifacts for one eval case."""

    def __init__(self, client, team_id: str):
        self.client = client
        self.team_id = team_id
        self._snapshot: Optional[Dict[str, Set[str]]] = None

    def _list_ids(self) -> Dict[str, Set[str]]:
        c = self.client
        datasets = {
            _id_of(d, "dataset_id", "id")
            for d in c.datasets.list_team_datasets(team_id=self.team_id)
        }
        # Scoping asymmetry: list_team_models() scopes by the client session's
        # active team — the harness must construct the client on the eval team.
        models = {_id_of(m, "model_id") for m in c.models.list_team_models()}
        preprocessors = {
            _id_of(p, "id", "preprocessor_id")
            for p in c.preprocessing.list_preprocessors(team_id=self.team_id)
        }
        deployments = {
            _id_of(d, "deployment_id")
            for d in c.deployments.list_deployments(team_id=self.team_id)
        }
        # list_optimisers is model-scoped; aggregate across the team's models.
        optimisers: Set[Optional[str]] = set()
        for model_id in models:
            if model_id is None:
                continue
            try:
                items = c.optimisers.list_optimisers(model_id)
            except Exception:
                continue  # e.g. model type without optimiser support
            optimisers.update(_id_of(o, "id", "optimiser_id") for o in items)
        return {
            "datasets": datasets - {None},
            "models": models - {None},
            "preprocessors": preprocessors - {None},
            "deployments": deployments - {None},
            "optimisers": optimisers - {None},
        }

    def snapshot(self) -> None:
        self._snapshot = self._list_ids()

    def diff(self) -> CreatedArtifacts:
        if self._snapshot is None:
            raise RuntimeError("diff() called before snapshot()")
        now = self._list_ids()
        return CreatedArtifacts(
            **{kind: sorted(now[kind] - self._snapshot[kind]) for kind in now}
        )

    def upload_fixture(self, path: str, name: str) -> str:
        response = self.client.datasets.upload_dataset_file(
            file_path=path, name=name, team_id=self.team_id
        )
        return response.dataset_id

    def teardown(self, created: CreatedArtifacts) -> List[str]:
        """Best-effort delete of created artifacts; returns leftovers.

        Order: deployments -> optimisers -> preprocessors -> datasets.
        Models have no client delete method and are always leftovers.
        """
        leftovers = []
        deletes = [
            ("deployment", created.deployments, self.client.deployments.delete_deployment),
            ("optimiser", created.optimisers, self.client.optimisers.delete_optimiser),
            ("preprocessor", created.preprocessors, self.client.preprocessing.delete_preprocessor),
            ("dataset", created.datasets, self.client.datasets.delete_dataset),
        ]
        for kind, ids, delete in deletes:
            for artifact_id in ids:
                try:
                    delete(artifact_id)
                except Exception as e:
                    leftovers.append(f"{kind}:{artifact_id} ({type(e).__name__}: {e})")
        leftovers.extend(f"model:{model_id}" for model_id in created.models)
        return leftovers
