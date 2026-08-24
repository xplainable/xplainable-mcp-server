# Runtime Tool Generation & Direct-Mode Surface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Replace the checked-in codegen'd MCP tool modules with runtime tool generation from the client's `@mcp_tool` registry, and restructure the tool surface into three tiers (direct / guided / advanced) with INSTRUCTIONS rewritten around the direct train → inspect → refit loop.

**Architecture:** A new `xplainable_mcp/runtime_tools.py` introspects the installed `xplainable-client`'s `_MCP_REGISTRY` at server startup and registers one FastMCP tool per entry (wrapper closure + copied `__signature__`). Server-side overlay constants demote the agentic trio to a `guided` tag and promote three preprocessing tools to `curated`. `include_tags` selects the tier: `{"curated"}` (default direct), `{"curated","guided"}` (XPLAINABLE_GUIDED_TOOLS), `None` (XPLAINABLE_ADVANCED_TOOLS). All codegen machinery (sync_workflow.py, tool_manager.py, tool_discovery.py, 15 generated tool modules) is deleted; docs generation and `list_tools`/`get_workflows` are rewritten on top of the live registries.

**Tech Stack:** Python 3.11, fastmcp 2.14.7, xplainable-client 1.13.0 (editable from `/Users/jtuppack/projects/xplainable-client/.worktrees/feat-train-primitive`), pytest + pytest-asyncio.

**Working directory:** `/Users/jtuppack/projects/xplainable-mcp-server/.worktrees/feat-direct-mode` (branch `feat/direct-mode-surface`). Test with `.venv/bin/python -m pytest`.

---

## Verified facts (spikes already run — do not re-derive)

