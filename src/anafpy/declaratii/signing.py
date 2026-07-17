"""The platform raw signer — a qualified signature without touching key material.

anafpy never handles the private key or the PIN/2FA (``DESIGN.md`` invariant):
the raw ``RSASSA-PKCS1-v1_5`` over SHA-256 is delegated to the OS, which drives
the token/cloud-HSM middleware. On macOS the qualified certificate lives behind
a CryptoTokenKit extension (certSIGN Paperless vToken: ``ro.certsign.vtoken.ctke``)
with **no PKCS#11 dylib**, so the key is reachable only through
Security.framework — and every raw signature fires the vToken phone approval,
which *is* the human gate.

:class:`KeychainRawSigner` ports the proven Swift reference semantics (a 70-line
``SecKeyCreateSignature`` program, validated end-to-end 2026-07-15) to **ctypes**
against Security.framework + CoreFoundation, so there is no build step and no new
runtime dependency. The Swift source is preserved as the semantic spec in
``docs/anaf-reference/declaratii/duk.md``.

Windows (a ``CngRawSigner`` or a DUK-``mscapi`` runner over the same
:class:`RawSigner` seam) is a later milestone; instantiating
:class:`KeychainRawSigner` off macOS raises :class:`AnafConfigError`.
"""

from __future__ import annotations

import asyncio
import ctypes
import importlib
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Protocol, cast, runtime_checkable

from ..exceptions import AnafConfigError
from ..spv.certs import DEFAULT_IDENTITY_PATH, load_selected_identity
from .models import PdfSignResult

__all__ = [
    "KeychainRawSigner",
    "RawSigner",
    "default_signed_path",
    "load_pdfsign",
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
    """Resolve which Keychain identity to sign with.

    Order: *explicit* > ``ANAFPY_SIGN_IDENTITY`` > the persisted SPV certificate
    selection (same qualified certificate). On macOS the selector is the
    Keychain identity **name**.

    Raises:
        AnafConfigError: nothing resolves — point the user at
            ``anafpy spv certs`` / ``anafpy spv select``.
    """
    if explicit:
        return explicit
    if env := os.environ.get("ANAFPY_SIGN_IDENTITY"):
        return env
    selected = load_selected_identity(identity_path)
    if selected is not None and selected.platform == "darwin":
        return selected.name
    raise AnafConfigError(
        "no signing certificate selected — set ANAFPY_SIGN_IDENTITY to the "
        "Keychain identity name, or run `anafpy spv certs` and "
        "`anafpy spv select` to pick the qualified certificate"
    )


class _Frameworks:
    """Lazily-loaded Security.framework + CoreFoundation ctypes handles.

    Kept off module import so this module imports on any platform (Linux CI);
    only constructing a :class:`KeychainRawSigner` touches the frameworks.
    """

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
            raise AnafConfigError(
                f"signing timed out after {self.sign_timeout:.0f}s — the "
                "certificate approval (PIN / phone 2FA) was not completed; retry"
            ) from None

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
