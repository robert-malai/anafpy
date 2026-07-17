"""Shared bounded subprocess runner."""

from __future__ import annotations

import os
from typing import Any

import pytest

from anafpy._transport.subprocess import run_subprocess


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group semantics")
async def test_timeout_kills_posix_process_group_and_waits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waited = False
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 1234
        returncode = None

        async def communicate(self) -> tuple[bytes, bytes]:
            raise TimeoutError

        async def wait(self) -> int:
            nonlocal waited
            waited = True
            return -9

    async def create(*_argv: str, **_kwargs: Any) -> FakeProcess:
        return FakeProcess()

    monkeypatch.setattr(
        "anafpy._transport.subprocess.asyncio.create_subprocess_exec", create
    )
    monkeypatch.setattr(
        "anafpy._transport.subprocess.os.killpg",
        lambda pid, sig: killed.append((pid, sig)),
    )

    with pytest.raises(TimeoutError):
        await run_subprocess(["java", "-version"], timeout=0.01)

    assert killed and killed[0][0] == 1234
    assert waited is True
