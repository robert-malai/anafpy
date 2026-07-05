"""Shared test setup: load a repo-root ``.env`` (if present) for the live suites,
and provide an in-memory keyring backend so store tests never touch the OS vault.

The respx suite is credential-free; only the ``live``-marked tests read these
variables. Values already present in the environment win over the file.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import keyring
import keyring.backend
import pytest
from keyring.errors import PasswordDeleteError

_ENV_FILE = Path(__file__).parent.parent / ".env"


class FakeKeyring(keyring.backend.KeyringBackend):
    """In-memory keyring backend; ``entries`` maps ``(service, username)`` to secret."""

    priority = 1

    def __init__(self) -> None:
        super().__init__()  # type: ignore[no-untyped-call]  # keyring is partially typed
        self.entries: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.entries.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.entries[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if (service, username) not in self.entries:
            raise PasswordDeleteError(username)
        del self.entries[(service, username)]


@pytest.fixture(autouse=True)
def fake_keyring() -> Iterator[FakeKeyring]:
    """In-memory keyring for EVERY test (autouse): keyring is the default token
    store backend, so without this a test that forgets to pick a backend would
    read/write the developer's real OS credential store."""
    previous = keyring.get_keyring()
    fake = FakeKeyring()
    keyring.set_keyring(fake)
    try:
        yield fake
    finally:
        keyring.set_keyring(previous)


def _load_dotenv(path: Path) -> None:
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


if _ENV_FILE.is_file():
    _load_dotenv(_ENV_FILE)