1. **Client registry:** `from xplainable_client.client.utils.mcp_markers import get_mcp_registry` returns a dict of 98 entries keyed by `module.QualName.method`. Each entry: `{function, name, signature, docstring, category (MCPCategory enum), parameters, module_path, qualname, step, depends_on, curated}`. Importing `xplainable_client.client.client` triggers full registration (all sub-client modules import). 29 entries have `curated=True`. No registered tool has a DataFrame/non-serializable parameter.
2. **Sub-client attribute derivation:** `qualname` is `<Class>Client.<method>` (e.g. `ModelsClient.train_model`). `class_name.replace("Client","").lower()` matches the attribute on `XplainableClient` for ALL registered classes (`models`, `deployments`, `preprocessing`, `monitors`, `datasets`, `inference`, `gpt`, `autotrain`, `misc`, `runs`, `reports`, `agentic`, `optimisers`, `workflow`).
3. **FastMCP runtime registration works:** `mcp.tool(wrapper, name=..., tags=..., icons=[XP_ICON])` returns a `FunctionTool`; JSON schema is built from `wrapper.__signature__` (verified: required vs optional params correct for `models_train_model`'s 11 params). Test call paths: `tool.fn(...)` directly (sync), or in-memory `async with Client(mcp) as c: await c.call_tool(name, args)`.
4. **fastmcp 2.14.7 breaks the old tests:** module attributes decorated with `@mcp.tool` are `FunctionTool` objects, not callables → 30 of 63 existing tests fail at HEAD (pre-existing; CI never runs pytest). Tests calling e.g. `models_tools.models_get_model("m1")` must be reworked to `.fn` / in-memory client calls.
5. **Hand-written tools in server.py:** `select_team`, `set_active_team`, `list_user_teams` (tags `{"admin","curated"}`), `workflow_get_run_charts` (tags `{"curated","workflow"}`), `list_tools` + `get_workflows` (untagged → advanced-only; both depend on `tool_discovery`). `xplainable_mcp/tools/docs.py` is hand-written (3 async docs tools, httpx-based, untagged) — must survive the tools/ package deletion.
6. **Skills** (`xplainable_mcp/skills/*.md`) reference no `workflow_*` tool names — no skill edits needed.
7. **Guided trio names:** `workflow_train_model`, `workflow_wait_for_update`, `workflow_decide`. The other six workflow tools stay curated.
8. **`get_client()`** lives in `xplainable_mcp/client_manager.py`; server.py re-exports it. `XP_ICON` is defined in server.py:84. To avoid circular imports, runtime_tools must import `get_client` from `client_manager` and take the icon as a parameter (or define its own).

## Expected surface counts (encode in tests as relationships, not all as literals)

- Runtime-registered: 98.
- Curated runtime tools after overlays: 29 (client-curated) − 3 (guided trio demoted) + 3 (preprocessing promotions) = 29.
- Direct default (`{"curated"}`): 29 + 4 hand-written curated (3 team tools + `workflow_get_run_charts`) = **33 tools**.
- Guided (`{"curated","guided"}`): 33 + 3 = **36 tools**.
- Advanced (`None`): 98 + all hand-written (team tools, charts, list_tools, get_workflows, 3 docs tools, plus any other untagged server tools) — assert `>= 105` and `advanced ⊇ guided ⊇ direct`.

---

### Task 1: Runtime tool generator (`xplainable_mcp/runtime_tools.py`)

**Files:**
- Create: `xplainable_mcp/runtime_tools.py`
- Create: `tests/test_runtime_tools.py`

**Step 1: Write failing tests** in `tests/test_runtime_tools.py`:

```python
"""Tests for runtime tool generation from the xplainable-client @mcp_tool registry."""

import inspect
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from xplainable_mcp.runtime_tools import (
    CURATED_PROMOTIONS,
    GUIDED_TOOLS,
    compute_tags,
    derive_tool_name,
    iter_registry_entries,
    register_client_tools,
)


@pytest.fixture()
def registered_mcp():
    mcp = FastMCP(name="test")  # no include_tags: register everything
    register_client_tools(mcp)
    return mcp


async def get_tool_map(mcp):
    return await mcp.get_tools()


class TestNaming:
    def test_derive_tool_name_from_qualname(self):
        entry = {"qualname": "ModelsClient.get_model", "name": "get_model"}
        assert derive_tool_name(entry) == "models_get_model"

    def test_all_registry_names_unique(self):
        names = [derive_tool_name(e) for e in iter_registry_entries()]
        assert len(names) == len(set(names))


class TestTags:
    def test_plain_read_tool(self):
        entry = _entry_for("models_get_model")
        assert compute_tags("models_get_model", entry) == {"read"}

    def test_curated_tool_gets_curated_tag(self):
        entry = _entry_for("models_train_model")
        assert compute_tags("models_train_model", entry) == {"write", "curated"}

    def test_guided_trio_demoted(self):
        for name in GUIDED_TOOLS:
            entry = _entry_for(name)
            tags = compute_tags(name, entry)
            assert tags == {"workflow", "guided"}, name
            assert "curated" not in tags

    def test_mechanical_workflow_tools_stay_curated(self):
        for name in ("workflow_deploy_model", "workflow_list_assets",
                     "workflow_predict", "workflow_create_report",
                     "workflow_optimise_model", "workflow_explain_model"):
            assert compute_tags(name, _entry_for(name)) == {"workflow", "curated"}, name

    def test_preprocessing_promotions(self):
        for name in CURATED_PROMOTIONS:
            assert "curated" in compute_tags(name, _entry_for(name)), name


class TestRegistration:
    @pytest.mark.asyncio
    async def test_registers_all_registry_tools(self, registered_mcp):
        tools = await get_tool_map(registered_mcp)
        assert len(tools) == len(list(iter_registry_entries()))

    @pytest.mark.asyncio
    async def test_signature_copied(self, registered_mcp):
        tools = await get_tool_map(registered_mcp)
        t = tools["models_train_model"]
        props = t.parameters["properties"]
        assert "dataset_id" in props and "self" not in props
        assert set(t.parameters["required"]) == {"dataset_id", "target_column", "model_name"}

    @pytest.mark.asyncio
    async def test_docstring_copied(self, registered_mcp):
        tools = await get_tool_map(registered_mcp)
        assert tools["models_train_model"].description

    @pytest.mark.asyncio
    async def test_wrapper_calls_client_method(self, registered_mcp):
        tools = await get_tool_map(registered_mcp)
        mock_client = MagicMock()
        mock_client.models.get_model.return_value = {"model_id": "m1"}
        with patch("xplainable_mcp.runtime_tools.get_client", return_value=mock_client):
            result = tools["models_get_model"].fn(model_id="m1")
        mock_client.models.get_model.assert_called_once_with(model_id="m1")
        assert result == {"model_id": "m1"}

    @pytest.mark.asyncio
    async def test_wrapper_model_dumps_pydantic(self, registered_mcp):
        tools = await get_tool_map(registered_mcp)
        obj = MagicMock()
        obj.model_dump.return_value = {"ok": True}
        mock_client = MagicMock()
        mock_client.models.get_model.return_value = obj
        with patch("xplainable_mcp.runtime_tools.get_client", return_value=mock_client):
            assert tools["models_get_model"].fn(model_id="m1") == {"ok": True}


def _entry_for(tool_name):
    for e in iter_registry_entries():
        if derive_tool_name(e) == tool_name:
            return e
    raise AssertionError(f"{tool_name} not in registry")
```

**Step 2: Run** `.venv/bin/python -m pytest tests/test_runtime_tools.py -q` — expect ImportError (module missing).

**Step 3: Implement** `xplainable_mcp/runtime_tools.py`:

```python
"""Runtime MCP tool generation from the xplainable-client @mcp_tool registry.

Replaces the old checked-in codegen (scripts/sync_workflow.py + tools/*.py).
The installed client is the single source of truth: every method decorated
with @mcp_tool is registered as a FastMCP tool at server startup, so a client
upgrade is automatically reflected in the tool surface (no sync PR).
"""

import inspect
import logging

from mcp.types import Icon

from .client_manager import get_client

logger = logging.getLogger(__name__)

XP_ICON = Icon(src="https://xplainable.io/assets/xplainable-icon.png", mimeType="image/png")

# Server-side tag overlays
# ------------------------
# The agentic trio delegates orchestration to the server-side pipeline
# (guided mode). It is opt-in via XPLAINABLE_GUIDED_TOOLS, not curated.
GUIDED_TOOLS = frozenset({
    "workflow_train_model",
    "workflow_wait_for_update",
    "workflow_decide",
})

# Preprocessing tools promoted into the curated (direct-mode) surface so
# Claude can author, preview, and apply preprocessing before training.
CURATED_PROMOTIONS = frozenset({
    "preprocessing_list_available_transformers",
    "preprocessing_create_preprocessor_from_spec",
    "preprocessing_preview_from_data",
})


def iter_registry_entries():
    """Yield @mcp_tool registry entries from the installed client."""
    # Importing the aggregate client module imports every sub-client module,
    # which populates the global registry as a side effect.
    import xplainable_client.client.client  # noqa: F401
    from xplainable_client.client.utils.mcp_markers import get_mcp_registry

    return list(get_mcp_registry().values())


def derive_tool_name(entry) -> str:
    """ModelsClient.get_model -> models_get_model (matches XplainableClient attrs)."""
    class_name = entry["qualname"].split(".")[0]
    module_attr = class_name.replace("Client", "").lower()
    return f"{module_attr}_{entry['name']}"


def compute_tags(tool_name: str, entry) -> set:
    if tool_name in GUIDED_TOOLS:
        return {entry["category"].value, "guided"}
    tags = {entry["category"].value}
    if entry["curated"] or tool_name in CURATED_PROMOTIONS:
        tags.add("curated")
    return tags


def _dump(result):
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, list) and result and hasattr(result[0], "model_dump"):
        return [item.model_dump() for item in result]
    return result


def _build_wrapper(entry, tool_name: str, module_attr: str):
    method_name = entry["name"]

    def wrapper(**kwargs):
        client = get_client()
        method = getattr(getattr(client, module_attr), method_name)
        result = method(**kwargs)
        logger.info("Executed %s.%s", module_attr, method_name)
        return _dump(result)

    params = [p for n, p in entry["signature"].parameters.items() if n not in ("self", "cls")]
    wrapper.__signature__ = entry["signature"].replace(parameters=params)
    wrapper.__name__ = tool_name
    wrapper.__doc__ = entry["docstring"]
    fn = entry["function"]
    wrapper.__annotations__ = {
        k: v for k, v in getattr(fn, "__annotations__", {}).items() if k != "return"
    }
    return wrapper


def register_client_tools(mcp) -> int:
    """Register every client @mcp_tool method as a FastMCP tool. Returns count."""
    entries = iter_registry_entries()
    seen = set()
    for entry in entries:
        tool_name = derive_tool_name(entry)
        if tool_name in seen:
            raise RuntimeError(f"Duplicate runtime tool name: {tool_name}")
        seen.add(tool_name)
        module_attr = entry["qualname"].split(".")[0].replace("Client", "").lower()
        wrapper = _build_wrapper(entry, tool_name, module_attr)
        mcp.tool(
            wrapper,
            name=tool_name,
            tags=compute_tags(tool_name, entry),
            icons=[XP_ICON],
        )
    logger.info("Registered %d runtime tools from xplainable-client registry", len(entries))
    return len(entries)
```

Note: FastMCP filters by `include_tags` at *listing* time, not registration time, so registering everything and letting `include_tags` gate the surface is correct.

**Step 4: Run** `.venv/bin/python -m pytest tests/test_runtime_tools.py -q` — expect all pass.

**Step 5: Commit** — `feat: runtime MCP tool generation from client @mcp_tool registry`

---

### Task 2: Three-tier include_tags in mcp_instance.py

**Files:**
- Modify: `xplainable_mcp/mcp_instance.py` (`resolve_include_tags`, lines 18-27, and the call at line 116)
- Modify: `tests/test_tag_gating.py`

**Step 1: Update tests.** `tests/test_tag_gating.py` currently tests the two-tier `resolve_include_tags(env_value)`. Rewrite for the new signature `resolve_include_tags(advanced, guided)`:

```python
from xplainable_mcp.mcp_instance import resolve_include_tags

def test_default_is_curated_only():
    assert resolve_include_tags(None, None) == {"curated"}

def test_default_excludes_workflow_tag():
    # "workflow" must NOT be in default tags or the demoted guided trio
    # (still tagged "workflow") would leak back into the direct surface.
    assert "workflow" not in resolve_include_tags(None, None)

def test_guided_adds_guided_tag():
    for v in ("1", "true", "yes", "TRUE", " Yes "):
        assert resolve_include_tags(None, v) == {"curated", "guided"}

def test_advanced_returns_none():
    for v in ("1", "true", "yes"):
        assert resolve_include_tags(v, None) is None

def test_advanced_wins_over_guided():
    assert resolve_include_tags("1", "1") is None

def test_falsy_values_stay_default():
    for v in ("", "0", "false", "no", None):
        assert resolve_include_tags(v, v) == {"curated"}
```

**Step 2: Run** — expect failures (signature mismatch).

**Step 3: Implement** in `mcp_instance.py`:

```python
def _truthy(env_value: Optional[str]) -> bool:
    return (env_value or "").strip().lower() in ("1", "true", "yes")


def resolve_include_tags(advanced: Optional[str], guided: Optional[str]) -> Optional[set]:
    """Resolve FastMCP include_tags for the three-tier tool surface.

    - default: direct mode — curated tools only (~33)
    - XPLAINABLE_GUIDED_TOOLS truthy: adds the guided agentic trio (~36)
    - XPLAINABLE_ADVANCED_TOOLS truthy: no filtering — full surface (~105)
    """
    if _truthy(advanced):
        return None
    if _truthy(guided):
        return {"curated", "guided"}
    return {"curated"}
```

And the FastMCP call becomes:

```python
    include_tags=resolve_include_tags(
        os.getenv("XPLAINABLE_ADVANCED_TOOLS"),
        os.getenv("XPLAINABLE_GUIDED_TOOLS"),
    ),
```

Also update `tests/conftest.py` to clear `XPLAINABLE_GUIDED_TOOLS` alongside `XPLAINABLE_ADVANCED_TOOLS`.

**Step 4: Run** `tests/test_tag_gating.py` — pass.

**Step 5: Commit** — `feat: three-tier tool surface (direct/guided/advanced) via include_tags`

---

### Task 3: Wire runtime tools into server; delete codegen machinery

This is the big deletion. Do it in one task so the tree never half-references dead modules.

**Files:**
- Modify: `xplainable_mcp/server.py`
- Move: `xplainable_mcp/tools/docs.py` → `xplainable_mcp/docs_tools.py` (fix relative imports: `from .mcp_instance import mcp`; define its own `XP_ICON` or import from `runtime_tools`)
- Delete: `xplainable_mcp/tools/` (entire package), `xplainable_mcp/tool_manager.py`, `xplainable_mcp/tool_discovery.py`, `scripts/sync_workflow.py`, `tests/test_tool_manager.py`, `tests/test_sync_tags.py`
- Modify: `xplainable_mcp/cli.py`
- Modify: `pyproject.toml` (client pin)

**Step 1: server.py changes:**

1. Line 84: keep `XP_ICON` (hand-written tools use it) but import it from `runtime_tools` instead of redefining: `from .runtime_tools import XP_ICON, register_client_tools`.
2. Line 86-87: replace `from . import __version__, tools` with `from . import __version__` and add, immediately after the hand-written tool definitions (end of module, before `main()`):
   ```python
   # Register all client @mcp_tool methods as MCP tools (runtime generation)
   register_client_tools(mcp)
   # Hand-written docs tools (self-register on import)
   from . import docs_tools  # noqa: E402,F401
   ```
3. **Rewrite `get_workflows`** (lines 585-~680) on the client registry instead of AST docstring-parsing — the registry has `step` and `depends_on` natively:
   ```python
   @mcp.tool(icons=[XP_ICON])
   def get_workflows() -> Dict[str, Any]:
       """Get available tool workflows grouped by service with execution order. ..."""
       from .runtime_tools import derive_tool_name, iter_registry_entries

       services: Dict[str, Dict[str, Any]] = {}
       for entry in iter_registry_entries():
           tool_name = derive_tool_name(entry)
           service = tool_name.split("_", 1)[0]
           bucket = services.setdefault(service, {"steps": [], "tools": []})
           item = {
               "tool": tool_name,
               "description": (entry["docstring"] or "").strip().splitlines()[0] if entry["docstring"] else "",
               "category": entry["category"].value,
               "parameters": list(entry["parameters"].keys()),
           }
           if entry["step"]:
               item["step"] = entry["step"]
           if entry["depends_on"]:
               item["depends_on"] = entry["depends_on"]
           bucket["steps" if entry["step"] else "tools"].append(item)
       for data in services.values():
           data["steps"].sort(key=lambda x: x["step"])
           for key in ("steps", "tools"):
               if not data[key]:
                   del data[key]
       return {"services": services}
   ```
4. **Rewrite `list_tools`** (lines 510-583) on the live FastMCP registry (`mcp` is sync context here; FastMCP exposes tools via async `get_tools()` — make the tool `async def`):
   ```python
   @mcp.tool(icons=[XP_ICON])
   async def list_tools() -> Dict[str, Any]:
       """List all registered MCP tools grouped by tag/category."""
       tools = await mcp.get_tools()
       categories: Dict[str, list] = {}
       for name, tool in sorted(tools.items()):
           tags = tool.tags or set()
           category = next((t for t in ("read", "write", "workflow", "analysis",
                                        "inference", "admin") if t in tags), "other")
           categories.setdefault(category, []).append({
               "name": name,
               "description": (tool.description or "").strip().splitlines()[0] if tool.description else "",
               "tags": sorted(tags),
           })
       return {
           "server_version": __version__,
           "total_tools": len(tools),
           "categories": categories,
       }
   ```
   Delete the now-orphaned helpers `_get_tool_docstring` and the "dynamic tool discovery" fallback block (~lines 400-507) if nothing else references them (grep first).
5. Delete any remaining `tool_discovery`/`tool_manager` imports.

**Step 2: cli.py.** `cmd_list_tools` and `cmd_generate_docs` import `tool_discovery`. Rewrite both on `iter_registry_entries()`/`derive_tool_name` (list: name, category, curated flag; docs: defer to scripts/generate_mcp_docs.py or print the same listing as markdown). Keep it minimal — these are dev conveniences.

**Step 3: pyproject.toml:** bump `"xplainable-client>=1.12.0"` → `"xplainable-client>=1.13.0"`. (CI installs from PyPI and will fail until client 1.13.0 is released — expected; note in PR description.)

**Step 4: Delete files:**
```bash
git rm -r xplainable_mcp/tools scripts/sync_workflow.py \
  xplainable_mcp/tool_manager.py xplainable_mcp/tool_discovery.py \
  tests/test_tool_manager.py tests/test_sync_tags.py
```
(`git mv xplainable_mcp/tools/docs.py xplainable_mcp/docs_tools.py` BEFORE the rm.)

**Step 5: Sanity check:** `.venv/bin/python -c "import xplainable_mcp.server"` imports cleanly, and:
```bash
.venv/bin/python - <<'EOF'
import asyncio, os
os.environ["XPLAINABLE_API_KEY"] = "test"
from xplainable_mcp.server import mcp
print(len(asyncio.run(mcp.get_tools())))
EOF
```
Expect 33 by default (see counts table); with `XPLAINABLE_ADVANCED_TOOLS=1` expect >= 105.

**Step 6: Run full suite** `.venv/bin/python -m pytest -q`. test_server.py/test_agentic_tools.py will still fail (fixed in Task 4). New/updated tests must pass.

**Step 7: Commit** — `feat: wire runtime tool generation into server; remove codegen machinery`

---

### Task 4: Repair the test suite (pre-existing fastmcp 2.14.7 breakage)

**Files:**
- Modify: `tests/test_server.py`, `tests/test_agentic_tools.py`, `tests/conftest.py`
- Create: `tests/test_surface.py`

**Step 1:** Rework every test that calls a `@mcp.tool`-decorated attribute directly. Pattern:

```python
# OLD (broken since fastmcp 2.x):
result = models_tools.models_get_model("model-1")

# NEW: fetch from the FastMCP registry and call .fn with kwargs
import asyncio
from xplainable_mcp.mcp_instance import mcp

def get_tool(name):
    return asyncio.get_event_loop().run_until_complete(mcp.get_tools())[name]
# (or a small async fixture with pytest-asyncio)

tool = get_tool("models_get_model")
with patch("xplainable_mcp.runtime_tools.get_client", return_value=mock_client):
    result = tool.fn(model_id="model-1")
```

Key change: runtime tools patch `xplainable_mcp.runtime_tools.get_client`; hand-written server tools still patch `xplainable_mcp.server.get_client`. Tests referencing deleted generated modules (`from xplainable_mcp.tools import models as models_tools`) import from the registry instead. Delete tests that only exercised codegen internals.

conftest.py must set `XPLAINABLE_API_KEY` before importing server (already does) and clear both surface env vars.

**Step 2: New surface invariants** in `tests/test_surface.py`:

```python
import pytest
from fastmcp import FastMCP
from xplainable_mcp.mcp_instance import resolve_include_tags
from xplainable_mcp.runtime_tools import GUIDED_TOOLS


async def _names(include_tags):
    # Import the fully-wired server mcp and re-filter
    from xplainable_mcp.server import mcp
    saved = mcp.include_tags
    mcp.include_tags = include_tags
    try:
        return set((await mcp.get_tools()).keys())
    finally:
        mcp.include_tags = saved


@pytest.mark.asyncio
async def test_direct_surface():
    direct = await _names(resolve_include_tags(None, None))
    assert "models_train_model" in direct
    assert "models_refit_model" in direct
    assert "reports_get_job_status" in direct
    assert "preprocessing_create_preprocessor_from_spec" in direct
    assert "workflow_deploy_model" in direct
    assert GUIDED_TOOLS.isdisjoint(direct)
    assert len(direct) == 33


@pytest.mark.asyncio
async def test_guided_adds_exactly_the_trio():
    direct = await _names(resolve_include_tags(None, None))
    guided = await _names(resolve_include_tags(None, "1"))
    assert guided - direct == set(GUIDED_TOOLS)


@pytest.mark.asyncio
async def test_advanced_superset():
    guided = await _names(resolve_include_tags(None, "1"))
    advanced = await _names(resolve_include_tags("1", None))
    assert guided < advanced
    assert len(advanced) >= 105
```

(Verify `mcp.include_tags` is the actual FastMCP attribute name for filter mutation; if not settable, build the surface test by constructing fresh `FastMCP(include_tags=...)` instances and re-registering — the runtime generator makes that cheap.)

**Step 3: Run full suite** — `.venv/bin/python -m pytest -q` — expect **0 failures**.

**Step 4: Commit** — `test: repair suite for fastmcp 2.x FunctionTool API; add surface invariants`

---

### Task 5: INSTRUCTIONS rewrite (direct-mode iterate loop)

**Files:**
- Modify: `xplainable_mcp/mcp_instance.py` (INSTRUCTIONS, lines 54-101)

**Step 1: Replace INSTRUCTIONS with:**

```python
INSTRUCTIONS = """\
Xplainable trains inherently explainable ML models server-side. You are the \
orchestrator: analyse the data, decide the preprocessing and features, train, \
inspect, and iterate. Compute always runs on the Xplainable platform — never \
train locally.

If a tool returns 'No team selected', set an active team first (select_team \
/ set_active_team, or the XPLAINABLE_TEAM_ID environment variable).

## The Iterate Loop

1. `workflow_list_assets` — see the team's datasets, models, and deployments.
2. `datasets_preview_dataset_json(dataset_id)` — inspect columns, types, and \
sample rows. Decide the target column, columns to drop (IDs, leakage), and \
whether preprocessing is needed.
3. (Optional) preprocessing: `preprocessing_list_available_transformers` → \
`preprocessing_create_preprocessor_from_spec(name, spec, sample_data)` → \
`preprocessing_preview_from_data(version_id, sample_data)` to verify the \
transformed output before training.
4. `models_train_model(dataset_id, target_column, model_name, ...)` — \
synchronous server-side training (may take up to a couple of minutes). \
Returns model_id, version_id, train/test metrics, and feature importances.
5. Inspect: compare train vs test metrics (a large gap = overfitting). Use \
`models_get_feature_info(version_id)` for feature health and \
`models_get_model_profile` / `workflow_explain_model` for contributions.
6. Iterate:
   - Hyperparameter tuning → `models_refit_model` (cheap, same structure).
   - Different features / preprocessing / target → `models_train_model` again.
   Narrate what you changed and why; show the user the metric movement.
7. `workflow_deploy_model(model_id)` — deploy once satisfied.
8. Act on the model:
   - `workflow_predict` — score rows (no deployment needed).
   - `workflow_optimise_model` — prescriptive optimisation toward an objective.
   - `workflow_create_report` — starts report generation; poll \
`reports_get_job_status(job_id)` until status is 'done'.

Read tools (datasets_*, models_*, deployments_*, optimisers_*, runs_*, \
agentic_*, misc_get_organisation_usage) are available for inspecting assets \
at any point.

## Guided Mode (opt-in)

Set `XPLAINABLE_GUIDED_TOOLS=1` to expose workflow_train_model / \
workflow_wait_for_update / workflow_decide: a hands-off run of the same \
agentic pipeline that powers the Xplainable platform UI. Prefer the direct \
loop above when available — it keeps you in control of every decision.

## Advanced Tool Surface

Set `XPLAINABLE_ADVANCED_TOOLS=1` to expose the full surface (~105 tools) \
including write/admin tools for monitors, GPT reports, inference, and \
low-level agentic run control.

## Available Skills

Pin a skill resource to your project for domain-specific workflow guidance. \
Available skills can be discovered via the MCP resources panel.
"""
```

**Step 2:** Verify server still imports and default surface count unchanged; run full suite.

**Step 3: Commit** — `feat: rewrite INSTRUCTIONS around the direct train→inspect→refit loop`

---

### Task 6: Docs generation + CI on the live registry

**Files:**
- Modify: `scripts/generate_mcp_docs.py` (full rewrite, much smaller)
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/update-mcp-docs.yml`

**Step 1: Rewrite `scripts/generate_mcp_docs.py`.** Replace AST parsing of `tools/*.py` with introspection: set `XPLAINABLE_API_KEY=docs-build` + `XPLAINABLE_ADVANCED_TOOLS=1`, import `xplainable_mcp.server.mcp`, `asyncio.run(mcp.get_tools())`, and emit the same `tools.mdx` structure (name, description, params from `tool.parameters` JSON schema, tags incl. curated/guided markers). Preserve the existing CLI (`--output` flag) so update-mcp-docs.yml keeps working. Keep output format compatible with the docs site (check current script's frontmatter/section layout and reproduce it).

**Step 2: ci.yml:**
- Remove `py_compile` lines for deleted files (tool_manager.py, tool_discovery.py, sync_workflow.py) and the `from xplainable_mcp.tool_discovery import ...` validation; replace tool-module import validation with `python -c "import xplainable_mcp.server"` (with a dummy `XPLAINABLE_API_KEY`).
- **Add a pytest step** (tech debt: CI never ran the tests): `pip install -e .[dev] pytest pytest-asyncio && python -m pytest -q` (add a `[project.optional-dependencies] dev` extra if absent). Note: requires xplainable-client>=1.13.0 on PyPI — CI red until released is acceptable and should be called out in the PR.

**Step 3: update-mcp-docs.yml:** trigger paths `xplainable_mcp/tools/**` no longer exist → change to `xplainable_mcp/**` and `scripts/generate_mcp_docs.py`.

**Step 4:** Run `XPLAINABLE_API_KEY=docs-build XPLAINABLE_ADVANCED_TOOLS=1 .venv/bin/python scripts/generate_mcp_docs.py --output /tmp/mcp-docs` and eyeball the output.

**Step 5: Commit** — `feat: docs generation + CI from live registry; run pytest in CI`

---

### Task 7: Final verification

1. `.venv/bin/python -m pytest -q` — 0 failures.
2. Surface counts: direct 33 / guided 36 / advanced ≥ 105 (script from Task 3 Step 5).
3. Boot check per tier: `XPLAINABLE_API_KEY=test MCP_TRANSPORT=stdio timeout 5 .venv/bin/python -m xplainable_mcp.server` (or the console script) starts without traceback for default, guided, advanced env combos.
4. `git grep -l "tool_discovery\|tool_manager\|sync_workflow"` returns only docs/plans historical references.
5. Update `README.md` if it documents the sync workflow or `XPLAINABLE_ADVANCED_TOOLS` only (add guided tier).
6. Commit any stragglers — `docs: update README for runtime tool generation`

---

## Out of scope

- Releasing xplainable-client 1.13.0 to PyPI (separate; CI will be red on the dependency-install step until then).
- Deleting `.github/workflows/*sync*` client-triggered sync action if present in the **client** repo (note for later).
- E2E telco-churn verification via Claude Desktop (post-merge verification gate from the design doc).
