# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pyobjc-core>=10",
#     "pyobjc-framework-Cocoa>=10",
#     "pyobjc-framework-Security>=10",
#     "cryptography>=42",
# ]
# ///
"""M0 spike: call SPV `listaMesaje` via macOS Keychain mTLS (NSURLSession).

THROWAWAY CODE — not part of the library. Purpose: observe real behavior of
the Keychain + NSURLSession client-certificate path against
https://webserviced.anaf.ro/SPVWS2/rest/ before designing the transport:

  1. Can we find the qualified-certificate identity (certSIGN & co.) via
     SecItemCopyMatching, including token-backed ones (CryptoTokenKit)?
  2. When exactly does the client-certificate challenge fire, and when does
     the token middleware's PIN prompt appear?
  3. Does a second request on the SAME NSURLSession re-fire the challenge
     (connection/TLS-session reuse), and does a FRESH session re-prompt for
     the PIN (per-process PIN caching)?
  4. Does the service set session cookies (the reference Java client installs
     a CookieManager)?

Run (uv resolves the inline deps automatically):

    uv run spikes/spv_macos_keychain.py --list          # enumerate identities
    uv run spikes/spv_macos_keychain.py                 # auto-pick RO CA identity
    uv run spikes/spv_macos_keychain.py --label certSIGN --zile 5
    uv run spikes/spv_macos_keychain.py --thumbprint AB12... --cif 12345678

While it runs, note on paper WHEN the PIN / Keychain prompt appears relative
to the timestamped log lines — that's the data point M1's design needs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
import time
from datetime import UTC, datetime
from urllib.parse import urlencode

import objc
from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID, NameOID
from Foundation import (  # type: ignore[import-not-found]
    NSURL,
    NSMutableURLRequest,
    NSObject,
    NSURLCredential,
    NSURLSession,
    NSURLSessionConfiguration,
)
from Security import (  # type: ignore[import-not-found]
    SecCertificateCopyData,
    SecCertificateCopySubjectSummary,
    SecIdentityCopyCertificate,
    SecItemCopyMatching,
    kSecClass,
    kSecClassIdentity,
    kSecMatchLimit,
    kSecMatchLimitAll,
    kSecReturnRef,
)

BASE_URL = "https://webserviced.anaf.ro/SPVWS2/rest/listaMesaje"

# Issuer patterns for Romanian qualified-certificate CAs.
RO_QUALIFIED_CAS = re.compile(
    r"certsign|digisign|trans\s*sped|alfasign|alfatrust|certdigital|cert\s*digital",
    re.IGNORECASE,
)

# NSURLSession auth-challenge dispositions (NSURLSessionAuthChallengeDisposition).
USE_CREDENTIAL = 0
PERFORM_DEFAULT_HANDLING = 1

CLIENT_CERT_METHOD = "NSURLAuthenticationMethodClientCertificate"


def log(message: str) -> None:
    """Timestamped stderr line — correlate these with PIN-prompt appearances."""
    now = datetime.now(tz=UTC).astimezone()
    print(f"[{now:%H:%M:%S}.{now.microsecond // 1000:03d}] {message}", file=sys.stderr)


class CandidateIdentity:
    """A Keychain identity plus the certificate facts needed to choose one."""

    def __init__(self, identity: object, der: bytes) -> None:
        self.identity = identity
        self.thumbprint = hashlib.sha1(der).hexdigest().upper()
        self.cert = x509.load_der_x509_certificate(der)

    @property
    def subject(self) -> str:
        names = self.cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        return names[0].value if names else self.cert.subject.rfc4514_string()

    @property
    def issuer(self) -> str:
        names = self.cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        return names[0].value if names else self.cert.issuer.rfc4514_string()

    @property
    def has_client_auth_eku(self) -> bool:
        try:
            eku = self.cert.extensions.get_extension_for_oid(
                ExtensionOID.EXTENDED_KEY_USAGE
            )
        except x509.ExtensionNotFound:
            return False
        return ExtendedKeyUsageOID.CLIENT_AUTH in eku.value

    @property
    def expired(self) -> bool:
        return self.cert.not_valid_after_utc < datetime.now(tz=UTC)

    @property
    def romanian_qualified(self) -> bool:
        return bool(RO_QUALIFIED_CAS.search(self.issuer))

    def describe(self) -> str:
        flags = ", ".join(
            flag
            for flag, on in [
                ("clientAuth", self.has_client_auth_eku),
                ("EXPIRED", self.expired),
                ("RO qualified CA", self.romanian_qualified),
            ]
            if on
        )
        return (
            f"  subject:    {self.subject}\n"
            f"  issuer:     {self.issuer}\n"
            f"  thumbprint: {self.thumbprint}\n"
            f"  valid to:   {self.cert.not_valid_after_utc:%Y-%m-%d}\n"
            f"  flags:      {flags or '-'}"
        )


def enumerate_identities() -> list[CandidateIdentity]:
    """All Keychain identities (cert + private key), incl. CryptoTokenKit ones."""
    query = {
        kSecClass: kSecClassIdentity,
        kSecMatchLimit: kSecMatchLimitAll,
        kSecReturnRef: True,
    }
    status, refs = SecItemCopyMatching(query, None)
    if status == -25300:  # errSecItemNotFound
        return []
    if status != 0:
        raise SystemExit(f"SecItemCopyMatching failed: OSStatus {status}")
    candidates: list[CandidateIdentity] = []
    for identity in refs:
        cert_status, cert = SecIdentityCopyCertificate(identity, None)
        if cert_status != 0:
            log(f"skipping identity, SecIdentityCopyCertificate OSStatus {cert_status}")
            continue
        summary = SecCertificateCopySubjectSummary(cert)
        try:
            der = bytes(SecCertificateCopyData(cert))
            candidates.append(CandidateIdentity(identity, der))
        except Exception as exc:
            log(f"skipping identity '{summary}': cannot parse certificate ({exc})")
    return candidates


def pick_identity(
    candidates: list[CandidateIdentity], thumbprint: str | None, label: str | None
) -> CandidateIdentity:
    if thumbprint:
        wanted = thumbprint.replace(":", "").replace(" ", "").upper()
        for c in candidates:
            if c.thumbprint == wanted:
                return c
        raise SystemExit(f"No identity with thumbprint {wanted}. Try --list.")
    if label:
        matches = [
            c
            for c in candidates
            if label.lower() in c.subject.lower() or label.lower() in c.issuer.lower()
        ]
        if len(matches) == 1:
            return matches[0]
        raise SystemExit(
            f"--label {label!r} matched {len(matches)} identities; "
            "disambiguate with --thumbprint (see --list)."
        )
    usable = [
        c
        for c in candidates
        if c.romanian_qualified and c.has_client_auth_eku and not c.expired
    ]
    if len(usable) == 1:
        return usable[0]
    raise SystemExit(
        f"Auto-pick found {len(usable)} Romanian qualified identities; "
        "pick one with --thumbprint or --label (see --list)."
    )


class ClientCertDelegate(NSObject):
    """Answers the TLS client-certificate challenge with the chosen identity."""

    def initWithIdentity_(self, identity: object) -> ClientCertDelegate:
        self = objc.super(ClientCertDelegate, self).init()
        self._identity = identity
        self.challenge_log: list[str] = []
        return self

    @objc.python_method
    def handle_challenge(self, challenge: object, completion_handler: object) -> None:
        space = challenge.protectionSpace()
        method = str(space.authenticationMethod())
        self.challenge_log.append(method)
        if method == CLIENT_CERT_METHOD:
            log(
                "client-certificate challenge received "
                f"(host={space.host()}, previous failures="
                f"{challenge.previousFailureCount()}) — answering with identity; "
                "a PIN prompt, if any, fires NOW"
            )
            credential = (
                NSURLCredential.credentialWithIdentity_certificates_persistence_(
                    self._identity,
                    None,
                    1,  # NSURLCredentialPersistenceForSession
                )
            )
            completion_handler(USE_CREDENTIAL, credential)
        else:
            log(f"challenge {method} — default handling")
            completion_handler(PERFORM_DEFAULT_HANDLING, None)

    # TLS challenges can arrive at either level depending on macOS version.
    def URLSession_didReceiveChallenge_completionHandler_(
        self, session: object, challenge: object, completion_handler: object
    ) -> None:
        self.handle_challenge(challenge, completion_handler)

    def URLSession_task_didReceiveChallenge_completionHandler_(
        self,
        session: object,
        task: object,
        challenge: object,
        completion_handler: object,
    ) -> None:
        self.handle_challenge(challenge, completion_handler)


def make_session(identity: CandidateIdentity) -> tuple[object, ClientCertDelegate]:
    config = NSURLSessionConfiguration.ephemeralSessionConfiguration()
    delegate = ClientCertDelegate.alloc().initWithIdentity_(identity.identity)
    session = NSURLSession.sessionWithConfiguration_delegate_delegateQueue_(
        config, delegate, None
    )
    return session, delegate


def fetch(
    session: object, url: str, timeout: float = 90.0
) -> tuple[int, dict[str, str], bytes]:
    """One GET on the given NSURLSession, synchronously."""
    done = threading.Event()
    outcome: dict[str, object] = {}

    def completion(data: object, response: object, error: object) -> None:
        outcome["data"] = bytes(data) if data is not None else b""
        outcome["response"] = response
        outcome["error"] = error
        done.set()

    request = NSMutableURLRequest.requestWithURL_(NSURL.URLWithString_(url))
    log(f"GET {url}")
    started = time.monotonic()
    session.dataTaskWithRequest_completionHandler_(request, completion).resume()
    if not done.wait(timeout):
        raise SystemExit(f"request timed out after {timeout}s (PIN prompt dismissed?)")
    elapsed = time.monotonic() - started
    if outcome["error"] is not None:
        raise SystemExit(f"request failed after {elapsed:.2f}s: {outcome['error']}")
    response = outcome["response"]
    headers = {str(k): str(v) for k, v in response.allHeaderFields().items()}
    log(f"HTTP {response.statusCode()} in {elapsed:.2f}s")
    return int(response.statusCode()), headers, outcome["data"]  # type: ignore[return-value]


def show_body(body: bytes) -> None:
    if body.startswith(b"%PDF"):
        print(f"(PDF document, {len(body)} bytes)")
        return
    try:
        parsed = json.loads(body)
    except ValueError:
        print(body[:2000].decode("utf-8", errors="replace"))
        return
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    if isinstance(parsed, dict) and "eroare" in parsed:
        print(
            "\nNOTE: response carries an `eroare` note (may be a plain "
            "'no messages in the last N days' — see docs/anaf-reference/spv/api.md §2)."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--list", action="store_true", help="enumerate identities and exit"
    )
    parser.add_argument("--thumbprint", help="pick identity by SHA-1 thumbprint (hex)")
    parser.add_argument("--label", help="pick identity by subject/issuer substring")
    parser.add_argument(
        "--zile", type=int, default=5, help="look-back days (default 5)"
    )
    parser.add_argument("--cif", help="optional CUI/CNP filter")
    parser.add_argument(
        "--skip-fresh-session",
        action="store_true",
        help="skip the third request on a new NSURLSession",
    )
    args = parser.parse_args()

    candidates = enumerate_identities()
    if args.list:
        print(f"{len(candidates)} identities in Keychain (incl. token-backed):\n")
        for i, c in enumerate(candidates):
            print(f"[{i}]\n{c.describe()}\n")
        return
    if not candidates:
        raise SystemExit(
            "No identities in Keychain. Is the token plugged in / middleware installed?"
        )

    chosen = pick_identity(candidates, args.thumbprint, args.label)
    print(f"Using identity:\n{chosen.describe()}\n", file=sys.stderr)

    params = {"zile": str(args.zile)}
    if args.cif:
        params["cif"] = args.cif
    url = f"{BASE_URL}?{urlencode(params)}"

    session, delegate = make_session(chosen)

    log("--- request 1 (new session; expect handshake + client-cert challenge) ---")
    _, headers, body = fetch(session, url)
    if cookies := headers.get("Set-Cookie"):
        log(f"Set-Cookie observed: {cookies}")
    show_body(body)

    log("--- request 2 (SAME session; challenge again = no connection reuse) ---")
    challenges_before = len(delegate.challenge_log)
    fetch(session, url)
    reused = len(delegate.challenge_log) == challenges_before
    new_challenges = len(delegate.challenge_log) - challenges_before
    log(f"request 2 fired {new_challenges} new challenge(s)")

    fresh_client_cert_challenges = None
    if not args.skip_fresh_session:
        log("--- request 3 (FRESH session; watch whether the PIN prompt re-fires) ---")
        session2, delegate2 = make_session(chosen)
        fetch(session2, url)
        fresh_client_cert_challenges = delegate2.challenge_log.count(CLIENT_CERT_METHOD)

    print("\n=== Observations for the transport design ===", file=sys.stderr)
    print(
        f"session 1 challenges: {delegate.challenge_log}\n"
        f"request 2 reused the connection/TLS session: {reused}\n"
        + (
            f"fresh session client-cert challenges: {fresh_client_cert_challenges} "
            "(did the PIN prompt appear again? note it down)\n"
            if fresh_client_cert_challenges is not None
            else ""
        ),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
