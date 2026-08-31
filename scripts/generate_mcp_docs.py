#!/usr/bin/env python3
"""Generate MDX MCP tool documentation from the live FastMCP server.

Imports the server and introspects the registered tools (including the
runtime tools generated from the xplainable-client @mcp_tool registry),
so the docs always match the actual tool surface. Produces a single
tools.mdx file suitable for Docusaurus.

Requires the package (and xplainable-client) to be installed.
"""

import argparse
import asyncio
import json
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODULE_DISPLAY_NAMES: Dict[str, str] = {
    "session": "Discovery & Session",
    "workflow": "Workflow",
    "models": "Models",
    "agentic": "Agentic Runs",
    "autotrain": "Auto-Train",
    "datasets": "Datasets",
    "preprocessing": "Preprocessing",
    "deployments": "Deployments",
    "inference": "Inference",
    "optimisers": "Optimisers",
    "monitors": "Monitors",
    "reports": "Reports",
    "runs": "Runs",
    "gpt": "AI Reports",
    "docs": "Documentation",
    "misc": "Utilities",
}

# Ordered list so the generated doc has a predictable section order.
MODULE_ORDER = [
    "session",
    "workflow",
    "models",
    "agentic",
    "autotrain",
    "datasets",
    "preprocessing",
    "deployments",
    "inference",
    "optimisers",
    "monitors",
    "reports",
    "runs",
    "gpt",
    "docs",
    "misc",
]

# Tool-name prefixes that map to a module section. Anything else
# (list_user_teams, set_active_team, select_team, ...) is a session tool.
_KNOWN_MODULES = set(MODULE_ORDER) - {"session"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParamInfo:
    name: str
    type: str = "str"
    required: bool = True
    default: Optional[str] = None
    description: str = ""


@dataclass
class ToolInfo:
    name: str
    description: str = ""
    params: List[ParamInfo] = field(default_factory=list)
    module: str = ""


# ---------------------------------------------------------------------------
# JSON-schema helpers
# ---------------------------------------------------------------------------

_SCHEMA_TYPES: Dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
    "null": "None",
}


def _schema_type(schema: dict) -> str:
    """Return a readable display type for a JSON-schema property."""
    if "anyOf" in schema:
        variants = [_schema_type(s) for s in schema["anyOf"]]
        non_null = [v for v in variants if v != "None"]
        if len(non_null) == 1:
            return non_null[0]
        return " | ".join(non_null) if non_null else "object"

    raw = schema.get("type")
    if isinstance(raw, list):
        non_null = [t for t in raw if t != "null"]
        raw = non_null[0] if non_null else "object"

    display = _SCHEMA_TYPES.get(raw, "object")
    if display == "list":
        items = schema.get("items")
        if isinstance(items, dict) and items:
            return f"List[{_schema_type(items)}]"
    if display == "dict":
        return "Dict"
    return display


