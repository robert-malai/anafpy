"""Ephemeral TLS for the OAuth callback listener.

ANAF's developer portal only registers ``https://`` callback URLs (an ``http://``
one is refused with HTTP 400 — verified 2026-07-02), so a local listener must
speak TLS — yet no public CA may issue a certificate for ``localhost`` (CA/Browser
Forum baseline requirements), so there is no certificate we could ship or obtain
that a browser would accept silently. The default login therefore generates a
**throwaway self-signed certificate per attempt**: the browser shows a one-time
"connection is not private" interstitial (the CLI announces it beforehand), the
user clicks through, and the redirect lands on the listener — no files to
create, nothing installed, nothing persisted.

The key pair is generated in memory and written only long enough for
``ssl.SSLContext.load_cert_chain`` (which insists on file paths) to read it,
inside a private temporary directory that is deleted immediately after. Users
who want a warning-free browser supply their own trusted certificate instead
(``--tls-cert``/``--tls-key`` — e.g. one minted with mkcert).
"""

from __future__ import annotations

import datetime
import ipaddress
import ssl
import tempfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

__all__ = ["ephemeral_server_context", "generate_self_signed_cert"]

#: One login attempt's lifespan, with slack for a slow certificate/2FA step.
_VALIDITY = datetime.timedelta(hours=24)
#: Tolerated clock skew between this machine and the browser's validator.
_CLOCK_SKEW = datetime.timedelta(minutes=5)


def generate_self_signed_cert(hostname: str) -> tuple[bytes, bytes]:
    """A throwaway self-signed certificate for ``hostname``: ``(cert, key)`` PEMs.

    The SANs cover ``hostname`` plus ``localhost`` and both loopback addresses,
    so the browser's only complaint is trust (self-signed), never a name
    mismatch. Not a CA, server-auth only, valid for ~a day.
    """
    key = ec.generate_private_key(ec.SECP256R1())
    sans: list[x509.GeneralName] = []
    for value in (hostname, "localhost", "127.0.0.1", "::1"):
        try:
            name: x509.GeneralName = x509.IPAddress(ipaddress.ip_address(value))
        except ValueError:
            name = x509.DNSName(value)
        if name not in sans:
            sans.append(name)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _CLOCK_SKEW)
        .not_valid_after(now + _VALIDITY)
        .add_extension(x509.SubjectAlternativeName(sans), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    return cert.public_bytes(Encoding.PEM), key_pem


def ephemeral_server_context(hostname: str = "localhost") -> ssl.SSLContext:
    """A TLS server context serving a freshly generated self-signed certificate.

    The PEMs touch disk only inside a private temporary directory, deleted as
    soon as the context has loaded them.
    """
    cert_pem, key_pem = generate_self_signed_cert(hostname)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # Pin the floor rather than inherit it (see cli._load_ssl_context).
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    with tempfile.TemporaryDirectory() as tmp:
        cert_path = Path(tmp) / "cert.pem"
        key_path = Path(tmp) / "key.pem"
        cert_path.write_bytes(cert_pem)
        key_path.touch(mode=0o600)  # perms set before the key material lands
        key_path.write_bytes(key_pem)
        context.load_cert_chain(cert_path, key_path)
    return context
