"""Tests for structured error surfacing from runtime tool wrappers.

The client raises XplainableAPIError with .code/.suggestion/.error parsed
from the platform's structured error contract. The wrapper converts these
into FastMCP ToolError with the format:

    [{code}] {base message} — Suggestion: {suggestion}

Legacy errors (code is None) surface as ToolError(str(e)); non-client
exceptions propagate unchanged.
"""

import asyncio
import inspect
from unittest.mock import MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError
from xplainable_client.client.base import XplainableAPIError

from xplainable_mcp.runtime_tools import _build_wrapper


def _fake_method(model_id: str) -> dict:
    """Stand-in client method; behaviour is injected via MagicMock."""
    return {"model_id": model_id}


def _make_wrapper():
    entry = {
        "name": "get_model",
        "signature": inspect.signature(_fake_method),
        "docstring": "Fake get_model.",
        "function": _fake_method,
    }
    return _build_wrapper(entry, "models_get_model", "models")


def _call(wrapper, side_effect=None, return_value=None, **kwargs):
    mock_client = MagicMock()
    if side_effect is not None:
        mock_client.models.get_model.side_effect = side_effect
    else:
        mock_client.models.get_model.return_value = return_value
    with patch(
        "xplainable_mcp.runtime_tools.get_client", return_value=mock_client
    ):
        return asyncio.run(wrapper(**kwargs))


def _structured_error():
    # The installed client (1.13.0) predates the structured contract, so
    # set the structured attrs manually on a real instance to exercise the
    # wrapper's isinstance check against the genuine class.
    exc = XplainableAPIError(
        403, "Model quota reached (30/30) Suggestion: Delete an unused model."
    )
    exc.code = "QUOTA_EXCEEDED"
    exc.suggestion = "Delete an unused model."
    exc.error = {
        "code": "QUOTA_EXCEEDED",
        "message": "Model quota reached (30/30)",
        "suggestion": "Delete an unused model.",
    }
    return exc


class TestStructuredErrors:
    def test_structured_error_formats_code_and_suggestion(self):
        wrapper = _make_wrapper()
        with pytest.raises(ToolError) as excinfo:
            _call(wrapper, side_effect=_structured_error(), model_id="m1")
        assert str(excinfo.value) == (
            "[QUOTA_EXCEEDED] Model quota reached (30/30)"
            " — Suggestion: Delete an unused model."
        )

    def test_legacy_error_uses_str_without_prefix(self):
        wrapper = _make_wrapper()
        exc = XplainableAPIError(404, "Model not found")
        # Installed client has no .code attr at all; the wrapper must be
        # getattr-safe and fall back to str(e).
        with pytest.raises(ToolError) as excinfo:
            _call(wrapper, side_effect=exc, model_id="m1")
        assert str(excinfo.value) == str(exc)
        assert not str(excinfo.value).startswith("[")

    def test_plain_exception_propagates_unchanged(self):
        wrapper = _make_wrapper()
        with pytest.raises(ValueError, match="boom"):
            _call(wrapper, side_effect=ValueError("boom"), model_id="m1")

    def test_successful_call_returns_value(self):
        wrapper = _make_wrapper()
        result = _call(wrapper, return_value={"model_id": "m1"}, model_id="m1")
        assert result == {"model_id": "m1"}
