"""pyHanko embedding round-trip with a software fake :class:`RawSigner`.

No Keychain, no token: a throwaway RSA key signs in-process, so the whole
sign → validate path (byte coverage, embedded-file survival, chain completion)
runs credential-free in CI.
"""

from __future__ import annotations

import datetime
import io
from pathlib import Path

import httpx
import pytest
import respx
from asn1crypto import x509 as ax509
from cryptography import x509 as cx509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import AuthorityInformationAccessOID, NameOID
from pyhanko.pdf_utils import embed
from pyhanko.pdf_utils.generic import (
    ArrayObject,
    DictionaryObject,
    NumberObject,
    pdf_name,
)
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.writer import PdfFileWriter
from pyhanko.sign.validation import async_validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

from anafpy.declaratii.pdfsign import sign_pdf

_EPOCH = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
_ISSUER_URL = "http://ca.example.test/issuer.crt"


def _make_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _self_signed(key: rsa.RSAPrivateKey, name: str, *, aia: bool = False) -> bytes:
    who = cx509.Name([cx509.NameAttribute(NameOID.COMMON_NAME, name)])
    builder = (
        cx509.CertificateBuilder()
        .subject_name(who)
        .issuer_name(who)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(_EPOCH)
        .not_valid_after(_EPOCH + datetime.timedelta(days=3650))
    )
    if aia:
        builder = builder.add_extension(
            cx509.AuthorityInformationAccess(
                [
                    cx509.AccessDescription(
                        AuthorityInformationAccessOID.CA_ISSUERS,
                        cx509.UniformResourceIdentifier(_ISSUER_URL),
                    )
                ]
            ),
            critical=False,
        )
    return builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.DER)


class FakeSigner:
    """Software :class:`~anafpy.declaratii.signing.RawSigner` over a test RSA key."""

    def __init__(self, key: rsa.RSAPrivateKey, cert_der: bytes) -> None:
        self._key = key
        self._cert = cert_der

    def certificate(self) -> bytes:
        return self._cert

    async def sign(self, data: bytes) -> bytes:
        return self._key.sign(data, padding.PKCS1v15(), hashes.SHA256())


def _build_pdf_with_attachment() -> bytes:
    writer = PdfFileWriter()
    page = DictionaryObject(
        {
            pdf_name("/Type"): pdf_name("/Page"),
            pdf_name("/MediaBox"): ArrayObject(
                [NumberObject(0), NumberObject(0), NumberObject(612), NumberObject(792)]
            ),
            pdf_name("/Resources"): DictionaryObject({}),
        }
    )
    writer.insert_page(page)
    ef = embed.EmbeddedFileObject.from_file_data(
        writer, data=b"<x/>", mime_type="application/xml"
    )
    embed.embed_file(
        writer, embed.FileSpec(file_spec_string="attach.xml", embedded_data=ef)
    )
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


async def _validate(signed: bytes, trust_der: bytes) -> object:
    vc = ValidationContext(
        extra_trust_roots=[ax509.Certificate.load(trust_der)], allow_fetching=False
    )
    reader = PdfFileReader(io.BytesIO(signed))
    return await async_validate_pdf_signature(reader.embedded_signatures[0], vc)


def _has_embedded_files(signed: bytes) -> bool:
    reader = PdfFileReader(io.BytesIO(signed))
    names = reader.root.get("/Names")
    names = names.get_object() if names is not None else None
    return names is not None and "/EmbeddedFiles" in names


async def test_sign_and_validate_round_trip() -> None:
    key = _make_key()
    leaf = _self_signed(key, "TEST LEAF")
    base = _build_pdf_with_attachment()

    result = await sign_pdf(base, FakeSigner(key, leaf))

    status = await _validate(result.pdf, leaf)
    assert status.intact and status.valid  # type: ignore[attr-defined]
    assert status.coverage.name == "ENTIRE_FILE"  # type: ignore[attr-defined]
    assert _has_embedded_files(result.pdf)


async def test_leaf_only_chain_warns() -> None:
    key = _make_key()
    leaf = _self_signed(key, "TEST LEAF")  # no AIA -> no issuer to fetch
    base = _build_pdf_with_attachment()

    result = await sign_pdf(base, FakeSigner(key, leaf))

    assert result.chain_complete is False
    assert result.warning is not None
    assert "leaf-only" in result.warning


@respx.mock
async def test_chain_completed_from_aia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = _make_key()
    leaf = _self_signed(key, "TEST LEAF", aia=True)
    issuer_key = _make_key()
    issuer = _self_signed(issuer_key, "TEST CA")
    respx.get(_ISSUER_URL).mock(return_value=httpx.Response(200, content=issuer))
    base = _build_pdf_with_attachment()

    # Point the AIA cache at a temp dir so a real ~/.anafpy cache can't shadow it.
    monkeypatch.setattr(
        "anafpy.declaratii.pdfsign._CA_CACHE_DIR", tmp_path / "ca-cache"
    )

    result = await sign_pdf(base, FakeSigner(key, leaf))

    assert result.chain_complete is True
    assert result.warning is None
