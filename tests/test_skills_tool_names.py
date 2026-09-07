"""Every tool the bundled skills tell an agent to call must exist on the surface.

The skills went stale silently once (v1 refit loop, deleted monitors_* tools,
bare names without the client-family prefix). This pins each `name(` the
skills mention that looks like a tool against the live registry plus the
server-native tools, so a surface change that orphans a skill fails CI.
"""
import re
from pathlib import Path

import pytest

from xplainable_mcp.runtime_tools import derive_tool_name, iter_registry_entries

SKILLS_DIR = Path(__file__).parent.parent / "xplainable_mcp" / "skills"
SERVER_NATIVE_TOOLS = {
    "list_user_teams", "set_active_team", "select_team",
    "docs_list_pages", "docs_get_page", "docs_search",
}
TOOL_FAMILIES = (
    "autotrain_", "datasets_", "deployments_", "docs_", "gpt_", "inference_",
    "misc_", "models_", "monitors_", "optimisers_", "preprocessing_", "reports_",
)


def _surface():
    return {derive_tool_name(e) for e in iter_registry_entries()} | SERVER_NATIVE_TOOLS


def _mentioned(text):
    names = set(re.findall(r"\b([a-z]+_[a-z_]+)\s*\(", text))
    return {n for n in names if n.startswith(TOOL_FAMILIES) or n in SERVER_NATIVE_TOOLS}


@pytest.mark.parametrize("skill", sorted(p.name for p in SKILLS_DIR.glob("*.md")))
def test_skill_only_cites_tools_on_the_surface(skill):
    text = (SKILLS_DIR / skill).read_text()
    unknown = sorted(_mentioned(text) - _surface())
    assert not unknown, f"{skill} cites tools that are not on the surface: {unknown}"


@pytest.mark.parametrize("skill", sorted(p.name for p in SKILLS_DIR.glob("*.md")))
def test_skill_uses_prefixed_tool_names(skill):
    """Bare `train_model(` / `refit_model(` style calls are not tool names."""
    text = (SKILLS_DIR / skill).read_text()
    bare = sorted(set(re.findall(r"(?<![a-z_])(train_model|refit_model|refit_features|"
                                  r"get_model_profile|get_feature_info|get_model_evaluation)\s*\(",
                                  text)))
    assert not bare, f"{skill} uses unprefixed tool names: {bare}"


def test_skills_mention_the_v2_iteration_primitive():
    text = (SKILLS_DIR / "xplainable-best-practices.md").read_text()
    assert "models_refit_features" in text
    assert "max_depth=" not in text  # v1 hyperparameter; never shown as a call argument
