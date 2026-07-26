"""Tests for the signer: label resolution, platform dispatch, both key stores.

Neither platform path can be driven for real here — the macOS one fires a 2FA
and the Windows one needs a certificate store — so each is exercised over a fake
of its own platform seam: ``_Frameworks`` for the Keychain ctypes calls,
PowerShell's two runners for the Windows store. Both fakes are platform-neutral,
so every CI leg covers both paths; the real ones are the opt-in live smokes.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from anafpy.declaratii.signing import (
    _WINDOWS_CERTIFICATE_SCRIPT,
    _WINDOWS_SIGN_SCRIPT,
    KeychainRawSigner,
    WindowsStoreRawSigner,
    _Frameworks,
    _normalize_thumbprint,
    _parse_certificate_result,
    _parse_signature_result,
    default_signed_path,
    load_pdfsign,
    platform_raw_signer,
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
    # macOS: the selector is the Keychain identity name. The Windows counterpart
    # is test_windows_selection_resolves_to_the_thumbprint.
    monkeypatch.setattr("anafpy.declaratii.signing.sys.platform", "darwin")
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


# --- Windows certificate store ------------------------------------------------------

_THUMB = "a1" * 20  # 40 hex digits, as a Windows UI copies it out
_CANONICAL = _THUMB.upper()


def _certificate_json(der: bytes = b"leaf-der", not_after: str = "2099-01-01") -> str:
    return json.dumps(
        {"certificate": base64.b64encode(der).decode(), "not_after": not_after}
    )


class _StubSubprocess:
    """Stand-in for the :mod:`subprocess` module the signer reads the cert with.

    Substituted wholesale rather than patching the real ``subprocess.run``, so
    nothing outside the signer is affected. ``TimeoutExpired`` must stay the real
    class — the signer catches it.
    """

    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(
        self,
        *,
        stdout: str = "",
        returncode: int = 0,
        stderr: str = "",
        raises: BaseException | None = None,
    ) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.raises = raises
        self.environments: list[dict[str, str]] = []
        self.argvs: list[Sequence[str]] = []

    def run(self, argv: Sequence[str], **kwargs: Any) -> Any:
        if self.raises is not None:
            raise self.raises
        self.argvs.append(argv)
        self.environments.append(dict(kwargs["env"]))
        return subprocess.CompletedProcess(
            argv, self.returncode, self.stdout, self.stderr
        )


@pytest.fixture
def on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend this interpreter runs on Windows (the platform guards read it)."""
    monkeypatch.setattr("anafpy.declaratii.signing.sys.platform", "win32")


def _stub_certificate_read(
    monkeypatch: pytest.MonkeyPatch, **kwargs: Any
) -> _StubSubprocess:
    stub = _StubSubprocess(**kwargs)
    monkeypatch.setattr("anafpy.declaratii.signing.subprocess", stub)
    return stub


def _stub_signature_run(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[dict[str, str]], tuple[int, bytes, bytes]],
) -> dict[str, Any]:
    """Fake the async signing run; *handler* plays PowerShell's part."""
    captured: dict[str, Any] = {}

    async def fake_run(
        argv: Sequence[str], *, timeout: float, env: dict[str, str], **_: Any
    ) -> tuple[int, bytes, bytes]:
        captured["argv"] = list(argv)
        captured["env"] = env
        captured["timeout"] = timeout
        payload = Path(env["ANAFPY_SIGN_PAYLOAD_FILE"])
        captured["payload"] = payload.read_bytes()
        return handler(env)

    monkeypatch.setattr("anafpy.declaratii.signing.run_subprocess", fake_run)
    return captured


def _writes(signature: bytes, *, reported: int | None = None) -> Any:
    """A handler that writes *signature* and reports its length (or *reported*)."""

    def handler(env: dict[str, str]) -> tuple[int, bytes, bytes]:
        Path(env["ANAFPY_SIGN_OUTPUT_FILE"]).write_bytes(signature)
        length = len(signature) if reported is None else reported
        return 0, json.dumps({"signature_length": length}).encode(), b""

    return handler


# -- the platform seam ---------------------------------------------------------------


def test_windows_signer_refuses_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("anafpy.declaratii.signing.sys.platform", "linux")
    with pytest.raises(AnafConfigError, match="needs Windows"):
        WindowsStoreRawSigner(_THUMB)


