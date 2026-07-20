"""Types named in public client signatures must be importable from ``anafpy``."""

from __future__ import annotations

import anafpy
from anafpy._transport.base import Environment


def test_environment_is_reexported() -> None:
    assert anafpy.Environment is Environment
    assert "Environment" in anafpy.__all__
