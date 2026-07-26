"""The platform raw signer — a qualified signature without touching key material.

anafpy never handles the private key or the PIN/2FA (``DESIGN.md`` invariant):
the raw ``RSASSA-PKCS1-v1_5`` over SHA-256 is delegated to the OS, which drives
the token/cloud-HSM middleware. Every raw signature fires that middleware's
approval prompt (a token PIN dialog, or the certSIGN vToken phone approval),
which *is* the human gate. :func:`platform_raw_signer` is the one place the
platform is chosen; both implementations satisfy :class:`RawSigner`, so
everything downstream (:mod:`anafpy.declaratii.pdfsign`, the CLI, the MCP tools)
is platform-neutral.

**macOS** — the qualified certificate lives behind a CryptoTokenKit extension
(certSIGN Paperless vToken: ``ro.certsign.vtoken.ctke``) with **no PKCS#11
dylib**, so the key is reachable only through Security.framework.
:class:`KeychainRawSigner` ports the proven Swift reference semantics (a 70-line
``SecKeyCreateSignature`` program, validated end-to-end 2026-07-15) to **ctypes**
against Security.framework + CoreFoundation, so there is no build step and no new
runtime dependency. The Swift source is preserved as the semantic spec in
``docs/anaf-reference/declaratii/duk.md``. The selector is the Keychain identity
**name**, which can collide after a renewal — an ambiguous name is refused
rather than resolved blindly.

**Windows** — :class:`WindowsStoreRawSigner` drives ``powershell.exe`` over
``Cert:\\CurrentUser\\My``, the same store :mod:`anafpy.spv.certs` enumerates,
selecting by SHA-1 **thumbprint** (unlike a name, a thumbprint cannot be
ambiguous). ``RSACertificateExtensions.GetRSAPrivateKey(...).SignData(...)``
covers a CNG/KSP key and a legacy CSP key through one call, so there is no
key-kind branch here and no ctypes against ``ncrypt.dll``; the key stays
non-exportable, and the middleware raises its PIN dialog on the user's desktop
(so signing is host-side, like every other interactive step). DUK's own ``-s``
with ``mscapi`` stays rejected — it would route the PIN through DUK's process.

Instantiating either class on the other platform raises
:class:`AnafConfigError`.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import ctypes
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol, cast, runtime_checkable

from .._transport.subprocess import run_subprocess
from ..exceptions import AnafConfigError
from ..spv.certs import DEFAULT_IDENTITY_PATH, load_selected_identity
from .models import PdfSignResult

__all__ = [
    "KeychainRawSigner",
    "RawSigner",
    "WindowsStoreRawSigner",
    "default_signed_path",
    "load_pdfsign",
    "platform_raw_signer",
    "resolve_signing_label",
]

#: Wall-clock budget for one raw signature, i.e. for the human's out-of-band
#: PIN/2FA approval. Mirrors the SPV bootstrap's bounded-wait stance.
_SIGN_TIMEOUT = 110.0

_SECURITY_PATH = "/System/Library/Frameworks/Security.framework/Security"
_CF_PATH = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"

_ERR_SEC_SUCCESS = 0
_CF_STRING_ENCODING_UTF8 = 0x08000100


@runtime_checkable
class RawSigner(Protocol):
    """A raw ``RSASSA-PKCS1-v1_5`` / SHA-256 signer over the qualified key.

    The implementation hashes *data* with SHA-256 internally (the OS "message"
    signing algorithms do), so callers pass the data to sign, not a digest.
    """

    def certificate(self) -> bytes:
        """The leaf (signing) certificate, DER-encoded."""
        ...

    async def sign(self, data: bytes) -> bytes:
        """Raw signature bytes over *data* (SHA-256, PKCS#1 v1.5)."""
        ...


def default_signed_path(source: Path) -> Path:
    """Return the conventional ``<stem>-semnat.pdf`` path beside *source*."""
    source = Path(source).expanduser()
    return source.with_name(f"{source.stem}-semnat.pdf")


class PdfSignModule(Protocol):
    """Typed shape of the optional :mod:`anafpy.declaratii.pdfsign` module."""

    async def sign_pdf(
        self, pdf: bytes, signer: RawSigner, *, field_name: str = "Semnatura1"
    ) -> PdfSignResult: ...


def load_pdfsign() -> PdfSignModule:
    """Load the optional pyHanko-backed signing module with an install hint."""
    try:
        module = importlib.import_module(".pdfsign", __package__)
    except ModuleNotFoundError as exc:
        raise AnafConfigError(
            "signing needs the anafpy[declaratii] extra — install it with "
            "`pip install 'anafpy[declaratii]'`"
        ) from exc
    return cast(PdfSignModule, module)


def resolve_signing_label(
    explicit: str | None = None,
    *,
    identity_path: str | os.PathLike[str] = DEFAULT_IDENTITY_PATH,
) -> str:
    """Resolve which platform-store certificate to sign with.

    Order: *explicit* > ``ANAFPY_SIGN_IDENTITY`` > the persisted SPV certificate
    selection (same qualified certificate). The selector is what this platform's
    signer takes — the Keychain identity **name** on macOS, the SHA-1
    **thumbprint** on Windows — which is exactly
    :attr:`~anafpy.spv.certs.SelectedIdentity.bootstrap_identity`. A selection
    made on the *other* platform is ignored rather than mistranslated (a synced
    home directory carries the file across machines).

    Raises:
        AnafConfigError: nothing resolves — point the user at
            ``anafpy spv certs`` / ``anafpy spv select``.
    """
    if explicit:
        return explicit
    if env := os.environ.get("ANAFPY_SIGN_IDENTITY"):
        return env
    selected = load_selected_identity(identity_path)
    if selected is not None and selected.platform == sys.platform:
        return selected.bootstrap_identity
    match sys.platform:
        case "win32":
            hint = "set ANAFPY_SIGN_IDENTITY to the certificate's SHA-1 thumbprint"
        case _:
            hint = "set ANAFPY_SIGN_IDENTITY to the Keychain identity name"
    raise AnafConfigError(
        f"no signing certificate selected — {hint}, or run `anafpy spv certs` "
        "and `anafpy spv select` to pick the qualified certificate"
    )


def platform_raw_signer(
    label: str, *, sign_timeout: float = _SIGN_TIMEOUT
) -> RawSigner:
    """The :class:`RawSigner` for this platform, over the certificate *label*.

    *label* is an already-resolved selector (see :func:`resolve_signing_label`),
    kept a separate step so a caller can name the certificate to the user
    *before* the signer touches the key store.

    Raises:
        AnafConfigError: the platform has no signer, or *label* names no usable
            certificate.
    """
    match sys.platform:
        case "darwin":
            return KeychainRawSigner(label, sign_timeout=sign_timeout)
        case "win32":
            return WindowsStoreRawSigner(label, sign_timeout=sign_timeout)
        case other:
            raise AnafConfigError(
                "certificate signing needs a platform key store — macOS "
                f"(Keychain) or Windows (CertStore); not {other!r}"
            )


def _timed_out(seconds: float) -> AnafConfigError:
    """The shared "the human never approved" failure, identical on both platforms."""
    return AnafConfigError(
        f"signing timed out after {seconds:.0f}s — the certificate approval "
        "(PIN / phone 2FA) was not completed; retry"
    )


# --- macOS ------------------------------------------------------------------------


class _Frameworks:
    """Lazily-loaded Security.framework + CoreFoundation ctypes handles.

    Kept off module import so this module imports on any platform (Linux CI);
    only constructing a :class:`KeychainRawSigner` touches the frameworks.
    """

    # Annotated at class level: on non-darwin platforms mypy treats the
    # assignments below as unreachable and cannot infer the attribute types.
    sec: ctypes.CDLL
    cf: ctypes.CDLL

    def __init__(self) -> None:
        if sys.platform != "darwin":
            raise AnafConfigError(
                "certificate signing via the Keychain is macOS-only in this "
                f"release; not available on {sys.platform!r} (Windows follows)"
            )
        self.sec = ctypes.CDLL(_SECURITY_PATH)
        self.cf = ctypes.CDLL(_CF_PATH)
        self._configure()

    def _configure(self) -> None:
        cf, sec = self.cf, self.sec
        p = ctypes.c_void_p
        cfindex = ctypes.c_long

        cf.CFRelease.argtypes = [p]
        cf.CFRelease.restype = None
        cf.CFRetain.argtypes = [p]
        cf.CFRetain.restype = p
        cf.CFStringGetLength.argtypes = [p]
        cf.CFStringGetLength.restype = cfindex
        cf.CFStringGetCString.argtypes = [p, ctypes.c_char_p, cfindex, ctypes.c_uint32]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFDataCreate.argtypes = [p, ctypes.c_char_p, cfindex]
        cf.CFDataCreate.restype = p
        cf.CFDataGetLength.argtypes = [p]
        cf.CFDataGetLength.restype = cfindex
        cf.CFDataGetBytePtr.argtypes = [p]
        cf.CFDataGetBytePtr.restype = p
        cf.CFDictionaryCreate.argtypes = [p, p, p, cfindex, p, p]
        cf.CFDictionaryCreate.restype = p
        cf.CFDictionaryGetValue.argtypes = [p, p]
        cf.CFDictionaryGetValue.restype = p
        cf.CFArrayGetCount.argtypes = [p]
        cf.CFArrayGetCount.restype = cfindex
        cf.CFArrayGetValueAtIndex.argtypes = [p, cfindex]
        cf.CFArrayGetValueAtIndex.restype = p
        cf.CFErrorCopyDescription.argtypes = [p]
        cf.CFErrorCopyDescription.restype = p

        sec.SecItemCopyMatching.argtypes = [p, ctypes.POINTER(p)]
        sec.SecItemCopyMatching.restype = ctypes.c_int32
        sec.SecIdentityCopyCertificate.argtypes = [p, ctypes.POINTER(p)]
        sec.SecIdentityCopyCertificate.restype = ctypes.c_int32
        sec.SecCertificateCopyData.argtypes = [p]
        sec.SecCertificateCopyData.restype = p
        sec.SecIdentityCopyPrivateKey.argtypes = [p, ctypes.POINTER(p)]
        sec.SecIdentityCopyPrivateKey.restype = ctypes.c_int32
        sec.SecKeyCreateSignature.argtypes = [p, p, p, ctypes.POINTER(p)]
        sec.SecKeyCreateSignature.restype = p

        # Global constants (all pointer-valued: CFStringRef keys/values, a
        # CFBooleanRef, and the dictionary callback structs by address).
        self.kSecClass = self._const(sec, "kSecClass")
        self.kSecClassIdentity = self._const(sec, "kSecClassIdentity")
        self.kSecMatchLimit = self._const(sec, "kSecMatchLimit")
        self.kSecMatchLimitAll = self._const(sec, "kSecMatchLimitAll")
        self.kSecReturnRef = self._const(sec, "kSecReturnRef")
        self.kSecReturnAttributes = self._const(sec, "kSecReturnAttributes")
        self.kSecAttrLabel = self._const(sec, "kSecAttrLabel")
        self.kSecValueRef = self._const(sec, "kSecValueRef")
        self.kSecAlgo = self._const(
            sec, "kSecKeyAlgorithmRSASignatureMessagePKCS1v15SHA256"
        )
        self.kCFBooleanTrue = self._const(cf, "kCFBooleanTrue")
        # Addresses of the callback structs (not their contents).
        self.key_callbacks = ctypes.addressof(
            p.in_dll(cf, "kCFTypeDictionaryKeyCallBacks")
        )
        self.value_callbacks = ctypes.addressof(
            p.in_dll(cf, "kCFTypeDictionaryValueCallBacks")
        )

    @staticmethod
    def _const(lib: ctypes.CDLL, name: str) -> int:
        """Read a pointer-valued global constant as an int (for argument passing)."""
        return ctypes.c_void_p.in_dll(lib, name).value or 0

    # -- small CF helpers --------------------------------------------------------------

    def cfstr_to_str(self, cfstr: int) -> str | None:
        if not cfstr:
            return None
        length = self.cf.CFStringGetLength(cfstr)
        buffer = ctypes.create_string_buffer((int(length) + 1) * 4)
        ok = self.cf.CFStringGetCString(
            cfstr, buffer, len(buffer), _CF_STRING_ENCODING_UTF8
        )
        return buffer.value.decode("utf-8") if ok else None

    def cfdata_to_bytes(self, cfdata: int) -> bytes:
        length = int(self.cf.CFDataGetLength(cfdata))
        ptr = self.cf.CFDataGetBytePtr(cfdata)
        return ctypes.string_at(ptr, length)

    def bytes_to_cfdata(self, data: bytes) -> int:
        return self.cf.CFDataCreate(None, data, len(data)) or 0

    def make_query(self, pairs: list[tuple[int, int]]) -> int:
        count = len(pairs)
        keys = (ctypes.c_void_p * count)(*[k for k, _ in pairs])
        values = (ctypes.c_void_p * count)(*[v for _, v in pairs])
        return (
            self.cf.CFDictionaryCreate(
                None,
                keys,
                values,
                count,
                self.key_callbacks,
                self.value_callbacks,
            )
            or 0
        )

    def error_description(self, cferror: int) -> str:
        if not cferror:
            return "unknown error"
        desc = self.cf.CFErrorCopyDescription(cferror)
        text = self.cfstr_to_str(desc) or "unknown error"
        if desc:
            self.cf.CFRelease(desc)
        return text


@lru_cache(maxsize=1)
def _frameworks() -> _Frameworks:
    """Return the immutable platform-framework bindings shared by all signers."""
    return _Frameworks()


class KeychainRawSigner:
    """A :class:`RawSigner` over a macOS Keychain / CryptoTokenKit identity.

    Args:
        label: the Keychain identity **name** (see
            :func:`~anafpy.spv.certs.list_keychain_identities`). Resolve it with
            :func:`resolve_signing_label` when you want the env/SPV-selection
            defaults.
        sign_timeout: seconds to wait for one signature — i.e. for the user's
            out-of-band PIN/2FA approval.

    Raises:
        AnafConfigError: off macOS, or no identity with that label.
    """

    def __init__(self, label: str, *, sign_timeout: float = _SIGN_TIMEOUT) -> None:
        self.label = label
        self.sign_timeout = sign_timeout
        self._fw = _frameworks()
        self._identity = self._find_identity(label)
        self._certificate = self._copy_certificate(self._identity)

    def certificate(self) -> bytes:
        return self._certificate

    async def sign(self, data: bytes) -> bytes:
        """Raw signature over *data*; blocks on the middleware approval.

        The blocking ``SecKeyCreateSignature`` runs in a worker thread bounded by
        ``sign_timeout``; a timeout raises :class:`AnafConfigError` so the caller
        can surface a clean failure rather than hang.
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._sign_blocking, data),
                timeout=self.sign_timeout,
            )
        except TimeoutError:
            raise _timed_out(self.sign_timeout) from None

    # -- internals ---------------------------------------------------------------------

    def _find_identity(self, label: str) -> int:
        fw = self._fw
        query = fw.make_query(
            [
                (fw.kSecClass, fw.kSecClassIdentity),
                (fw.kSecMatchLimit, fw.kSecMatchLimitAll),
                (fw.kSecReturnRef, fw.kCFBooleanTrue),
                (fw.kSecReturnAttributes, fw.kCFBooleanTrue),
            ]
        )
        result = ctypes.c_void_p()
        status = fw.sec.SecItemCopyMatching(query, ctypes.byref(result))
        fw.cf.CFRelease(query)
        if status != _ERR_SEC_SUCCESS or not result.value:
            raise AnafConfigError(
                f"no signing identities in the Keychain (status {status}); "
                "run `anafpy spv certs` to list available certificates"
            )
        array = result.value
        try:
            count = int(fw.cf.CFArrayGetCount(array))
            matches: list[int] = []
            for index in range(count):
                item = fw.cf.CFArrayGetValueAtIndex(array, index)
                label_ref = fw.cf.CFDictionaryGetValue(item, fw.kSecAttrLabel)
                if fw.cfstr_to_str(label_ref) == label:
                    ref = fw.cf.CFDictionaryGetValue(item, fw.kSecValueRef)
                    if ref:
                        matches.append(int(ref))
            if len(matches) > 1:
                # Mirrors spv.certs.identity_by_thumbprint: names collide after
                # a certificate renewal, and picking one blindly could sign
                # with the expired certificate.
                raise AnafConfigError(
                    f"the Keychain holds {len(matches)} identities named "
                    f"{label!r} (e.g. a renewed certificate next to the old "
                    "one) — an ambiguous name could silently sign with the "
                    "wrong certificate, so remove or rename the stale one in "
                    "Keychain Access before signing"
                )
            if matches:
                fw.cf.CFRetain(matches[0])
                return matches[0]
            raise AnafConfigError(
                f"no Keychain identity named {label!r} — list the available "
                "certificates with `anafpy spv certs` and select again"
            )
        finally:
            fw.cf.CFRelease(array)

    def _copy_certificate(self, identity: int) -> bytes:
        fw = self._fw
        cert = ctypes.c_void_p()
        status = fw.sec.SecIdentityCopyCertificate(identity, ctypes.byref(cert))
        if status != _ERR_SEC_SUCCESS or not cert.value:
            raise AnafConfigError(
                f"cannot read the certificate for identity {self.label!r} "
                f"(status {status})"
            )
        try:
            data = fw.sec.SecCertificateCopyData(cert)
            der = fw.cfdata_to_bytes(data)
            fw.cf.CFRelease(data)
            return der
        finally:
            fw.cf.CFRelease(cert)

    def _sign_blocking(self, data: bytes) -> bytes:
        fw = self._fw
        key = ctypes.c_void_p()
        status = fw.sec.SecIdentityCopyPrivateKey(self._identity, ctypes.byref(key))
        if status != _ERR_SEC_SUCCESS or not key.value:
            raise AnafConfigError(
                f"cannot access the private key for {self.label!r} (status {status})"
            )
        cfdata = fw.bytes_to_cfdata(data)
        error = ctypes.c_void_p()
        try:
            signature = fw.sec.SecKeyCreateSignature(
                key, fw.kSecAlgo, cfdata, ctypes.byref(error)
            )
            if not signature:
                detail = fw.error_description(error.value or 0)
                if error.value:
                    # The CFError arrived through a Create-Rule out-parameter,
                    # so this side owns (and must release) it.
                    fw.cf.CFRelease(error.value)
                raise AnafConfigError(f"signing failed: {detail}")
            raw = fw.cfdata_to_bytes(signature)
            fw.cf.CFRelease(signature)
            return raw
        finally:
            fw.cf.CFRelease(cfdata)
            fw.cf.CFRelease(key)

    def __del__(self) -> None:
        # Best-effort release of the retained identity; guard everything because
        # __del__ may run during interpreter teardown.
        try:
            if getattr(self, "_identity", 0):
                self._fw.cf.CFRelease(self._identity)
        except Exception:
            pass


# --- Windows ----------------------------------------------------------------------

#: Windows PowerShell 5.1 ships on every supported Windows and carries the .NET
#: Framework 4.6+ ``RSA.SignData(byte[], HashAlgorithmName, RSASignaturePadding)``
#: overload both key kinds implement. Same interpreter :mod:`anafpy.spv.certs`
#: uses for discovery.
_POWERSHELL = "powershell.exe"

_THUMBPRINT_RE = re.compile(r"^[0-9A-F]{40}$")

# Both scripts take every value through the environment, never through the
# command line: no quoting or injection surface, and a path holding a Romanian
# certificate name cannot break the argv encoding. `Emit` writes one compact JSON
# object straight to the console stream, bypassing PowerShell's output formatter
# (which may wrap a long piped string at the host width). An expected, actionable
# condition is reported as {"error": "<slug>"} with exit 0, which leaves a
# non-zero exit to mean "PowerShell itself failed".
_EMIT_HELPER = r"""
$ErrorActionPreference = 'Stop'
function Emit($o) {
    [Console]::Out.Write((ConvertTo-Json -Compress -InputObject $o))
}
$found = @(Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { $_.Thumbprint -eq $env:ANAFPY_SIGN_THUMBPRINT })
if ($found.Count -eq 0) {
    Emit @{ error = 'not-found' }
    exit 0
}
$cert = $found[0]
"""

_WINDOWS_CERTIFICATE_SCRIPT = (
    _EMIT_HELPER
    + r"""
if (-not $cert.HasPrivateKey) {
    Emit @{ error = 'no-private-key' }
    exit 0
}
Emit @{
    certificate = [Convert]::ToBase64String($cert.RawData)
    not_after = $cert.NotAfter.ToString('yyyy-MM-dd')
}
"""
)

_WINDOWS_SIGN_SCRIPT = (
    _EMIT_HELPER
    + r"""
$ext = [Security.Cryptography.X509Certificates.RSACertificateExtensions]
$rsa = $ext::GetRSAPrivateKey($cert)
if ($null -eq $rsa) {
    Emit @{ error = 'no-rsa-key' }
    exit 0
}
try {
    $signature = $rsa.SignData(
        [IO.File]::ReadAllBytes($env:ANAFPY_SIGN_PAYLOAD_FILE),
        [Security.Cryptography.HashAlgorithmName]::SHA256,
        [Security.Cryptography.RSASignaturePadding]::Pkcs1)
} finally {
    $rsa.Dispose()
}
[IO.File]::WriteAllBytes($env:ANAFPY_SIGN_OUTPUT_FILE, $signature)
Emit @{ signature_length = $signature.Length }
"""
)


def _require_windows() -> None:
    """Refuse the Windows signer off Windows.

    Kept a function (like :func:`_frameworks` for macOS) so the signer's own body
    never sits behind a platform check mypy resolves as unreachable.

    Raises:
        AnafConfigError: not running on Windows.
    """
    if sys.platform != "win32":
        raise AnafConfigError(
            "certificate signing via the Windows certificate store needs "
            f"Windows; not available on {sys.platform!r}"
        )


def _normalize_thumbprint(selector: str) -> str:
    """Validate and canonicalise a SHA-1 thumbprint selector.

    Accepts the separator styles the Windows UIs copy out (``aa:bb``, ``aa bb``)
    and upper-cases, matching :func:`anafpy.spv.certs.identity_by_thumbprint`.
    The shape check is also the guard that keeps a stray selector out of the
    certificate-store lookup.

    Raises:
        AnafConfigError: not 40 hexadecimal digits.
    """
    thumbprint = selector.replace(":", "").replace(" ", "").upper()
    if not _THUMBPRINT_RE.match(thumbprint):
        raise AnafConfigError(
            f"{selector!r} is not a certificate thumbprint — Windows signing "
            "selects by the 40-hex-digit SHA-1 thumbprint (not the certificate "
            "name); run `anafpy spv certs` to list them"
        )
    return thumbprint


def _powershell_argv(script: str) -> list[str]:
    """The argv running *script* under a clean, non-interactive PowerShell."""
    return [_POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", script]


def _powershell_object(stdout: str, *, what: str) -> dict[str, object]:
    """Decode a script's single compact JSON object.

    Raises:
        AnafConfigError: the output is not a JSON object.
    """
    try:
        data = json.loads(stdout.strip() or "null")
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise AnafConfigError(
            f"unrecognised {what} output from PowerShell: {stdout.strip()[:200]!r}"
        )
    return data


def _no_certificate(thumbprint: str) -> AnafConfigError:
    return AnafConfigError(
        f"no certificate with thumbprint {thumbprint} in the Windows "
        "certificate store (Cert:\\CurrentUser\\My) — plug in the token or open "
        "its middleware, then run `anafpy spv certs` and `anafpy spv select` "
        "to pick the qualified certificate again"
    )


def _parse_certificate_result(
    stdout: str, *, thumbprint: str, today: date | None = None
) -> bytes:
    """The DER leaf certificate from ``_WINDOWS_CERTIFICATE_SCRIPT`` output.

    Args:
        stdout: the script's JSON output.
        thumbprint: the canonical thumbprint asked for, for the error messages.
        today: reference date for the expiry refusal (defaults to today, UTC).

    Raises:
        AnafConfigError: the certificate is absent, has no private key, has
            expired, or the output is unrecognisable.
    """
    match _powershell_object(stdout, what="certificate"):
        case {"error": "not-found"}:
            raise _no_certificate(thumbprint)
        case {"error": "no-private-key"}:
            raise AnafConfigError(
                f"the certificate {thumbprint} has no usable private key in this "
                "user's store — a signing certificate must be installed with "
                "its key (or its token middleware running)"
            )
        case {"certificate": str() as encoded, "not_after": str() as not_after}:
            # Discovery filters expired certificates, but the selection is
            # persisted and the certificate can lapse afterwards: refuse here
            # rather than let ANAF reject the filing.
            if (expiry := _parse_date(not_after)) is not None and expiry < (
                today or _today()
            ):
                raise AnafConfigError(
                    f"the certificate {thumbprint} expired on {not_after} — "
                    "renew it, then run `anafpy spv select` again"
                )
            try:
                return base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise AnafConfigError(
                    f"malformed certificate bytes for {thumbprint}: {exc}"
                ) from exc
        case other:
            raise AnafConfigError(
                f"unrecognised certificate output from PowerShell: {other!r}"
            )


def _parse_signature_result(stdout: str, *, thumbprint: str) -> int:
    """The signature length ``_WINDOWS_SIGN_SCRIPT`` reports it wrote.

    Raises:
        AnafConfigError: the certificate or its RSA key went away between the
            two runs, or the output is unrecognisable.
    """
    match _powershell_object(stdout, what="signature"):
        case {"error": "not-found"}:
            raise _no_certificate(thumbprint)
        case {"error": "no-rsa-key"}:
            raise AnafConfigError(
                f"the private key of {thumbprint} is not reachable as an RSA key "
                "— the token middleware must expose it through CNG or a CSP for "
                "anafpy to have the OS sign with it"
            )
        case {"signature_length": int() as length} if length > 0:
            return length
        case other:
            raise AnafConfigError(
                f"unrecognised signature output from PowerShell: {other!r}"
            )


def _today() -> date:
    """Today's date in UTC (the default reference for the expiry refusal)."""
    return datetime.now(UTC).date()


def _parse_date(text: str) -> date | None:
    """An ``yyyy-MM-dd`` date, or ``None`` when the shape is unexpected."""
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


class WindowsStoreRawSigner:
    """A :class:`RawSigner` over a Windows certificate-store identity.

    The leaf certificate is read at construction (no private-key use, so no
    PIN prompt); :meth:`sign` is what fires the middleware's approval.

    Args:
        thumbprint: the certificate's SHA-1 thumbprint (see
            :func:`~anafpy.spv.certs.list_windows_identities`). Resolve it with
            :func:`resolve_signing_label` when you want the env/SPV-selection
            defaults.
        sign_timeout: seconds to wait for one signature — i.e. for the user's
            out-of-band PIN/2FA approval.

    Raises:
        AnafConfigError: off Windows, *thumbprint* is malformed, or no usable
            certificate carries it.
    """

    def __init__(self, thumbprint: str, *, sign_timeout: float = _SIGN_TIMEOUT) -> None:
        _require_windows()
        self.thumbprint = _normalize_thumbprint(thumbprint)
        self.sign_timeout = sign_timeout
        self._certificate = self._load_certificate()

    def certificate(self) -> bytes:
        return self._certificate

    async def sign(self, data: bytes) -> bytes:
        """Raw signature over *data*; blocks on the middleware approval.

        The PowerShell run is bounded by ``sign_timeout`` and killed past it, so
        a dismissed or ignored PIN dialog fails cleanly instead of hanging.
        """
        with tempfile.TemporaryDirectory(prefix="anafpy-sign-") as directory:
            payload = Path(directory) / "payload.bin"
            output = Path(directory) / "signature.bin"
            payload.write_bytes(data)
            stdout = await self._run_signature(payload, output)
            expected = _parse_signature_result(stdout, thumbprint=self.thumbprint)
            try:
                signature = output.read_bytes()
            except OSError as exc:
                raise AnafConfigError(
                    f"the signature file was not written: {exc}"
                ) from exc
        if len(signature) != expected:
            # A short read means the write was truncated — never hand pyHanko a
            # partial signature, it would embed a silently invalid one.
            raise AnafConfigError(
                f"the signature is {len(signature)} bytes, PowerShell reported "
                f"{expected} — the signing run was interrupted; retry"
            )
        return signature

    # -- internals ---------------------------------------------------------------------

    def _environment(self, **extra: str) -> dict[str, str]:
        """The child environment: this process's, plus the script's inputs."""
        return os.environ | {"ANAFPY_SIGN_THUMBPRINT": self.thumbprint} | extra

    def _load_certificate(self) -> bytes:
        try:
            result = subprocess.run(
                _powershell_argv(_WINDOWS_CERTIFICATE_SCRIPT),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                env=self._environment(),
            )
        except OSError as exc:
            raise AnafConfigError(f"cannot run {_POWERSHELL}: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise AnafConfigError(
                f"reading certificate {self.thumbprint} timed out — the token "
                "middleware did not answer"
            ) from exc
        if result.returncode != 0:
            raise AnafConfigError(
                f"cannot read certificate {self.thumbprint}: "
                f"{result.stderr.strip() or result.stdout[:200]}"
            )
        return _parse_certificate_result(result.stdout, thumbprint=self.thumbprint)

    async def _run_signature(self, payload: Path, output: Path) -> str:
        environment = self._environment(
            ANAFPY_SIGN_PAYLOAD_FILE=str(payload),
            ANAFPY_SIGN_OUTPUT_FILE=str(output),
        )
        try:
            returncode, stdout, stderr = await run_subprocess(
                _powershell_argv(_WINDOWS_SIGN_SCRIPT),
                timeout=self.sign_timeout,
                env=environment,
            )
        except TimeoutError:
            raise _timed_out(self.sign_timeout) from None
        except OSError as exc:
            raise AnafConfigError(f"cannot run {_POWERSHELL}: {exc}") from exc
        if returncode != 0:
            # Where a dismissed PIN dialog, a wrong PIN, or a removed token
            # lands: the middleware throws, PowerShell reports it here.
            detail = _decode(stderr).strip() or _decode(stdout).strip()[:200]
            raise AnafConfigError(
                f"signing failed: {detail or f'PowerShell exited {returncode}'}"
            )
        return _decode(stdout)


def _decode(raw: bytes) -> str:
    """Decode child output; a Windows console may emit the OEM code page."""
    return raw.decode("utf-8", errors="replace")
