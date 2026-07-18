"""The workflow skills (``anafpy-workflows`` plugin) as user-invoked MCP prompts.

The ``anafpy-workflows`` plugin's ``skills/`` directory
(``plugins/anafpy-workflows/skills/<name>/SKILL.md``) is the single home of the
workflow playbooks — Markdown with YAML frontmatter. It is the same tree the
plugin ships to Cowork as Agent Skills; this module re-serves it so every
prompt-capable MCP consumer (``claude mcp add``, Claude Desktop, ...) also gets
them as user-invoked MCP **prompts** of the same name, carrying the same Markdown —
prompts are the closest MCP primitive to a skill, invoked by the *user* (a slash
command in Claude Code, the "+" attachment menu in Claude Desktop). The SKILL.md
files are the single source of truth: this module reads them, it never
duplicates them.

Parsing is ``python-frontmatter``'s job (PyYAML underneath); this module only
checks that the fields the prompt listing needs — ``name`` and ``description`` —
are present, and fails loudly when they are not.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import frontmatter
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..exceptions import AnafConfigError
from .config import ServerConfig

__all__ = ["SkillDocument", "load_skills", "register"]


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
        skills_dir: the skills root (the ``anafpy-workflows`` plugin's
            ``skills/`` or ``ANAFPY_SKILLS_DIR``).

    Returns:
        The parsed skills, sorted by path for a stable prompt order.

    Raises:
        AnafConfigError: if a skill file lacks the ``name``/``description``
            frontmatter fields the prompt listing needs.
    """
    return [_parse_skill(path) for path in sorted(skills_dir.glob("*/SKILL.md"))]


def register(mcp: FastMCP, cfg: ServerConfig) -> None:
    """Expose the workflow skills as user-invoked MCP prompts."""
    if (skills := _skills_dir(cfg)) is None:
        return
    for skill in load_skills(skills):
        mcp.prompt(name=skill.name, description=skill.description)(
            _make_prompt(skill.body)
        )


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


def _skills_dir(cfg: ServerConfig) -> Path | None:
    default = (
        Path(__file__).resolve().parents[3]
        / "plugins"
        / "anafpy-workflows"
        / "skills"
    )
    skills = cfg.skills_dir or default
    return skills if skills.is_dir() else None


def _make_prompt(body: str) -> Callable[..., str]:
    def prompt(
        source: Annotated[
            str,
            Field(
                description="Optional: the source data or a pointer to it (pasted "
                "text, a file path, a message reference) to seed the workflow with."
            ),
        ] = "",
    ) -> str:
        if source:
            return f"{body}\n---\n\nSource data from the user:\n{source}\n"
        return body

    return prompt
