"""XPLAINABLE_INFERENCE_HOST reaches every XplainableClient the manager builds.

The direct-to-inference tools (inference_score_dataset, optimisers_run_portfolio)
POST to Session.inference_hostname; the server must be able to point that at a
non-prod inference host the same way XPLAINABLE_HOSTNAME points the API.

The fake client below enforces the REAL XplainableClient constructor
signature: a keyword the facade does not accept (inference_hostname lives on
Session, not on the facade) must fail here, not in production.
"""
import importlib
import inspect
from unittest.mock import MagicMock

import pytest

import xplainable_mcp.client_manager as cm
from xplainable_client.client.client import XplainableClient

_REAL_PARAMS = set(inspect.signature(XplainableClient.__init__).parameters) - {"self"}


class _FakeClient:
    """Accepts exactly the keywords the real facade accepts; exposes a session."""

    instances = []

    def __init__(self, **kwargs):
        unknown = set(kwargs) - _REAL_PARAMS
        if unknown:
            raise TypeError(f"XplainableClient.__init__() got unexpected keyword(s): {sorted(unknown)}")
        self.kwargs = kwargs
        self.session = MagicMock()
        self.session.inference_hostname = None
        _FakeClient.instances.append(self)


@pytest.fixture
def fresh_manager(monkeypatch):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "k")
    monkeypatch.setenv("XPLAINABLE_INFERENCE_HOST", "https://inference.test")
    module = importlib.reload(cm)
    module._static_client = None
    module._clients.clear()
    _FakeClient.instances.clear()
    monkeypatch.setattr("xplainable_client.client.client.XplainableClient", _FakeClient)
    yield module
    monkeypatch.delenv("XPLAINABLE_INFERENCE_HOST", raising=False)
    importlib.reload(cm)


def test_static_client_gets_inference_host_on_its_session(fresh_manager):
    client = fresh_manager._get_static_client()
    assert client.session.inference_hostname == "https://inference.test"


def test_user_client_gets_inference_host_on_its_session(fresh_manager):
    client = fresh_manager._get_user_client("user-1", "tok")
    assert client.session.inference_hostname == "https://inference.test"


def test_set_active_team_paths_build_valid_clients(fresh_manager):
    fresh_manager.set_active_team("team-9")  # stdio path: static client
    assert fresh_manager._static_client.session.inference_hostname == "https://inference.test"
    assert fresh_manager._static_client.kwargs["team_id"] == "team-9"


def test_unset_env_leaves_session_default(monkeypatch):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "k")
    monkeypatch.delenv("XPLAINABLE_INFERENCE_HOST", raising=False)
    module = importlib.reload(cm)
    module._static_client = None
    monkeypatch.setattr("xplainable_client.client.client.XplainableClient", _FakeClient)
    client = module._get_static_client()
    assert client.session.inference_hostname is None
