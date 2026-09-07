"""XPLAINABLE_INFERENCE_HOST reaches every XplainableClient the manager builds.

The direct-to-inference tools (inference_score_dataset, optimisers_run_portfolio)
POST to Session.inference_hostname; the server must be able to point that at a
non-prod inference host the same way XPLAINABLE_HOSTNAME points the API.
"""
import importlib
from unittest.mock import MagicMock

import pytest

import xplainable_mcp.client_manager as cm


@pytest.fixture
def fresh_manager(monkeypatch):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "k")
    monkeypatch.setenv("XPLAINABLE_INFERENCE_HOST", "https://inference.test")
    module = importlib.reload(cm)
    module._static_client = None
    module._clients.clear()
    fake = MagicMock()
    monkeypatch.setattr("xplainable_client.client.client.XplainableClient", fake)
    yield module, fake
    monkeypatch.delenv("XPLAINABLE_INFERENCE_HOST", raising=False)
    importlib.reload(cm)


def test_static_client_gets_inference_host(fresh_manager):
    module, fake = fresh_manager
    module._get_static_client()
    assert fake.call_args.kwargs["inference_hostname"] == "https://inference.test"


def test_user_client_gets_inference_host(fresh_manager):
    module, fake = fresh_manager
    module._get_user_client("user-1", "tok")
    assert fake.call_args.kwargs["inference_hostname"] == "https://inference.test"


def test_unset_env_leaves_client_default(monkeypatch):
    monkeypatch.setenv("XPLAINABLE_API_KEY", "k")
    monkeypatch.delenv("XPLAINABLE_INFERENCE_HOST", raising=False)
    module = importlib.reload(cm)
    module._static_client = None
    fake = MagicMock()
    monkeypatch.setattr("xplainable_client.client.client.XplainableClient", fake)
    module._get_static_client()
    assert fake.call_args.kwargs["inference_hostname"] is None
