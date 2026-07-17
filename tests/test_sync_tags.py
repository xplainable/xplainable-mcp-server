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
