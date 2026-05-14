#!/usr/bin/env python3
"""Generate MDX MCP tool documentation from xplainable-mcp-server source.

Uses AST parsing to extract tool definitions from Python source files
without requiring any runtime imports. Produces a single tools.mdx file
suitable for Docusaurus.
"""

import argparse
import ast
import json
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent.parent / "xplainable_mcp" / "tools"
SERVER_FILE = Path(__file__).resolve().parent.parent / "xplainable_mcp" / "server.py"

MODULE_DISPLAY_NAMES: Dict[str, str] = {
    "session": "Discovery & Session",
    "models": "Models",
    "inference": "Inference",
    "deployments": "Deployments",
    "autotrain": "Auto-Train",
    "preprocessing": "Preprocessing",
    "datasets": "Datasets",
    "monitors": "Monitors",
    "reports": "Reports",
    "runs": "Runs",
    "misc": "Utilities",
    "gpt": "AI Reports",
}

# Ordered list so the generated doc has a predictable section order.
MODULE_ORDER = [
    "session",
    "models",
    "autotrain",
    "datasets",
    "preprocessing",
    "deployments",
    "inference",
    "monitors",
    "reports",
    "runs",
    "gpt",
    "misc",
]


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
# Type normalisation helpers
# ---------------------------------------------------------------------------

_SIMPLE_TYPES = {"str", "int", "float", "bool", "dict", "list", "None"}


def _normalize_type(raw: str) -> Tuple[str, bool]:
    """Return (display_type, is_optional).

    Handles ``Optional[X]``, ``List[X]``, ``Dict[X, Y]``, ``Any``, etc.
    """
    raw = raw.strip()

    # Optional[X] -> X, mark optional
    m = re.match(r"Optional\[(.+)\]$", raw)
    if m:
        inner, _ = _normalize_type(m.group(1))
        return inner, True

    # Union[X, None] style
    m = re.match(r"Union\[(.+),\s*None\]$", raw)
    if m:
        inner, _ = _normalize_type(m.group(1))
        return inner, True

    # List[X]
    m = re.match(r"[Ll]ist\[(.+)\]$", raw)
    if m:
        inner, _ = _normalize_type(m.group(1))
        return f"List[{inner}]", False

    # Dict[X, Y]
    m = re.match(r"[Dd]ict\[(.+)\]$", raw)
    if m:
        return "Dict", False

    # Simple well-known types
    low = raw.lower()
    for t in _SIMPLE_TYPES:
        if low == t.lower():
            return t, False

    if raw == "Any":
        return "object", False

    # Fallback
    return raw if raw else "object", False


def _annotation_to_str(node: ast.expr) -> str:
    """Convert an AST annotation node to a readable string."""
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_annotation_to_str(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        base = _annotation_to_str(node.value)
        sl = node.slice
        if isinstance(sl, ast.Tuple):
            inner = ", ".join(_annotation_to_str(e) for e in sl.elts)
        else:
            inner = _annotation_to_str(sl)
        return f"{base}[{inner}]"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _annotation_to_str(node.left)
        right = _annotation_to_str(node.right)
        if right == "None":
            return f"Optional[{left}]"
        return f"Union[{left}, {right}]"
    return "object"


def _default_to_str(node: ast.expr) -> str:
    """Convert a default-value AST node to a display string."""
    if isinstance(node, ast.Constant):
        if node.value is None:
            return "None"
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.List):
        return "[]"
    if isinstance(node, ast.Dict):
        return "{}"
    return "..."


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
            # Check if it's a section header like Returns:, Raises:, Category:, Workflow:
            maybe_header = stripped.split(":")[0].strip()
            if maybe_header in ("Returns", "Raises", "Category", "Workflow", "Yields"):
                # Save current param
                if current_param is not None:
                    param_descs[current_param] = " ".join(current_desc_parts).strip()
                in_args = False
                continue

        if not in_args:
            continue

        # Match param lines like "param_name: description" or "param_name (type): desc"
        m = re.match(r"\s+(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)", line)
        if m:
            # Save previous param
            if current_param is not None:
                param_descs[current_param] = " ".join(current_desc_parts).strip()
            current_param = m.group(1)
            current_desc_parts = [m.group(2).strip()] if m.group(2).strip() else []
        elif current_param and stripped:
            # Continuation line
            current_desc_parts.append(stripped)

    # Save last param
    if current_param is not None:
        param_descs[current_param] = " ".join(current_desc_parts).strip()

    return description, param_descs