def test_platform_raw_signer_picks_the_windows_store(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    _stub_certificate_read(monkeypatch, stdout=_certificate_json())
    signer = platform_raw_signer(_THUMB)
    assert isinstance(signer, WindowsStoreRawSigner)
    assert signer.thumbprint == _CANONICAL


def test_platform_raw_signer_picks_the_keychain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("anafpy.declaratii.signing.sys.platform", "darwin")
    _install(monkeypatch, ["MIHAI-ROBERT MALAI"])
    signer = platform_raw_signer("MIHAI-ROBERT MALAI")
    assert isinstance(signer, KeychainRawSigner)


def test_platform_raw_signer_refuses_elsewhere(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("anafpy.declaratii.signing.sys.platform", "linux")
    with pytest.raises(AnafConfigError, match="platform key store"):
        platform_raw_signer("whatever")


def test_windows_selection_resolves_to_the_thumbprint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, on_windows: None
) -> None:
    monkeypatch.delenv("ANAFPY_SIGN_IDENTITY", raising=False)
    path = tmp_path / "identity.json"
    save_selected_identity(
        SelectedIdentity(
            name="MIHAI-ROBERT MALAI", sha1_thumbprint=_CANONICAL, platform="win32"
        ),
        path,
    )
    # Windows selects by thumbprint, never by the (collidable) name.
    assert resolve_signing_label(identity_path=path) == _CANONICAL


def test_foreign_platform_selection_is_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, on_windows: None
) -> None:
    # A synced home directory can carry a macOS selection onto a Windows box;
    # a Keychain name is not a thumbprint, so refuse rather than mistranslate.
    monkeypatch.delenv("ANAFPY_SIGN_IDENTITY", raising=False)
    path = tmp_path / "identity.json"
    save_selected_identity(
        SelectedIdentity(
            name="MIHAI-ROBERT MALAI", sha1_thumbprint=_CANONICAL, platform="darwin"
        ),
        path,
    )
    with pytest.raises(AnafConfigError, match="SHA-1 thumbprint"):
        resolve_signing_label(identity_path=path)


# -- the selector --------------------------------------------------------------------


@pytest.mark.parametrize(
    "selector",
    [_THUMB, _CANONICAL, ":".join(["a1"] * 20), " ".join(["A1"] * 20)],
)
def test_thumbprint_separators_are_accepted(selector: str) -> None:
    assert _normalize_thumbprint(selector) == _CANONICAL


@pytest.mark.parametrize("selector", ["MIHAI-ROBERT MALAI", "", "a1" * 19, "z" * 40])
def test_non_thumbprint_selector_is_refused(selector: str) -> None:
    with pytest.raises(AnafConfigError, match="not a certificate thumbprint"):
        _normalize_thumbprint(selector)


# -- the scripts ---------------------------------------------------------------------


def test_scripts_read_only_environment_the_signer_provides() -> None:
    # The signer passes every input through the environment (no argv quoting, no
    # injection surface); a new $env: reference must come with the code that
    # sets it, so pin the set.
    referenced = set(
        re.findall(r"\$env:(\w+)", _WINDOWS_CERTIFICATE_SCRIPT + _WINDOWS_SIGN_SCRIPT)
    )
    assert referenced == {
        "ANAFPY_SIGN_THUMBPRINT",
        "ANAFPY_SIGN_PAYLOAD_FILE",
        "ANAFPY_SIGN_OUTPUT_FILE",
    }


def test_certificate_script_needs_only_the_thumbprint() -> None:
    # Reading the leaf must not depend on a signing temp file — it runs in the
    # constructor, before any payload exists.
    assert set(re.findall(r"\$env:(\w+)", _WINDOWS_CERTIFICATE_SCRIPT)) == {
        "ANAFPY_SIGN_THUMBPRINT"
    }


# -- reading the certificate ---------------------------------------------------------


