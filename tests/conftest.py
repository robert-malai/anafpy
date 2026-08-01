"""Shared test setup: load a repo-root ``.env`` (if present) for the live suites,
provide an in-memory keyring backend so store tests never touch the OS vault,
and teach respx to intercept httpx2 traffic.

The respx suite is credential-free; only the ``live``-marked tests read these
variables. Values already present in the environment win over the file.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import keyring
import keyring.backend
import pytest
from keyring.errors import PasswordDeleteError
from respx.mocks import HTTPCoreMocker

from anafpy.auth import FileTokenStore, KeyringTokenStore, TokenStore

_ENV_FILE = Path(__file__).parent.parent / ".env"


class HTTPCore2Mocker(HTTPCoreMocker):
    """respx mocker patching httpcore2 — the transport under ``httpx2``.

    respx only knows classic httpx/httpcore; anafpy's clients run on httpx2.
    Interception at the httpcore2 layer keeps the whole respx router API
    working unchanged (requests and responses cross that boundary as raw
    byte-level objects, so respx's classic-httpx currency never meets an
    httpx2 type). Vendored from ``lundberg/pytest-httpx2`` 1.0.0 — the respx
    author's own bridge — rather than depended on, because it is these six
    target strings plus a fixture anafpy does not use. respx registers the
    class by ``name`` at definition time.
    """

    name = "httpcore2"
    targets: ClassVar[list[str]] = [
        "httpcore2._sync.connection.HTTPConnection",
        "httpcore2._sync.connection_pool.ConnectionPool",
        "httpcore2._sync.http_proxy.HTTPProxy",
        "httpcore2._async.connection.AsyncHTTPConnection",
        "httpcore2._async.connection_pool.AsyncConnectionPool",
        "httpcore2._async.http_proxy.AsyncHTTPProxy",
    ]


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
def isolated_managed_duk_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the managed DUK dist at the test's tmp dir for EVERY test (autouse):
    ``default_duk_dir()`` is the implicit fallback of the DUK resolution, so
    without this a test on a developer machine with a real ``~/.anafpy/duk-dist``
    would silently resolve it (and behave differently than in CI)."""
    managed = tmp_path / "managed-duk-dist"
    monkeypatch.setattr("anafpy.declaratii.install.MANAGED_DUK_DIR", managed)
    return managed


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
    if (file_store := FileTokenStore(path)).load() is not None:
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
