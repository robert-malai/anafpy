"""Tests for the signer's platform-agnostic parts (label resolution, guards).

The ctypes Keychain path itself is macOS-only and fires a real 2FA, so it is
exercised only by the opt-in live sign smoke test, not here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from anafpy.declaratii.signing import (
    KeychainRawSigner,
    _Frameworks,
    default_signed_path,
    load_pdfsign,
    resolve_signing_label,
)
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


def test_default_signed_path() -> None:
    assert default_signed_path(Path("/tmp/d300.pdf")) == Path("/tmp/d300-semnat.pdf")


def test_load_pdfsign_translates_missing_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(*_args: object, **_kwargs: object) -> object:
        raise ModuleNotFoundError("No module named 'pyhanko'", name="pyhanko")

    monkeypatch.setattr("anafpy.declaratii.signing.importlib.import_module", missing)
    with pytest.raises(AnafConfigError, match=r"anafpy\[declaratii\]"):
        load_pdfsign()


# --- Keychain interaction over a fake framework binding -----------------------------


class _FakeFrameworks:
    """Stand-in for ``signing._Frameworks`` recording CF retain/release traffic.

    Handle scheme (opaque ints standing in for CF pointers): query 100, result
    array 200, per-item dictionaries ``1000+i``, label CFStrings ``2000+i``,
    identity refs ``3000+i``, cfdata 500, private key 600, certificate 650,
    certificate data 660, CFError 777.
    """

    kSecClass = 1
    kSecClassIdentity = 2
    kSecMatchLimit = 3
    kSecMatchLimitAll = 4
    kSecReturnRef = 5
    kSecReturnAttributes = 6
    kSecAttrLabel = 7
    kSecValueRef = 8
    kSecAlgo = 9
    kCFBooleanTrue = 10

    def __init__(self, labels: list[str]) -> None:
        self.labels = labels
        self.released: list[int] = []
        self.retained: list[int] = []
        # The real object exposes the two libraries as .cf / .sec attributes.
        self.cf = self
        self.sec = self

    @staticmethod
    def _handle(ref: object) -> int:
        if isinstance(ref, int):
            return ref
        return int(getattr(ref, "value", 0) or 0)

    # -- CoreFoundation ----------------------------------------------------------------

    def CFRelease(self, ref: object) -> None:
        self.released.append(self._handle(ref))

    def CFRetain(self, ref: object) -> int:
        handle = self._handle(ref)
        self.retained.append(handle)
        return handle

    def CFArrayGetCount(self, array: object) -> int:
        return len(self.labels)

    def CFArrayGetValueAtIndex(self, array: object, index: int) -> int:
        return 1000 + index

    def CFDictionaryGetValue(self, item: object, key: object) -> int:
        offset = self._handle(item) - 1000
        return (2000 if key == self.kSecAttrLabel else 3000) + offset

    # -- Security ----------------------------------------------------------------------

    def SecItemCopyMatching(self, query: object, out: Any) -> int:
        out._obj.value = 200
        return 0

    def SecIdentityCopyCertificate(self, identity: object, out: Any) -> int:
        out._obj.value = 650
        return 0

    def SecCertificateCopyData(self, cert: object) -> int:
        return 660

    def SecIdentityCopyPrivateKey(self, identity: object, out: Any) -> int:
        out._obj.value = 600
        return 0

    def SecKeyCreateSignature(
        self, key: object, algo: object, data: object, error: Any
    ) -> None:
        error._obj.value = 777
        return None  # signature creation failed; the CFError carries the cause

    # -- _Frameworks helpers -----------------------------------------------------------

    def make_query(self, pairs: list[tuple[int, int]]) -> int:
        return 100

    def cfstr_to_str(self, cfstr: object) -> str | None:
        return self.labels[self._handle(cfstr) - 2000]

    def bytes_to_cfdata(self, data: bytes) -> int:
        return 500

    def cfdata_to_bytes(self, cfdata: object) -> bytes:
        return b"DER"

    def error_description(self, cferror: int) -> str:
        return "approval denied"


def _install(monkeypatch: pytest.MonkeyPatch, labels: list[str]) -> _FakeFrameworks:
    fake = _FakeFrameworks(labels)
    monkeypatch.setattr("anafpy.declaratii.signing._frameworks", lambda: fake)
    return fake


def test_unique_label_is_selected_among_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _install(monkeypatch, ["OTHER CERT", "MIHAI-ROBERT MALAI"])
    signer = KeychainRawSigner("MIHAI-ROBERT MALAI")
    assert signer.certificate() == b"DER"
    assert fake.retained == [3001]  # the second item's identity ref


def test_ambiguous_keychain_label_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two identities with the same name (a renewed certificate next to the old
    # one) must refuse, mirroring spv.certs.identity_by_thumbprint — never
    # silently sign with whichever the OS lists first.
    fake = _install(monkeypatch, ["MIHAI-ROBERT MALAI", "MIHAI-ROBERT MALAI"])
    with pytest.raises(AnafConfigError, match="2 identities named"):
        KeychainRawSigner("MIHAI-ROBERT MALAI")
    assert fake.retained == []  # nothing was retained on the refusal path


def test_failed_signature_releases_the_cferror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _install(monkeypatch, ["MIHAI-ROBERT MALAI"])
    signer = KeychainRawSigner("MIHAI-ROBERT MALAI")
    with pytest.raises(AnafConfigError, match="signing failed: approval denied"):
        signer._sign_blocking(b"payload")
    # The CFError out-parameter is a Create-Rule reference this side owns; the
    # cfdata and private key are released alongside it.
    assert 777 in fake.released
    assert 500 in fake.released
    assert 600 in fake.released
