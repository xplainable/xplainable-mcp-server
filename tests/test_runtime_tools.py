"""Tests for runtime tool generation from the xplainable-client @mcp_tool registry."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from xplainable_mcp.runtime_tools import (
    compute_annotations,
    compute_tags,
    derive_tool_name,
    iter_registry_entries,
    register_client_tools,
)


def _entry_for(tool_name):
    for e in iter_registry_entries():
        if derive_tool_name(e) == tool_name:
            return e
    raise AssertionError(f"{tool_name} not in registry")


@pytest.fixture(scope="module")
def tool_map():
    mcp = FastMCP(name="test")
    register_client_tools(mcp)
    return asyncio.run(mcp.get_tools())


class TestNaming:
    def test_derive_tool_name_from_qualname(self):
        entry = {"qualname": "ModelsClient.get_model", "name": "get_model"}
        assert derive_tool_name(entry) == "models_get_model"

    def test_all_registry_names_unique(self):
        names = [derive_tool_name(e) for e in iter_registry_entries()]
        assert len(names) == len(set(names))


class TestTags:
    """Tags are informational only: exactly the category, no overlays."""

    def test_read_tool_tagged_read(self):
        entry = _entry_for("models_get_model")
        assert compute_tags(entry) == {"read"}

    def test_write_tool_tagged_write(self):
        entry = _entry_for("models_train_model")
        assert compute_tags(entry) == {"write"}

    def test_no_overlay_tags_anywhere(self):
        for entry in iter_registry_entries():
            tags = compute_tags(entry)
            assert tags in ({"read"}, {"write"}), derive_tool_name(entry)
            assert not tags & {"curated", "guided", "workflow"}


class TestAnnotations:
    """MCP annotations are derived from the registry category."""

    def test_read_tool_has_read_only_hint(self, tool_map):
        annotations = tool_map["models_get_model"].annotations
        assert annotations is not None
        assert annotations.readOnlyHint is True
        assert annotations.destructiveHint is not True

    def test_write_tool_has_destructive_hint(self, tool_map):
        annotations = tool_map["models_train_model"].annotations
        assert annotations is not None
        assert annotations.destructiveHint is True
        assert annotations.readOnlyHint is not True

    def test_every_tool_annotated_by_category(self, tool_map):
        for entry in iter_registry_entries():
            name = derive_tool_name(entry)
            annotations = tool_map[name].annotations
            assert annotations is not None, name
            if entry["category"].value == "read":
                assert annotations.readOnlyHint is True, name
            else:
                assert annotations.destructiveHint is True, name

    def test_unknown_category_raises(self):
        category = MagicMock()
        category.value = "banana"
        with pytest.raises(ValueError, match="Unknown registry category: 'banana'"):
            compute_annotations({"category": category})


class TestRegistration:
    def test_registers_all_registry_tools(self, tool_map):
        assert len(tool_map) == len(iter_registry_entries()) == 36

    def test_signature_copied(self, tool_map):
        t = tool_map["models_train_model"]
        props = t.parameters["properties"]
        assert "dataset_id" in props
        assert "self" not in props
        assert len(props) == 11
        assert set(t.parameters["required"]) == {
            "dataset_id",
            "target_column",
            "model_name",
        }

    def test_docstring_copied(self, tool_map):
        assert tool_map["models_train_model"].description

    def test_tags_applied_on_registered_tool(self, tool_map):
        assert tool_map["models_train_model"].tags == {"write"}
        assert tool_map["models_get_model"].tags == {"read"}

    def test_wrapper_calls_client_method(self, tool_map):
        mock_client = MagicMock()
        mock_client.models.get_model.return_value = {"model_id": "m1"}
        with patch(
            "xplainable_mcp.runtime_tools.get_client", return_value=mock_client
        ):
            result = asyncio.run(tool_map["models_get_model"].fn(model_id="m1"))
        mock_client.models.get_model.assert_called_once_with(model_id="m1")
        assert result == {"model_id": "m1"}

    def test_wrapper_model_dumps_pydantic(self, tool_map):
        obj = MagicMock()
        obj.model_dump.return_value = {"ok": True}
        mock_client = MagicMock()
        mock_client.models.get_model.return_value = obj
        with patch(
            "xplainable_mcp.runtime_tools.get_client", return_value=mock_client
        ):
            assert asyncio.run(
                tool_map["models_get_model"].fn(model_id="m1")
            ) == {"ok": True}

    def test_wrapper_model_dumps_list_of_pydantic(self, tool_map):
        obj = MagicMock()
        obj.model_dump.return_value = {"ok": True}
        mock_client = MagicMock()
        mock_client.models.list_team_models.return_value = [obj, obj]
        with patch(
            "xplainable_mcp.runtime_tools.get_client", return_value=mock_client
        ):
            result = asyncio.run(tool_map["models_list_team_models"].fn())
        assert result == [{"ok": True}, {"ok": True}]

    def test_duplicate_name_raises(self):
        entry = _entry_for("models_get_model")
        with patch(
            "xplainable_mcp.runtime_tools.iter_registry_entries",
            return_value=[entry, entry],
        ):
            with pytest.raises(RuntimeError, match="Duplicate"):
                register_client_tools(FastMCP(name="dupe"))
