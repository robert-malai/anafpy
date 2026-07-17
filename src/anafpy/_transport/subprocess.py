"""Bounded async subprocess execution shared by transport integrations."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

__all__ = ["run_subprocess"]


async def run_subprocess(
    argv: Sequence[str],
    *,
    timeout: float,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[int, bytes, bytes]:
    """Run *argv* with captured output and a hard wall-clock deadline.

    A new process group/session is created so a timeout terminates descendants
    as well as the direct JVM/curl process. ``TimeoutError`` and ``OSError`` are
    intentionally left for the service-specific caller to translate.
    """
    process_kwargs: dict[str, Any] = {}
    if os.name == "posix":
        process_kwargs["start_new_session"] = True
    elif os.name == "nt":
        process_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
        )

    process = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd is not None else None,
        env=dict(env) if env is not None else None,
        **process_kwargs,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        if os.name == "posix":
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        await process.wait()
        raise
    return process.returncode or 0, stdout, stderr
