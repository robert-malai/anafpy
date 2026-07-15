"""Embed a qualified signature into a DUK-rendered PDF with pyHanko.

DUKIntegrator ``-p`` renders the official PDF with the XML embedded; this module
adds a standard ``adbe.pkcs7.detached`` CMS signature as an **incremental
update**, so the ``/EmbeddedFiles`` tree the render produced survives untouched
and the signature covers the whole file. The raw RSA operation is delegated to a
:class:`~anafpy.declaratii.signing.RawSigner` (the OS / token middleware) — no
key material or PIN passes through here.

Requires the optional ``anafpy[declaratii]`` extra (pyHanko). Callers should
import this module inside a ``try`` and translate :class:`ModuleNotFoundError`
into a "install anafpy[declaratii]" :class:`AnafConfigError`, mirroring the
``mcp`` extra's pattern.

Proven end-to-end 2026-07-15 (pyHanko 0.35.2): validation ``intact=True,
valid=True``, coverage ``ENTIRE_FILE``, embedded XML preserved.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import httpx
from asn1crypto import x509
from pydantic import BaseModel
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko_certvalidator.registry import SimpleCertificateStore

from .signing import RawSigner

__all__ = ["PdfSignResult", "sign_pdf"]

_CA_CACHE_DIR = Path("~/.anafpy/ca-cache").expanduser()


class PdfSignResult(BaseModel):
    """A signed PDF plus whether the issuer chain could be completed."""

    pdf: bytes
    #: The intermediate CA was embedded (chain leaf -> issuer), not leaf-only.
    chain_complete: bool
    #: Non-fatal note (e.g. the AIA fetch failed and the CMS is leaf-only).
    warning: str | None = None


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

    The leaf certificate comes from the signer; its issuer is fetched
    best-effort from the leaf's AIA (``ca_issuers``) URL and cached under
    ``~/.anafpy/ca-cache/``. If the fetch fails the CMS is leaf-only and
    ``chain_complete`` is ``False`` with a ``warning`` — portal acceptance of a
    leaf-only signature is unverified.
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
    """Fetch the issuer (CA) certificate DER from the leaf's AIA, best-effort."""
    url = _ca_issuers_url(leaf)
    if not url:
        return None
    cache = _CA_CACHE_DIR / f"{hashlib.sha256(url.encode()).hexdigest()[:16]}.crt"
    if cache.exists():
        return cache.read_bytes()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            der = response.content
    except httpx.HTTPError:
        return None
    try:
        _CA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(der)
    except OSError:
        pass  # caching is an optimisation, not required
    return der


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
