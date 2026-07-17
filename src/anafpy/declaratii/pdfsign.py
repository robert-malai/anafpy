"""Embed a qualified signature into a DUK-rendered PDF with pyHanko.

DUKIntegrator ``-p`` renders the official PDF with the XML embedded; this module
adds a standard ``adbe.pkcs7.detached`` CMS signature as an **incremental
update**, so the ``/EmbeddedFiles`` tree the render produced survives untouched
and the signature covers the whole file. The raw RSA operation is delegated to a
:class:`~anafpy.declaratii.signing.RawSigner` (the OS / token middleware) — no
key material or PIN passes through here.

Requires the optional ``anafpy[declaratii]`` extra (pyHanko). Use
:func:`anafpy.declaratii.load_pdfsign` when a guarded optional import is needed.

Proven end-to-end 2026-07-15 (pyHanko 0.35.2): validation ``intact=True,
valid=True``, coverage ``ENTIRE_FILE``, embedded XML preserved.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
from pathlib import Path

import httpx
from asn1crypto import cms, pem, x509
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko_certvalidator.registry import SimpleCertificateStore

from .models import PdfSignResult
from .signing import RawSigner

__all__ = ["sign_pdf"]

_CA_CACHE_DIR = Path("~/.anafpy/ca-cache").expanduser()


class _RawSignerAdapter(signers.Signer):
    """pyHanko :class:`~pyhanko.sign.signers.Signer` backed by a :class:`RawSigner`."""

    def __init__(
        self, raw: RawSigner, leaf: x509.Certificate, registry: SimpleCertificateStore
    ) -> None:
        self._raw = raw
        self._sig_size = leaf.public_key.bit_size // 8
        super().__init__(signing_cert=leaf, cert_registry=registry)

    async def async_sign_raw(
        self, data: bytes, digest_algorithm: str, dry_run: bool = False
    ) -> bytes:
        if dry_run:
            # A placeholder the size of the real signature so pyHanko can lay out
            # the byte range; the real size is the RSA modulus, read from the key.
            return bytes(self._sig_size)
        if digest_algorithm.lower() != "sha256":
            raise ValueError(
                f"unexpected digest algorithm {digest_algorithm!r}; the signer "
                "produces SHA-256 PKCS#1 v1.5 signatures"
            )
        return await self._raw.sign(data)


async def sign_pdf(
    pdf: bytes, signer: RawSigner, *, field_name: str = "Semnatura1"
) -> PdfSignResult:
    """Sign *pdf* with *signer*, returning the signed bytes and chain status.

    The leaf certificate comes from the signer; its **direct** issuer is
    fetched best-effort from the leaf's AIA (``ca_issuers``) URL and cached
    under ``~/.anafpy/ca-cache/``. Only a certificate whose subject is the
    leaf's issuer name is embedded (AIA URLs are commonly plain ``http://``, so
    an unchecked body must never enter the chain). ``chain_complete=True``
    means exactly that this one issuer is embedded — the issuer's own AIA is
    never followed, so deeper intermediates (leaf → subCA₂ → subCA₁ → root)
    are not chased. If the fetch fails or the body is not the issuer, the CMS
    is leaf-only and ``chain_complete`` is ``False`` with a ``warning`` —
    portal acceptance of a leaf-only signature is unverified.
    """
    leaf_der = signer.certificate()
    leaf = x509.Certificate.load(leaf_der)
    registry = SimpleCertificateStore()  # type: ignore[no-untyped-call]
    chain_complete = False
    warning: str | None = None

    if (issuer_der := await _fetch_issuer(leaf)) is not None:
        registry.register(x509.Certificate.load(issuer_der))
        chain_complete = True
    else:
        warning = (
            "could not fetch the issuer certificate from the leaf's AIA URL; the "
            "signature is leaf-only — portal acceptance of a leaf-only chain is "
            "unverified"
        )

    pyhanko_signer = _RawSignerAdapter(signer, leaf, registry)
    meta = signers.PdfSignatureMetadata(field_name=field_name, md_algorithm="sha256")
    writer = IncrementalPdfFileWriter(io.BytesIO(pdf))
    output = io.BytesIO()
    await signers.async_sign_pdf(writer, meta, signer=pyhanko_signer, output=output)
    return PdfSignResult(
        pdf=output.getvalue(), chain_complete=chain_complete, warning=warning
    )


async def _fetch_issuer(leaf: x509.Certificate) -> bytes | None:
    """Fetch and validate the issuer certificate DER, best-effort.

    AIA endpoints commonly serve DER, PEM, or a PKCS#7 certificate bundle.
    A certificate is accepted only when its subject is the leaf's issuer name —
    the AIA fetch may ride cleartext ``http://``, so an arbitrary answer must
    not be embedded or cached. Only an accepted certificate is cached; corrupt
    or non-issuer cache entries are removed and fetched once more.
    """
    url = _ca_issuers_url(leaf)
    if not url:
        return None
    cache = _CA_CACHE_DIR / f"{hashlib.sha256(url.encode()).hexdigest()[:16]}.crt"
    if cache.exists():
        try:
            cached = cache.read_bytes()
        except OSError:
            cached = b""
        if (issuer_der := _certificate_der(cached)) is not None and _is_leaf_issuer(
            issuer_der, leaf
        ):
            return issuer_der
        with contextlib.suppress(OSError):
            cache.unlink()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            issuer_der = _certificate_der(response.content)
    except httpx.HTTPError:
        return None
    if issuer_der is None or not _is_leaf_issuer(issuer_der, leaf):
        return None
    try:
        _CA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(issuer_der)
    except OSError:
        pass  # caching is an optimisation, not required
    return issuer_der


def _is_leaf_issuer(issuer_der: bytes, leaf: x509.Certificate) -> bool:
    """Whether the candidate certificate's subject is the leaf's issuer name.

    Compared via asn1crypto's normalized ``Name.hashable`` form (the idiom the
    validators use), so case/whitespace differences don't defeat the match.
    """
    candidate = x509.Certificate.load(issuer_der)
    return bool(candidate.subject.hashable == leaf.issuer.hashable)


def _certificate_der(data: bytes) -> bytes | None:
    """Extract one validated certificate as canonical DER from common AIA bodies."""
    if not data:
        return None
    candidates = [data]
    if pem.detect(data):
        try:
            _, _, unarmored = pem.unarmor(data)
        except ValueError:
            pass
        else:
            candidates.insert(0, unarmored)

    for candidate in candidates:
        try:
            certificate = x509.Certificate.load(candidate)
            _ = certificate.native  # force lazy ASN.1 validation before caching
        except (TypeError, ValueError):
            pass
        else:
            return bytes(certificate.dump())

        try:
            content = cms.ContentInfo.load(candidate)
            if content["content_type"].native != "signed_data":
                continue
            certificates = content["content"]["certificates"]
            if certificates is None:
                continue
            for choice in certificates:
                if choice.name != "certificate":
                    continue
                certificate = choice.chosen
                _ = certificate.native
                return bytes(certificate.dump())
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _ca_issuers_url(cert: x509.Certificate) -> str | None:
    """The ``ca_issuers`` HTTP URL from a certificate's AIA extension, if any."""
    for extension in cert["tbs_certificate"]["extensions"]:
        if extension["extn_id"].native != "authority_information_access":
            continue
        for description in extension["extn_value"].parsed:
            if description["access_method"].native != "ca_issuers":
                continue
            location = description["access_location"]
            if location.name == "uniform_resource_identifier":
                url = location.native
                if isinstance(url, str) and url.startswith(("http://", "https://")):
                    return url
    return None
