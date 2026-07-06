"""The workflow skills (``skills/*/SKILL.md``) as user-invoked MCP prompts."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..config import ServerConfig
from ..skills import load_skills

__all__ = ["register"]


def register(mcp: FastMCP, cfg: ServerConfig) -> None:
    """Expose the workflow skills as user-invoked MCP prompts.

    Each ``skills/`` playbook is served as a prompt of the same name, carrying the
    same Markdown — prompts are the closest MCP primitive to a skill, invoked by
    the *user* (a slash command in Claude Code, the "+" attachment menu in Claude
    Desktop).
    """
    if (skills := _skills_dir(cfg)) is None:
        return
    for skill in load_skills(skills):
        mcp.prompt(name=skill.name, description=skill.description)(
            _make_prompt(skill.body)
        )


def _skills_dir(cfg: ServerConfig) -> Path | None:
    default = Path(__file__).resolve().parents[4] / "skills"
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
