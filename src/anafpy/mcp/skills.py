"""Workflow skills, loaded for exposure as MCP prompts.

The repo's ``skills/`` directory holds workflow skills — Markdown playbooks with
YAML frontmatter (``skills/<name>/SKILL.md``). Every prompt-capable MCP consumer
(``claude mcp add``, Claude Desktop, ...) gets them as user-invoked MCP **prompts**
(see :func:`anafpy.mcp.server.create_server`). The SKILL.md files are
the single source of truth: this module reads them, it never duplicates them.

Parsing is ``python-frontmatter``'s job (PyYAML underneath); this module only
checks that the fields the prompt listing needs — ``name`` and ``description`` —
are present, and fails loudly when they are not.
"""

from __future__ import annotations

from pathlib import Path

import frontmatter
from pydantic import BaseModel

from ..exceptions import AnafConfigError

__all__ = ["SkillDocument", "load_skills"]


class SkillDocument(BaseModel):
    """One parsed skill: its identity plus the Markdown playbook body.

    Attributes:
        name: the skill's frontmatter ``name`` — becomes the MCP prompt name.
        description: the frontmatter ``description``, folded onto one line —
            becomes the MCP prompt description.
        body: the Markdown after the frontmatter, the playbook itself.
    """

    name: str
    description: str
    body: str


def load_skills(skills_dir: Path) -> list[SkillDocument]:
    """Parse every ``<skills_dir>/*/SKILL.md`` into a :class:`SkillDocument`.

    Args:
        skills_dir: the skills root (the repo's ``skills/`` or
            ``ANAFPY_SKILLS_DIR``).

    Returns:
        The parsed skills, sorted by path for a stable prompt order.

    Raises:
        AnafConfigError: if a skill file lacks the ``name``/``description``
            frontmatter fields the prompt listing needs.
    """
    return [_parse_skill(path) for path in sorted(skills_dir.glob("*/SKILL.md"))]


def _parse_skill(path: Path) -> SkillDocument:
    post = frontmatter.load(str(path))
    return SkillDocument(
        name=_required_field(post, "name", path),
        description=_required_field(post, "description", path),
        body=post.content.strip() + "\n",
    )


def _required_field(post: frontmatter.Post, key: str, path: Path) -> str:
    value = post.metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AnafConfigError(f"skill file {path} frontmatter is missing {key!r}")
    return value.strip()
