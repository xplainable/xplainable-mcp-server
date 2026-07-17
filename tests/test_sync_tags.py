"""Tests for tag emission and module scanning in scripts/sync_workflow.py.

Covers the C1 tag-gating work:
- generated ``@mcp.tool`` decorators carry ``tags={...}`` built from the
  method's category plus an optional ``curated`` marker;
- discovery records the new ``_mcp_curated`` marker (default False);
- the class scanner ignores classes *imported into* a client module (the
  client's workflow.py imports 8 sub-client classes at module top-level,
  which would otherwise be re-emitted as bogus ``workflow_*`` tools).
"""

import importlib.util
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def sync_workflow():
    """Import scripts/sync_workflow.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "sync_workflow", REPO_ROOT / "scripts" / "sync_workflow.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _method_info(**overrides):
    info = {
        "module": "workflow",
        "class": "WorkflowClient",
        "method": "zz_fake_method",
        "mcp_name": "workflow_zz_fake_method",
        "category": "workflow",
        "curated": True,
        "signature": "(self, dataset_id: str)",
        "docstring": "Fake method for testing.",
        "step": 0,
        "depends_on": [],
    }
    info.update(overrides)
    return info


class _FakeCategory:
    """Mimics the client's McpCategory enum members (scan reads .value)."""

    def __init__(self, value):
        self.value = value


def _fake_method(name, category=None, curated=None):
    def method(self, x: str):
        """Fake docstring."""

    method.__name__ = name
    method._is_mcp_tool = True
    if category is not None:
        method._mcp_category = _FakeCategory(category)
    if curated is not None:
        method._mcp_curated = curated
    return method


def _make_client_class(class_name, module_name, methods):
    cls = type(class_name, (), {m.__name__: m for m in methods})
    cls.__module__ = module_name
    return cls


class TestDiscoveryCuratedFlag:
    def test_curated_defaults_to_false_when_marker_absent(self, sync_workflow):
        module = types.ModuleType("fake_pkg.reads")
        module.ReadsClient = _make_client_class(
            "ReadsClient", "fake_pkg.reads", [_fake_method("get_thing", category="read")]
        )

        infos = sync_workflow.scan_module_for_mcp_methods("reads", module)

        assert len(infos) == 1
        assert infos[0]["curated"] is False
        assert infos[0]["category"] == "read"

    def test_curated_true_when_marker_set(self, sync_workflow):
        module = types.ModuleType("fake_pkg.reads")
        module.ReadsClient = _make_client_class(
            "ReadsClient",
            "fake_pkg.reads",
            [_fake_method("get_thing", category="read", curated=True)],
        )

        infos = sync_workflow.scan_module_for_mcp_methods("reads", module)

        assert len(infos) == 1
        assert infos[0]["curated"] is True


class TestScannerSkipsImportedClasses:
    def test_only_locally_defined_client_classes_are_scanned(self, sync_workflow):
        # ForeignClient is defined in fake_pkg.models but imported into
        # fake_pkg.workflow (like WorkflowClient importing 8 sub-clients).
        foreign_module = types.ModuleType("fake_pkg.models")
        foreign_module.ModelsClient = _make_client_class(
            "ModelsClient",
            "fake_pkg.models",
            [_fake_method("train_model", category="write")],
        )

        workflow_module = types.ModuleType("fake_pkg.workflow")
        workflow_module.WorkflowClient = _make_client_class(
            "WorkflowClient",
            "fake_pkg.workflow",
            [_fake_method("wf_train_model", category="workflow", curated=True)],
        )
        # Simulate top-level `from .models import ModelsClient` in workflow.py
        workflow_module.ModelsClient = foreign_module.ModelsClient

        infos = sync_workflow.scan_module_for_mcp_methods("workflow", workflow_module)

        names = [i["mcp_name"] for i in infos]
        assert names == ["workflow_wf_train_model"], (
            "imported ModelsClient must not be re-emitted as workflow_* tools"
        )


class TestWorkflowDependsOnPrefixing:
    def test_already_prefixed_depends_on_is_not_double_prefixed(self, sync_workflow):
        # The client's workflow.py declares depends_on with full tool names
        # (e.g. "workflow_train_model"); the generator must not prefix again.
        code = sync_workflow.generate_tool_implementation(
            _method_info(step=5, depends_on=["workflow_train_model"])
        )
        assert "Run after: workflow_train_model." in code
        assert "workflow_workflow_train_model" not in code

    def test_bare_method_depends_on_still_gets_module_prefix(self, sync_workflow):
        # Other client modules (deployments, reports) declare bare method
        # names (e.g. "deploy"), which must still be prefixed to full tool names.
        code = sync_workflow.generate_tool_implementation(
            _method_info(
                module="deployments",
                method="zz_fake_method",
                mcp_name="deployments_zz_fake_method",
                step=3,
                depends_on=["deploy"],
            )
        )
        assert "Run after: deployments_deploy." in code


class TestGenerateToolTags:
    def test_workflow_curated_emits_both_tags_sorted(self, sync_workflow):
        code = sync_workflow.generate_tool_implementation(
            _method_info(category="workflow", curated=True)
        )
        assert '@mcp.tool(icons=[XP_ICON], tags={"curated", "workflow"})' in code

    def test_read_uncurated_emits_only_category_tag(self, sync_workflow):
        code = sync_workflow.generate_tool_implementation(
            _method_info(category="read", curated=False)
        )
        assert '@mcp.tool(icons=[XP_ICON], tags={"read"})' in code
        assert '"curated"' not in code
