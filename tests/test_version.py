"""The package version is declared twice; keep the two statements agreeing."""

from __future__ import annotations

import tomllib
from pathlib import Path

import anafpy


def test_dunder_version_matches_pyproject() -> None:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject.open("rb") as fh:
        declared = tomllib.load(fh)["project"]["version"]
    assert anafpy.__version__ == declared
