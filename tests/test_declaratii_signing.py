"""Tests for the signer's platform-agnostic parts (label resolution, guards).

The ctypes Keychain path itself is macOS-only and fires a real 2FA, so it is
exercised only by the opt-in live sign smoke test, not here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anafpy.declaratii.signing import _Frameworks, resolve_signing_label
from anafpy.exceptions import AnafConfigError
from anafpy.spv.certs import SelectedIdentity, save_selected_identity


def test_explicit_label_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANAFPY_SIGN_IDENTITY", "env-label")
    assert resolve_signing_label("explicit-label") == "explicit-label"


def test_env_label_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANAFPY_SIGN_IDENTITY", "env-label")
    assert resolve_signing_label(identity_path=tmp_path / "nope.json") == "env-label"


def test_falls_back_to_selected_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ANAFPY_SIGN_IDENTITY", raising=False)
    path = tmp_path / "identity.json"
    save_selected_identity(
        SelectedIdentity(
            name="MIHAI-ROBERT MALAI",
            sha1_thumbprint="A" * 40,
            platform="darwin",
        ),
        path,
    )
    assert resolve_signing_label(identity_path=path) == "MIHAI-ROBERT MALAI"


def test_nothing_resolves_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ANAFPY_SIGN_IDENTITY", raising=False)
    with pytest.raises(AnafConfigError, match="no signing certificate selected"):
        resolve_signing_label(identity_path=tmp_path / "missing.json")


def test_frameworks_rejects_non_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("anafpy.declaratii.signing.sys.platform", "linux")
    with pytest.raises(AnafConfigError, match="macOS-only"):
        _Frameworks()