def _default_to_str(value) -> str:
    """Convert a JSON-schema default value to a display string."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, list):
        return "[]" if not value else json.dumps(value)
    if isinstance(value, dict):
        return "{}" if not value else json.dumps(value)
    return str(value)


# ---------------------------------------------------------------------------
# Docstring parsing
# ---------------------------------------------------------------------------

def _parse_docstring(raw: Optional[str]) -> Tuple[str, Dict[str, str]]:
    """Return (first_paragraph_description, {param_name: description}).

    Handles Google-style ``Args:`` sections.
    """
    if not raw:
        return "", {}

    lines = textwrap.dedent(raw).strip().splitlines()

    # First paragraph = everything before the first blank line or ``Args:``
    desc_lines: List[str] = []
    idx = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "" or stripped.startswith("Args:"):
            break
        desc_lines.append(stripped)
    else:
        idx += 1

    description = " ".join(desc_lines)

    # Parse Args section
    param_descs: Dict[str, str] = {}
    in_args = False
    current_param: Optional[str] = None
    current_desc_parts: List[str] = []

    for line in lines[idx:]:
        stripped = line.strip()

        if stripped == "Args:":
            in_args = True
            continue

        # End of Args section on next top-level section header
        if in_args and stripped and not stripped.startswith("-") and ":" in stripped:
            maybe_header = stripped.split(":")[0].strip()
            if maybe_header in ("Returns", "Raises", "Category", "Workflow", "Yields"):
                if current_param is not None:
                    param_descs[current_param] = " ".join(current_desc_parts).strip()
                in_args = False
                continue

        if not in_args:
            continue

        # Match param lines like "param_name: description" or "param_name (type): desc"
        m = re.match(r"\s+(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)", line)
        if m:
            if current_param is not None:
                param_descs[current_param] = " ".join(current_desc_parts).strip()
            current_param = m.group(1)
            current_desc_parts = [m.group(2).strip()] if m.group(2).strip() else []
        elif current_param and stripped:
            current_desc_parts.append(stripped)

    if current_param is not None:
        param_descs[current_param] = " ".join(current_desc_parts).strip()

    return description, param_descs


# ---------------------------------------------------------------------------
# MDX escaping
# ---------------------------------------------------------------------------

def _escape_mdx(text: str) -> str:
    """Escape curly braces for MDX safety."""
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    return text


def _escape_js_string(text: str) -> str:
    """Escape a string for use inside a JS string literal (inside PropTable)."""
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\n", " ")
    return text


# ---------------------------------------------------------------------------
# MDX generation
# ---------------------------------------------------------------------------

def _render_prop_table(params: List[ParamInfo]) -> str:
    """Render a ``<PropTable ... />`` JSX block."""
    entries: List[str] = []
    for p in params:
        parts = [
            f'name: "{p.name}"',
            f'type: "{_escape_js_string(p.type)}"',
        ]
        if p.required:
            parts.append("required: true")
        if p.default is not None:
            parts.append(f'default: "{_escape_js_string(p.default)}"')
        if p.description:
            parts.append(f'description: "{_escape_js_string(p.description)}"')
        entries.append("  { " + ", ".join(parts) + " }")

    inner = ",\n".join(entries)
    return f"<PropTable params={{[\n{inner}\n]}} />"


def _render_tool(tool: ToolInfo) -> str:
    """Render a single tool section as MDX."""
    lines: List[str] = []
    lines.append(f"### `{tool.name}`")
    lines.append("")
    if tool.description:
        lines.append(_escape_mdx(tool.description))
    else:
        lines.append(f"Execute the `{tool.name}` tool.")
    lines.append("")

    if tool.params:
        lines.append(_render_prop_table(tool.params))
    else:
        lines.append("*No parameters.*")

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sample data generation for ToolCallSim
# ---------------------------------------------------------------------------

# Param name → sample value
_SAMPLE_VALUES: Dict[str, str] = {
    "model_id": '"mdl_8gJq2Xv"',
    "version_id": '"ver_3kLm9Nq"',
    "deployment_id": '"dep_5xRt2Wp"',
    "monitor_id": '"mon_7yKs4Bz"',
    "dataset_id": '"ds_2mNp6Fj"',
    "run_id": '"run_9qWe1Ht"',
    "team_id": '"team_abc123"',
    "preprocessor_id": '"pp_4vCx8Rd"',
    "key_id": '"key_1aNb3Gk"',
    "job_id": '"job_6pLs2Yf"',
    "report_id": '"rpt_8wDm5Qt"',
    "training_id": '"train_3kLm9"',
    "filename": '"data.csv"',
    "file_path": '"./dataset.csv"',
    "name": '"My Resource"',
    "model_name": '"Credit Risk Model"',
    "model_description": '"Predicting loan defaults"',
    "description": '"A description"',
    "target_column": '"target"',
    "label": '"churned"',
    "threshold": "0.5",
    "delimiter": '","',
    "batch_size": "1000",
    "test_size": "0.2",
    "n": "5",
    "rows": "10",
    "max_features": "15",
    "temperature": "0.7",
    "report_name": '"Model Report"',
    "content": '"What features drive churn?"',
}

# Type → default sample value
_TYPE_SAMPLES: Dict[str, str] = {
    "str": '"example"',
    "int": "1",
    "float": "0.5",
    "bool": "true",
    "list": "[]",
    "dict": "{}",
    "Dict": "{}",
    "object": "{}",
}

# Tool name pattern → sample response
_RESPONSE_PATTERNS: List[tuple] = [
    ("list_", '[\n  &#123; "id": "item_1", "name": "Example" &#125;\n]'),
    ("get_", '&#123;\n  "id": "res_abc",\n  "name": "Example",\n  "status": "active"\n&#125;'),
    ("create_", '&#123; "id": "new_abc123", "status": "created" &#125;'),
    ("deploy", '&#123; "deployment_id": "dep_5xRt2Wp", "status": "deployed" &#125;'),
    ("activate", '&#123; "status": "active" &#125;'),
    ("deactivate", '&#123; "status": "inactive" &#125;'),
    ("delete", '&#123; "status": "deleted" &#125;'),
    ("predict", '&#123;\n  "score": 0.87,\n  "prediction": 1,\n  "contributions": &#123; "feature_1": 0.12, "feature_2": -0.05 &#125;\n&#125;'),
    ("summarize", '&#123;\n  "rows": 5000,\n  "columns": 12,\n  "target": "churned",\n  "summary": "Dataset ready for training"\n&#125;'),
    ("generate_", '[\n  &#123; "suggestion": "Example suggestion", "confidence": 0.85 &#125;\n]'),
    ("train", '&#123;\n  "job_id": "job_2K9P",\n  "status": "running",\n  "model_id": "mdl_new"\n&#125;'),
    ("check_", '&#123; "status": "completed", "progress": 100 &#125;'),
    ("upload", '&#123; "dataset_id": "ds_new123", "rows": 5000 &#125;'),
    ("report", '&#123; "report_id": "rpt_abc", "status": "generating" &#125;'),
]


def _generate_sample_args(tool: ToolInfo) -> str:
    """Generate sample JSON arguments for a tool."""
    if not tool.params:
        return "{}"

    args = {}
    for p in tool.params:
        val = _SAMPLE_VALUES.get(p.name)
        if val is None:
            val = _TYPE_SAMPLES.get(p.type, '"example"')
        args[p.name] = val

    lines = []
    for k, v in args.items():
        lines.append(f'  "{k}": {v}')
    return "{\n" + ",\n".join(lines) + "\n}" if lines else "{}"


def _generate_sample_result(tool: ToolInfo) -> str:
    """Generate a plausible mock result for a tool."""
    name = tool.name.lower()
    for pattern, result in _RESPONSE_PATTERNS:
        if pattern in name:
            return result
    return '&#123; "ok": true &#125;'


def _render_tool_call_sim(groups: Dict[str, List[ToolInfo]]) -> str:
    """Render a <ToolCallSim> block with sample tools."""
    all_tools = []
    for module_key in MODULE_ORDER:
        tools = groups.get(module_key, [])
        for t in tools[:2]:  # max 2 per module
            all_tools.append(t)
    all_tools = all_tools[:12]  # cap at 12

    entries = []
    for t in all_tools:
        args = _generate_sample_args(t)
        result = _generate_sample_result(t)
        safe_args = args.replace("{", "&#123;").replace("}", "&#125;").replace("`", "\\`")
        safe_result = result.replace("`", "\\`")
        entries.append(
            f'  {{ name: "{t.name}", '
            f'args: `{safe_args}`, '
            f'result: `{safe_result}` }}'
        )

    inner = ",\n".join(entries)
    return f"<ToolCallSim tools={{[\n{inner}\n]}} />"


def _render_mdx(groups: Dict[str, List[ToolInfo]]) -> str:
    """Render the full tools.mdx content."""
    parts: List[str] = []

    # Frontmatter
    parts.append("---")
    parts.append("sidebar_position: 2")
    parts.append("title: Tool Reference")
    parts.append("description: Complete reference for all xplainable MCP server tools.")
    parts.append("---")
    parts.append("")
    parts.append("import PropTable from '@site/src/components/PropTable';")
    parts.append("import MethodBadge from '@site/src/components/MethodBadge';")
    parts.append("import ToolCallSim from '@site/src/components/ToolCallSim';")
    parts.append("")
    parts.append("# Tool Reference")
    parts.append("")
    parts.append(
        "Complete reference for every tool exposed by the xplainable MCP server. "
        "Tools are grouped by category."
    )
    parts.append("")

    # Try a tool call section
    parts.append("## Try a tool call")
    parts.append("")
    parts.append("Select a tool, review the sample arguments, and invoke it to see a simulated response.")
    parts.append("")
    parts.append(_render_tool_call_sim(groups))
    parts.append("")
    parts.append("---")
    parts.append("")

    for module_key in MODULE_ORDER:
        tools = groups.get(module_key)
        if not tools:
            continue
        display_name = MODULE_DISPLAY_NAMES.get(module_key, module_key.title())
        parts.append(f"## {display_name}")
        parts.append("")
        for tool in tools:
            parts.append(_render_tool(tool))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tool collection (FastMCP introspection)
# ---------------------------------------------------------------------------

def _tool_module(name: str) -> str:
    """Map a tool name to its docs module section by prefix."""
    prefix = name.split("_", 1)[0]
    return prefix if prefix in _KNOWN_MODULES else "session"


def _collect_tools() -> Dict[str, List[ToolInfo]]:
    """Introspect the FastMCP server and return grouped tools."""
    # The server refuses to boot without credentials; a dummy key is fine
    # for introspection (no API calls are made).
    os.environ.setdefault("XPLAINABLE_API_KEY", "docs-generation-key")

    from xplainable_mcp.server import mcp

    tool_map = asyncio.run(mcp.get_tools())

    groups: Dict[str, List[ToolInfo]] = {}
    for name in sorted(tool_map):
        tool = tool_map[name]
        description, param_descs = _parse_docstring(tool.description)

        schema = tool.parameters or {}
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        params: List[ParamInfo] = []
        for pname, pschema in properties.items():
            has_default = "default" in pschema
            params.append(ParamInfo(
                name=pname,
                type=_schema_type(pschema),
                required=pname in required,
                default=_default_to_str(pschema["default"]) if has_default else None,
                description=param_descs.get(pname, ""),
            ))

        groups.setdefault(_tool_module(name), []).append(ToolInfo(
            name=name,
            description=description,
            params=params,
            module=_tool_module(name),
        ))

    return groups


def generate(output_dir: str) -> None:
    """Generate documentation files into *output_dir*."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    groups = _collect_tools()

    total = sum(len(t) for t in groups.values())
    print(f"Discovered {total} tools across {len(groups)} modules")

    mdx = _render_mdx(groups)
    tools_path = out / "tools.mdx"
    tools_path.write_text(mdx)
    print(f"Wrote {tools_path}")

    # Write _category_.json only if it doesn't already exist
    category_path = out / "_category_.json"
    if not category_path.exists():
        category = {
            "label": "MCP Server",
            "position": 6,
            "link": {
                "type": "generated-index",
                "description": "Model Context Protocol server for xplainable."
            }
        }
        category_path.write_text(json.dumps(category, indent=2) + "\n")
        print(f"Wrote {category_path}")
    else:
        print(f"Skipped {category_path} (already exists)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate MDX documentation for xplainable MCP tools."
    )
    parser.add_argument(
        "--output",
        default="./generated-docs/mcp",
        help="Output directory for generated files (default: ./generated-docs/mcp)",
    )
    args = parser.parse_args()
    generate(args.output)
