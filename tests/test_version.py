"""The version is declared in several places; keep every statement agreeing.

Besides ``pyproject.toml`` and ``anafpy.__version__``, the MCP Bundle under
``mcpb/`` re-states the version twice: the manifest's ``version`` and the
bundle project's own version + its ``anafpy[mcp]==X.Y.Z`` dependency pin.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import anafpy

_ROOT = Path(__file__).parent.parent


def _pyproject_version() -> str:
    with (_ROOT / "pyproject.toml").open("rb") as fh:
        version: str = tomllib.load(fh)["project"]["version"]
    return version


def test_dunder_version_matches_pyproject() -> None:
    assert anafpy.__version__ == _pyproject_version()


def test_mcpb_bundle_agrees_with_pyproject() -> None:
    declared = _pyproject_version()
    manifest = json.loads((_ROOT / "mcpb" / "manifest.json").read_text())
    assert manifest["version"] == declared
    with (_ROOT / "mcpb" / "pyproject.toml").open("rb") as fh:
        bundle = tomllib.load(fh)["project"]
    assert bundle["version"] == declared
    assert f"anafpy[mcp]=={declared}" in bundle["dependencies"]