def test_certificate_is_read_at_construction(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    stub = _stub_certificate_read(monkeypatch, stdout=_certificate_json(b"the-leaf"))
    signer = WindowsStoreRawSigner(_THUMB)
    assert signer.certificate() == b"the-leaf"
    assert stub.environments[0]["ANAFPY_SIGN_THUMBPRINT"] == _CANONICAL
    assert "-NonInteractive" in stub.argvs[0]
    # No payload/output path is set for the certificate read.
    assert "ANAFPY_SIGN_PAYLOAD_FILE" not in stub.environments[0]


def test_certificate_read_failure_is_reported(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    _stub_certificate_read(monkeypatch, returncode=1, stderr="Get-ChildItem: denied")
    with pytest.raises(AnafConfigError, match=r"cannot read certificate .*denied"):
        WindowsStoreRawSigner(_THUMB)


def test_missing_powershell_is_reported(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    _stub_certificate_read(monkeypatch, raises=OSError("not found"))
    with pytest.raises(AnafConfigError, match=r"cannot run powershell\.exe"):
        WindowsStoreRawSigner(_THUMB)


def test_absent_certificate_points_at_the_selection_commands() -> None:
    with pytest.raises(AnafConfigError, match="anafpy spv select"):
        _parse_certificate_result(
            json.dumps({"error": "not-found"}), thumbprint=_CANONICAL
        )


def test_certificate_without_private_key_is_refused() -> None:
    with pytest.raises(AnafConfigError, match="no usable private key"):
        _parse_certificate_result(
            json.dumps({"error": "no-private-key"}), thumbprint=_CANONICAL
        )


def test_expired_certificate_is_refused_before_signing() -> None:
    # Discovery filters expired certificates, but a persisted selection can
    # lapse: fail here rather than let ANAF reject the filing.
    with pytest.raises(AnafConfigError, match="expired on 2026-05-01"):
        _parse_certificate_result(
            _certificate_json(not_after="2026-05-01"),
            thumbprint=_CANONICAL,
            today=date(2026, 7, 26),
        )


def test_certificate_valid_today_is_accepted() -> None:
    assert (
        _parse_certificate_result(
            _certificate_json(b"leaf", not_after="2026-07-26"),
            thumbprint=_CANONICAL,
            today=date(2026, 7, 26),
        )
        == b"leaf"
    )


def test_malformed_certificate_bytes_are_refused() -> None:
    with pytest.raises(AnafConfigError, match="malformed certificate bytes"):
        _parse_certificate_result(
            json.dumps({"certificate": "not base64!", "not_after": "2099-01-01"}),
            thumbprint=_CANONICAL,
        )


@pytest.mark.parametrize("stdout", ["", "Get-ChildItem : oops", "[]", "{}"])
def test_unrecognised_certificate_output_is_refused(stdout: str) -> None:
    with pytest.raises(AnafConfigError, match="unrecognised certificate output"):
        _parse_certificate_result(stdout, thumbprint=_CANONICAL)


# -- signing -------------------------------------------------------------------------


async def test_windows_sign_round_trip(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    _stub_certificate_read(monkeypatch, stdout=_certificate_json())
    captured = _stub_signature_run(monkeypatch, _writes(b"raw-signature"))
    signer = WindowsStoreRawSigner(_THUMB, sign_timeout=5.0)

    assert await signer.sign(b"the-bytes-to-sign") == b"raw-signature"

    assert captured["payload"] == b"the-bytes-to-sign"
    assert captured["env"]["ANAFPY_SIGN_THUMBPRINT"] == _CANONICAL
    assert captured["timeout"] == 5.0
    assert captured["argv"][0] == "powershell.exe"
    # The payload never outlives the call: no signing input left on disk.
    assert not Path(captured["env"]["ANAFPY_SIGN_PAYLOAD_FILE"]).exists()


async def test_dismissed_approval_is_reported_as_a_signing_failure(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    _stub_certificate_read(monkeypatch, stdout=_certificate_json())

    def cancelled(_env: dict[str, str]) -> tuple[int, bytes, bytes]:
        return 1, b"", b"Keyset not defined. PIN dialog cancelled"

    _stub_signature_run(monkeypatch, cancelled)
    signer = WindowsStoreRawSigner(_THUMB)
    with pytest.raises(
        AnafConfigError, match=r"signing failed: .*PIN dialog cancelled"
    ):
        await signer.sign(b"payload")


async def test_unanswered_approval_times_out(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    _stub_certificate_read(monkeypatch, stdout=_certificate_json())

    def hang(_env: dict[str, str]) -> tuple[int, bytes, bytes]:
        raise TimeoutError

    _stub_signature_run(monkeypatch, hang)
    signer = WindowsStoreRawSigner(_THUMB, sign_timeout=7.0)
    with pytest.raises(AnafConfigError, match="signing timed out after 7s"):
        await signer.sign(b"payload")


async def test_truncated_signature_is_refused(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    # A partial signature must never reach pyHanko — it would embed a silently
    # invalid one.
    _stub_certificate_read(monkeypatch, stdout=_certificate_json())
    _stub_signature_run(monkeypatch, _writes(b"abc", reported=256))
    signer = WindowsStoreRawSigner(_THUMB)
    with pytest.raises(AnafConfigError, match=r"signature is 3 bytes.*reported 256"):
        await signer.sign(b"payload")


async def test_unwritten_signature_is_refused(
    monkeypatch: pytest.MonkeyPatch, on_windows: None
) -> None:
    _stub_certificate_read(monkeypatch, stdout=_certificate_json())

    def writes_nothing(_env: dict[str, str]) -> tuple[int, bytes, bytes]:
        return 0, json.dumps({"signature_length": 256}).encode(), b""

    _stub_signature_run(monkeypatch, writes_nothing)
    signer = WindowsStoreRawSigner(_THUMB)
    with pytest.raises(AnafConfigError, match="signature file was not written"):
        await signer.sign(b"payload")


def test_unreachable_rsa_key_names_the_middleware() -> None:
    with pytest.raises(AnafConfigError, match="CNG or a CSP"):
        _parse_signature_result(
            json.dumps({"error": "no-rsa-key"}), thumbprint=_CANONICAL
        )


def test_certificate_lost_between_runs_is_reported() -> None:
    with pytest.raises(AnafConfigError, match="no certificate with thumbprint"):
        _parse_signature_result(
            json.dumps({"error": "not-found"}), thumbprint=_CANONICAL
        )


@pytest.mark.parametrize(
    "stdout", ["", "oops", "{}", json.dumps({"signature_length": 0})]
)
def test_unrecognised_signature_output_is_refused(stdout: str) -> None:
    with pytest.raises(AnafConfigError, match="unrecognised signature output"):
        _parse_signature_result(stdout, thumbprint=_CANONICAL)
