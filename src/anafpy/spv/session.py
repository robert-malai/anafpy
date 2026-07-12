"""SPV session state and its persistence.

An SPV "session" is the F5 BIG-IP APM **cookie set** (``MRHSession`` & friends)
minted by the one certificate-authenticated handshake at ``/my.policy`` — see
``docs/anaf-reference/spv/api.md`` §1.1. After that handshake every request rides
the cookies, so the cookie set is a **bearer credential** to the taxpayer's SPV
and gets the same custody treatment as the OAuth tokens: a
:class:`SessionStore` protocol with an atomic, ``0o600`` JSON file backend.

The APM rotates ``MRHSession`` mid-session (revalidation hops), so the client
re-saves the session whenever the cookie values change.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError

from ..exceptions import AnafConfigError

__all__ = [
    "DEFAULT_SESSION_PATH",
    "FileSessionStore",
    "MemorySessionStore",
    "SessionStore",
    "SpvSession",
]

#: Default location of the persisted session, next to the OAuth token store's
#: default (``~/.anafpy/tokens.json``).
DEFAULT_SESSION_PATH = "~/.anafpy/spv-session.json"


class SpvSession(BaseModel):
    """The APM cookie set plus when it was established.

    ``cookies`` maps cookie name to value for the ``webserviced.anaf.ro`` domain
    (the only host SPV lives on — domain/path carry no information worth
    persisting). ``established_at`` is when the certificate handshake ran; the
    APM idle timeout is not published, so staleness is discovered by the first
    request bouncing to ``/my.policy``, not predicted from this timestamp.
    """

    cookies: dict[str, str]
    established_at: datetime

    @property
    def is_authenticated_shape(self) -> bool:
        """Whether the cookie set contains the APM session cookie at all."""
        return "MRHSession" in self.cookies


@runtime_checkable
class SessionStore(Protocol):
    """Where SPV sessions are loaded from and saved to."""

    def load(self) -> SpvSession | None: ...

    def save(self, session: SpvSession) -> None: ...

    def clear(self) -> None: ...


class MemorySessionStore:
    """In-process session store (tests, ephemeral runtimes)."""

    def __init__(self, session: SpvSession | None = None) -> None:
        self._session = session

    def load(self) -> SpvSession | None:
        return self._session

    def save(self, session: SpvSession) -> None:
        self._session = session

    def clear(self) -> None:
        self._session = None


class FileSessionStore:
    """JSON-file session store, written atomically with ``0o600`` permissions."""

    def __init__(self, path: str | os.PathLike[str] = DEFAULT_SESSION_PATH) -> None:
        self.path = Path(path).expanduser()

    def load(self) -> SpvSession | None:
        """The stored session, or ``None`` when no store file exists.

        Raises:
            AnafConfigError: the file exists but cannot be read or parsed — stay
                in the AnafError hierarchy instead of leaking a pydantic/OS error.
        """
        if not self.path.exists():
            return None
        try:
            return SpvSession.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise AnafConfigError(
                f"unreadable SPV session store {self.path}: {exc} — "
                "delete it and log in to SPV again"
            ) from exc

    def save(self, session: SpvSession) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = session.model_dump_json(indent=2)
        # Write to a temp file in the same dir, fix perms, then atomically replace.
        fd, tmp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=".spv-", suffix=".json"
        )
        tmp = Path(tmp_name)
        try:
            os.write(fd, data.encode("utf-8"))
        finally:
            os.close(fd)
        tmp.chmod(0o600)
        tmp.replace(self.path)

    def clear(self) -> None:
        """Delete the store file; a no-op when none exists.

        Raises:
            AnafConfigError: the file exists but cannot be removed.
        """
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            raise AnafConfigError(
                f"cannot remove SPV session store {self.path}: {exc}"
            ) from exc
