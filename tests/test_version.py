"""The version is declared in several places; keep every statement agreeing.

The Claude Desktop extension manifest needs no check of its own:
scripts/build_mcpb.py generates it at build time with the version read from
``pyproject.toml``, so there is nothing to drift. The same file pins the exact
CPython the bundles carry; the build refuses a loose pin, and so does this
suite (earlier, where the native release runners cannot each bundle a
different interpreter).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import anafpy

_ROOT = Path(__file__).parent.parent


def _pyproject() -> dict[str, Any]:
    with (_ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def test_dunder_version_matches_pyproject() -> None:
    assert anafpy.__version__ == _pyproject()["project"]["version"]


def test_bundle_python_pin_is_exact() -> None:
    pin: str = _pyproject()["tool"]["anafpy"]["bundle-python"]
    parts = pin.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), (
        f"bundle-python must be an exact X.Y.Z pin, got {pin!r}"
    )