# ---------------------------------------------------------------------------
# AST extraction
# ---------------------------------------------------------------------------

def _has_mcp_tool_decorator(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> bool:
    """Check whether the function has an ``@mcp.tool(...)`` decorator."""
    for dec in func_node.decorator_list:
        if isinstance(dec, ast.Call):
            func = dec.func
            if (isinstance(func, ast.Attribute)
                    and func.attr == "tool"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "mcp"):
                return True
    return False


def _extract_tools_from_source(source: str, module_name: str) -> List[ToolInfo]:
    """Parse a Python source string and return all ``@mcp.tool()`` functions."""
    tree = ast.parse(source)
    tools: List[ToolInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _has_mcp_tool_decorator(node):
            continue

        # Docstring
        raw_doc = ast.get_docstring(node)
        description, param_descs = _parse_docstring(raw_doc)

        # Parameters
        args = node.args
        params: List[ParamInfo] = []

        # Build list of defaults aligned to args (right-aligned)
        num_args = len(args.args)
        defaults = args.defaults
        num_defaults = len(defaults)
        padded_defaults: List[Optional[ast.expr]] = [None] * (num_args - num_defaults) + list(defaults)

        for i, arg in enumerate(args.args):
            name = arg.arg
            # Skip 'self', 'cls', 'ctx' (FastMCP Context)
            if name in ("self", "cls", "ctx"):
                continue

            # Type annotation
            if arg.annotation:
                raw_type = _annotation_to_str(arg.annotation)
            else:
                raw_type = "str"

            display_type, is_optional_type = _normalize_type(raw_type)

            # Default value
            default_node = padded_defaults[i]
            has_default = default_node is not None
            default_str = _default_to_str(default_node) if has_default else None

            required = not has_default and not is_optional_type

            # Description from docstring
            pdesc = param_descs.get(name, "")

            params.append(ParamInfo(
                name=name,
                type=display_type,
                required=required,
                default=default_str,
                description=pdesc,
            ))

        tools.append(ToolInfo(
            name=node.name,
            description=description,
            params=params,
            module=module_name,
        ))

    return tools


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
    parts.append("")
    parts.append("# Tool Reference")
    parts.append("")
    parts.append(
        "Complete reference for every tool exposed by the xplainable MCP server. "
        "Tools are grouped by category."
    )
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
# Main logic
# ---------------------------------------------------------------------------

def _collect_tools() -> Dict[str, List[ToolInfo]]:
    """Scan all tool source files and server.py, returning grouped tools."""
    groups: Dict[str, List[ToolInfo]] = {}

    # 1. Session / discovery tools from server.py
    if SERVER_FILE.exists():
        source = SERVER_FILE.read_text()
        session_tools = _extract_tools_from_source(source, "session")
        if session_tools:
            groups["session"] = session_tools

    # 2. Tool module files
    if TOOLS_DIR.is_dir():
        for py_file in sorted(TOOLS_DIR.iterdir()):
            if py_file.name.startswith("_") or py_file.suffix != ".py":
                continue
            module_name = py_file.stem
            source = py_file.read_text()
            tools = _extract_tools_from_source(source, module_name)
            if tools:
                groups.setdefault(module_name, []).extend(tools)

    return groups


def generate(output_dir: str) -> None:
    """Generate documentation files into *output_dir*."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    groups = _collect_tools()

    # Count tools
    total = sum(len(t) for t in groups.values())
    print(f"Discovered {total} tools across {len(groups)} modules")

    # Render and write tools.mdx
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
