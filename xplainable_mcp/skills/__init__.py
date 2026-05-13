"""
Bundled skills for the xplainable MCP server.

Skills are exposed as MCP resources that clients can discover and pin
to projects. Each skill provides domain-specific workflow guidance.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent


def get_available_skills() -> dict[str, dict]:
    """Return metadata for all bundled skills."""
    skills = {}
    for path in sorted(SKILLS_DIR.glob("*.md")):
        name = path.stem
        content = path.read_text()
        # Extract title from first markdown heading
        title = name.replace("-", " ").title()
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        # Extract description from the prerequisite line or first paragraph
        description = f"Workflow skill for {title.lower()}"
        skills[name] = {
            "name": name,
            "title": title,
            "path": path,
            "description": description,
        }
    return skills


def register_skill_resources(mcp):
    """Register all bundled skills as MCP resources."""
    skills = get_available_skills()

    for skill_name, skill_info in skills.items():
        path = skill_info["path"]
        title = skill_info["title"]

        # Create a closure to capture the path
        def make_reader(p):
            def read_skill() -> str:
                return p.read_text()
            read_skill.__name__ = f"skill_{p.stem}"
            read_skill.__doc__ = f"{title} — domain-specific workflow for xplainable ML"
            return read_skill

        mcp.resource(
            f"skill://xplainable/{skill_name}",
            name=skill_name,
            title=title,
            description=skill_info["description"],
            mime_type="text/markdown",
        )(make_reader(path))

    logger.info(f"Registered {len(skills)} skill resources")
