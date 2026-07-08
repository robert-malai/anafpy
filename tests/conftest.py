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

from anafpy.auth import FileTokenStore, KeyringTokenStore, TokenStore

_ENV_FILE = Path(__file__).parent.parent / ".env"


class FakeKeyring(keyring.backend.KeyringBackend):
    """In-memory keyring backend; ``entries`` maps ``(service, username)`` to secret."""

    priority = 1
    previous: keyring.backend.KeyringBackend  # set by the fixture

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
    fake.previous = previous  # the real backend, for `live_token_store` only
    keyring.set_keyring(fake)
    try:
        yield fake
    finally:
        keyring.set_keyring(previous)


@pytest.fixture
def live_token_store(fake_keyring: FakeKeyring) -> Iterator[TokenStore]:
    """The developer's REAL token store, for the opt-in live suites only.

    Resolution mirrors the CLI: the file store when ``ANAFPY_TOKEN_STORE`` (or
    its default path) holds tokens, else the OS keyring — the default backend
    since 2026-07-05, which the autouse fake deliberately blocks, so the real
    backend is reinstated for the duration of the test. Live tests refresh and
    save through this store exactly like the CLI would; skips when no login has
    been bootstrapped.
    """
    path = Path(
        os.environ.get("ANAFPY_TOKEN_STORE", "~/.anafpy/tokens.json")
    ).expanduser()
    file_store = FileTokenStore(path)
    if file_store.load() is not None:
        yield file_store
        return
    keyring.set_keyring(fake_keyring.previous)
    try:
        store = KeyringTokenStore()
        if store.load() is None:
            pytest.skip("no token store — run `anafpy auth login` first")
        yield store
    finally:
        keyring.set_keyring(fake_keyring)


def _load_dotenv(path: Path) -> None:
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


if _ENV_FILE.is_file():
    _load_dotenv(_ENV_FILE)
