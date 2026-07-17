"""``anafpy`` CLI — host-side OAuth bootstrap, token inspection, and SPV login.

The interactive ``auth login`` runs where your certificate is (browser + USB token).
After that, tokens refresh headlessly, so this is needed only ~once a year.

``spv login`` is SPV's equivalent interactive step: the certificate TLS handshake
plus the token PIN / cloud-HSM 2FA prompt, yielding the cookie session the SPV
client (and the MCP ``spv_*`` tools) then ride non-interactively.
"""

from __future__ import annotations

import secrets
import ssl
import sys
import time
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import httpx
from cyclopts import App, Parameter

from .. import __version__
from ..auth import (
    CallbackListener,
    FileTokenStore,
    KeyringTokenStore,
    TokenStore,
    build_authorize_url,
    exchange_code,
    parse_redirect_url,
)
from ..exceptions import AnafAuthError, AnafConfigError, AnafError
from ..spv import (
    DEFAULT_SESSION_PATH,
    CurlBootstrapper,
    FileSessionStore,
    MessageList,
    SpvClient,
    SpvSessionProvider,
    discover_identities,
    identity_by_thumbprint,
    load_selected_identity,
    save_selected_identity,
)
from ..spv.certs import DEFAULT_IDENTITY_PATH

if TYPE_CHECKING:
    from ..declaratii import DukFinding, DukIntegrator

DEFAULT_STORE = "~/.anafpy/tokens.json"

#: How long the callback listener waits for the redirect before offering paste mode.
_CALLBACK_TIMEOUT = 180.0

_PASTE_HINT = (
    "After authorizing, your browser will show a connection error — that is\n"
    "expected. Copy the FULL URL from the address bar and paste it below\n"
    "(promptly: ANAF's code expires in ~60 seconds)."
)

app = App(
    name="anafpy",
    help="ANAF e-Factura / e-Transport / public-services client",
    version=f"anafpy {__version__}",
    # `main` owns the exit-code mapping (AnafError -> 1, Ctrl-C -> 130), so
    # commands hand their exit codes back instead of sys.exit()-ing inside
    # cyclopts, and KeyboardInterrupt propagates to `main`'s handler.
    result_action="return_value",
    suppress_keyboard_interrupt=False,
)

auth_app = App(name="auth", help="authentication")
spv_app = App(name="spv", help="SPV mailbox session (certificate mTLS)")
declaratii_app = App(
    name="declaratii",
    help="tax-declaration validation, rendering, signing, and filing status",
)
app.command(auth_app)
app.command(spv_app)
app.command(declaratii_app)

# Shared option shapes, mirrored across commands the way argparse's helper
# functions used to. The env-var fallback lives on the Parameter, read at parse
# time, so wrappers and tests can set the environment after module import.
_StoreOption = Annotated[
    str, Parameter(env_var="ANAFPY_TOKEN_STORE", help="token store path (file backend)")
]
_StoreBackendOption = Annotated[
    str,
    Parameter(
        env_var="ANAFPY_TOKEN_STORE_BACKEND",
        help="where tokens live: the OS credential store (macOS Keychain / "
        "Windows Credential Manager; the default), or a JSON file at --store "
        "(for Docker/headless hosts)",
    ),
]
_SessionOption = Annotated[
    str, Parameter(env_var="ANAFPY_SPV_SESSION", help="SPV session store path")
]
_IdentityFileOption = Annotated[
    str,
    Parameter(
        env_var="ANAFPY_SPV_IDENTITY_FILE", help="persisted certificate selection"
    ),
]
_DukDirOption = Annotated[
    str | None,
    Parameter(
        env_var="ANAFPY_DUK_DIR", help="the extracted DUKIntegrator dist/ folder"
    ),
]
_JavaOption = Annotated[
    str | None,
    Parameter(
        env_var="ANAFPY_DUK_JAVA", help="the java binary to run DUKIntegrator with"
    ),
]


def _load_ssl_context(cert: str, key: str | None) -> ssl.SSLContext:
    """A TLS server context for the callback listener from user-supplied PEM files."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # Pin the floor rather than inherit it: PROTOCOL_TLS_SERVER's default minimum
    # comes from the OpenSSL build's security level, which can still permit TLS 1.0/1.1.
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        context.load_cert_chain(cert, key)
    except (OSError, ssl.SSLError) as exc:
        raise AnafConfigError(f"cannot load TLS certificate {cert!r}: {exc}") from exc
    return context


def _paste_code(expected_state: str | None = None) -> str:
    print(f"\n{_PASTE_HINT}")
    return parse_redirect_url(
        input("Redirect URL (or code): "), expected_state=expected_state
    )


def _token_store(store: str, store_backend: str) -> tuple[TokenStore, str]:
    """The store selected by ``--store-backend``, plus a human label for messages.

    Validated here rather than by a ``Literal`` type: a bad value must travel
    the ``AnafConfigError`` path (``error: ...`` + exit 1) whether it came from
    the flag or from ``ANAFPY_TOKEN_STORE_BACKEND``, not exit via a parse error.
    """
    if store_backend == "keyring":
        backend = KeyringTokenStore()
        return backend, f"the OS credential store (service {backend.service!r})"
    if store_backend != "file":
        raise AnafConfigError(
            f"unknown token store backend {store_backend!r} — use 'file' or 'keyring'"
        )
    path = Path(store).expanduser()
    return FileTokenStore(path), str(path)


async def _do_login(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    store: TokenStore,
    store_label: str,
    *,
    paste: bool = False,
    ssl_context: ssl.SSLContext | None = None,
) -> int:
    # A per-attempt OAuth `state`: the redirect must echo it back, so a forged
    # redirect cannot inject someone else's authorization code (login CSRF).
    state = secrets.token_urlsafe(16)
    url = build_authorize_url(client_id, redirect_uri, state=state)

    # Bind the listener BEFORE the browser opens: with a cached certificate/session
    # the redirect can arrive within a second, and a not-yet-listening port would
    # drop the code (ANAF's codes expire in ~60s).
    listener: CallbackListener | None = None
    if not paste:
        try:
            listener = CallbackListener(
                redirect_uri, ssl_context=ssl_context, expected_state=state
            )
        except AnafConfigError as exc:
            print(f"Callback listener unavailable: {exc}", file=sys.stderr)

    print("Opening your browser for ANAF authorization (select your certificate)...")
    print(f"  If it doesn't open, visit:\n  {url}\n")
    webbrowser.open(url)

    if listener is None:
        code = _paste_code(state)
    else:
        with listener:
            print(f"Waiting for the callback on {redirect_uri} ...")
            captured = listener.wait(_CALLBACK_TIMEOUT)
        if captured is None:
            print(
                f"No callback received within {_CALLBACK_TIMEOUT:.0f}s.",
                file=sys.stderr,
            )
            code = _paste_code(state)
        else:
            code = captured

    async with httpx.AsyncClient(timeout=30.0) as http:
        tokens = await exchange_code(
            http,
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )

    store.save(tokens)
    print(f"\n✓ Authenticated. Tokens saved to {store_label}.")
    days = (tokens.access_expires_at - time.time()) / 86400
    print(f"  Access token valid ~{days:.0f} days; refresh is headless thereafter.")
    return 0


@auth_app.command(name="login")
async def auth_login(
    *,
    redirect_uri: str,
    client_id: Annotated[str | None, Parameter(env_var="ANAFPY_CLIENT_ID")] = None,
    client_secret: Annotated[
        str | None, Parameter(env_var="ANAFPY_CLIENT_SECRET")
    ] = None,
    paste: bool = False,
    tls_cert: str | None = None,
    tls_key: str | None = None,
    store: _StoreOption = DEFAULT_STORE,
    store_backend: _StoreBackendOption = "keyring",
) -> int:
    """Interactive OAuth bootstrap (browser + certificate).

    Args:
        redirect_uri: Must match the registered Callback URL (ANAF requires
            ``https://``).
        client_id: OAuth application id from ANAF's portal.
        client_secret: OAuth application secret from ANAF's portal.
        paste: Run no listener; paste the redirect URL from the browser instead.
        tls_cert: PEM certificate: serve the callback listener over TLS directly.
        tls_key: PEM private key for ``--tls-cert`` (omit if the key is in the
            cert file).
    """
    if not client_id or not client_secret:
        print(
            "error: client id/secret required "
            "(--client-id/--client-secret or ANAFPY_CLIENT_ID/ANAFPY_CLIENT_SECRET)",
            file=sys.stderr,
        )
        return 2
    if paste and tls_cert:
        print("error: --paste and --tls-cert are mutually exclusive", file=sys.stderr)
        return 2
    if tls_key and not tls_cert:
        print("error: --tls-key requires --tls-cert", file=sys.stderr)
        return 2
    ssl_context = _load_ssl_context(tls_cert, tls_key) if tls_cert else None
    # Build the store before the browser flow so a missing keyring package or
    # backend fails fast, not after the user has authorized with the certificate.
    token_store, store_label = _token_store(store, store_backend)
    return await _do_login(
        client_id,
        client_secret,
        redirect_uri,
        token_store,
        store_label,
        paste=paste,
        ssl_context=ssl_context,
    )


@auth_app.command(name="status")
def auth_status(
    *,
    store: _StoreOption = DEFAULT_STORE,
    store_backend: _StoreBackendOption = "keyring",
) -> int:
    """Show stored token validity."""
    token_store, _ = _token_store(store, store_backend)
    tokens = token_store.load()
    if tokens is None:
        print("not authenticated — run `anafpy auth login`")
        return 1
    now = time.time()
    acc = (tokens.access_expires_at - now) / 86400
    ref = (tokens.refresh_expires_at - now) / 86400
    acc_str = "expired" if tokens.access_expired() else f"~{acc:.0f} days left"
    print("authenticated")
    print(f"  access token : {acc_str}")
    print(f"  refresh token: ~{ref:.0f} days left")
    return 0


@auth_app.command(name="logout")
def auth_logout(
    *,
    store: _StoreOption = DEFAULT_STORE,
    store_backend: _StoreBackendOption = "keyring",
) -> int:
    """Remove the stored tokens (ends this machine's access)."""
    # Purely local: ANAF's documented /revoke is not reachable headlessly (it
    # answers with the certificate login wall — live-probed 2026-07-05), so
    # deleting the refresh token from this machine IS the logout; server-side the
    # tokens end by expiry or the portal's "Renunțare Oauth".
    token_store, store_label = _token_store(store, store_backend)
    try:
        tokens = token_store.load()
    except AnafConfigError:
        # An unreadable store is exactly what logout should get rid of.
        print("warning: token store unreadable — removing it anyway", file=sys.stderr)
    else:
        if tokens is None:
            print("not authenticated — nothing to remove")
            return 0
    token_store.clear()
    print(f"✓ Logged out. Tokens removed from {store_label}.")
    return 0


# --- spv --------------------------------------------------------------------------


def _print_spv_identity(listing: MessageList) -> None:
    if listing.note is not None:
        # ANAF's no-results shape carries no identity fields at all.
        print(f"  ({listing.note} — ANAF omits the certificate identity fields")
        print("   on empty windows; the session itself is active)")
        return
    print(f"  certificate holder (CNP): {listing.cnp}")
    print(f"  certificate serial      : {listing.certificate_serial}")
    print(f"  authorized CUIs/CNPs    : {', '.join(listing.authorized_cuis)}")


@spv_app.command(name="certs")
def spv_certs(
    *,
    session: _SessionOption = DEFAULT_SESSION_PATH,
    identity_file: _IdentityFileOption = DEFAULT_IDENTITY_PATH,
) -> int:
    """List usable certificates."""
    identities = discover_identities()
    if not identities:
        print("no usable TLS-client identities found — is the token plugged in?")
        return 1
    selected = load_selected_identity(identity_file)
    for identity in identities:
        marker = (
            " (selected)"
            if selected is not None
            and identity.sha1_thumbprint == selected.sha1_thumbprint
            else ""
        )
        print(f"{identity.sha1_thumbprint}  {identity.name}{marker}")
        if identity.issuer:
            print(f"{'':42}issuer: {identity.issuer}")
    print("\nselect one: anafpy spv select <thumbprint>")
    return 0


@spv_app.command(name="select")
def spv_select(
    thumbprint: str,
    *,
    session: _SessionOption = DEFAULT_SESSION_PATH,
    identity_file: _IdentityFileOption = DEFAULT_IDENTITY_PATH,
) -> int:
    """Persist which certificate to use.

    Args:
        thumbprint: SHA-1 thumbprint from ``anafpy spv certs``.
    """
    identity = identity_by_thumbprint(thumbprint)
    save_selected_identity(identity, identity_file)
    print(f"✓ Selected {identity.name!r} ({identity.sha1_thumbprint}).")
    print("  Establish a session with `anafpy spv login`.")
    return 0


def _resolve_spv_identity(
    identity: str | None, thumbprint: str | None, identity_file: str
) -> str:
    """The ``--cert`` selector for the bootstrap, from args/selection/discovery."""
    if identity:
        return identity
    if thumbprint:
        return identity_by_thumbprint(thumbprint).bootstrap_identity
    if (selected := load_selected_identity(identity_file)) is not None:
        return selected.bootstrap_identity
    identities = discover_identities()
    if len(identities) == 1:
        return identities[0].bootstrap_identity
    raise AnafConfigError(
        f"{len(identities)} identities found and none selected — run "
        "`anafpy spv certs` and `anafpy spv select <thumbprint>` first"
    )


@spv_app.command(name="login")
async def spv_login(
    *,
    identity: str | None = None,
    thumbprint: Annotated[
        str | None, Parameter(help="pick the certificate by SHA-1 thumbprint")
    ] = None,
    timeout: float = 240.0,
    session: _SessionOption = DEFAULT_SESSION_PATH,
    identity_file: _IdentityFileOption = DEFAULT_IDENTITY_PATH,
) -> int:
    """Establish the SPV cookie session (interactive: certificate + 2FA).

    Args:
        identity: Certificate selector passed to curl verbatim (macOS Keychain
            name / Windows thumbprint); overrides the persisted selection.
        timeout: Seconds to wait for the handshake incl. the 2FA.
    """
    resolved = _resolve_spv_identity(identity, thumbprint, identity_file)
    print(f"Establishing SPV session with identity {resolved!r}...", flush=True)
    print("Answer the certificate PIN / 2FA prompt when it appears.", flush=True)
    provider = SpvSessionProvider(
        store=FileSessionStore(session),
        bootstrapper=CurlBootstrapper(resolved, timeout=timeout),
    )
    async with SpvClient(provider) as spv:
        await spv.login()
        # 60-day window: the identity fields (CNP/serial/authorized CUIs)
        # only ride responses that contain messages. Best-effort: the login
        # already succeeded and the session is saved — a probe hiccup must
        # not report it as failed (observed live 2026-07-13: the probe
        # raised right after a good login).
        outcome: MessageList | AnafError
        try:
            outcome = await spv.list_messages(60)
        except AnafError as exc:
            outcome = exc
    print(f"\n✓ SPV session established; saved to {session}.")
    if isinstance(outcome, AnafError):
        print(f"(identity probe failed: {outcome} — `anafpy spv status` re-checks)")
    else:
        _print_spv_identity(outcome)
    return 0


@spv_app.command(name="status")
async def spv_status(
    *,
    session: _SessionOption = DEFAULT_SESSION_PATH,
    identity_file: _IdentityFileOption = DEFAULT_IDENTITY_PATH,
) -> int:
    """Check the stored SPV session."""
    provider = SpvSessionProvider(store=FileSessionStore(session))
    try:
        async with SpvClient(provider) as spv:
            listing = await spv.list_messages(60)
    except AnafAuthError as exc:
        print(f"no usable SPV session ({exc})")
        print("run `anafpy spv login`")
        return 1
    print("SPV session active")
    _print_spv_identity(listing)
    return 0


@spv_app.command(name="logout")
def spv_logout(
    *,
    session: _SessionOption = DEFAULT_SESSION_PATH,
    identity_file: _IdentityFileOption = DEFAULT_IDENTITY_PATH,
) -> int:
    """Remove the stored SPV session."""
    # Purely local, like `auth logout`: the APM session server-side ends by its
    # own idle timeout; removing the cookies ends this machine's access.
    FileSessionStore(session).clear()
    print(f"✓ SPV session removed from {session}.")
    return 0


# --- declaratii -------------------------------------------------------------------


def _duk(duk_dir: str | None, java: str | None) -> DukIntegrator:
    """Build the DUKIntegrator wrapper from ``--duk-dir`` / ``ANAFPY_DUK_DIR``."""
    from ..declaratii import DukIntegrator

    if not duk_dir:
        raise AnafConfigError(
            "no DUKIntegrator directory — pass --duk-dir or set ANAFPY_DUK_DIR to "
            "the extracted dist/ folder"
        )
    return DukIntegrator(Path(duk_dir).expanduser(), java=java)


def _print_findings(findings: list[DukFinding]) -> None:
    for finding in findings:
        print(f"{finding.severity.upper()}: {finding.message}")


def _read_bytes(path: Path, what: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise AnafConfigError(f"cannot read {what} {str(path)!r}: {exc}") from exc


def _write_bytes(path: Path, data: bytes, what: str) -> None:
    # Overwrite-by-default is fine at a terminal (a human is watching), but a
    # replacement must never be silent (mirrors the MCP layer's stricter guard).
    replaced = path.exists()
    try:
        path.write_bytes(data)
    except OSError as exc:
        raise AnafConfigError(f"cannot write {what} {str(path)!r}: {exc}") from exc
    if replaced:
        print(f"replaced existing {path}")


@declaratii_app.command(name="validate")
async def declaratii_validate(
    form: str,
    xml: Path,
    *,
    duk_dir: _DukDirOption = None,
    java: _JavaOption = None,
    option: Annotated[int, Parameter(help="DUKIntegrator valOption")] = 0,
) -> int:
    """Validate a declaration with DUKIntegrator.

    Args:
        form: Form name, e.g. D300.
        xml: Path to the declaration XML.
    """
    duk = _duk(duk_dir, java)
    xml_bytes = _read_bytes(xml.expanduser(), "declaration XML")
    result = await duk.validate(form, xml_bytes, option=option)
    if result.ok:
        # A warning-only run passes, but DUK's notices are the user's to see
        # (mirrors the MCP declaratie_validate `warnings` field).
        _print_findings(result.warnings)
        print(f"✓ {form} is valid.")
        return 0
    _print_findings(result.findings)
    return 1


@declaratii_app.command(name="render")
async def declaratii_render(
    form: str,
    xml: Path,
    *,
    output: Annotated[
        Path,
        Parameter(
            name=["--output", "-o"],
            help="output PDF path (an existing file is overwritten, with a notice)",
        ),
    ],
    duk_dir: _DukDirOption = None,
    java: _JavaOption = None,
    option: Annotated[int, Parameter(help="DUKIntegrator valOption")] = 0,
) -> int:
    """Render the official PDF (validates first).

    Args:
        form: Form name, e.g. D300.
        xml: Path to the declaration XML.
    """
    duk = _duk(duk_dir, java)
    xml_bytes = _read_bytes(xml.expanduser(), "declaration XML")
    out = output.expanduser()
    replacing = out.exists()  # DUK itself writes the PDF — note a replacement.
    result = await duk.render(form, xml_bytes, out, option=option)
    if not result.ok:
        print("validation failed; no PDF written:", file=sys.stderr)
        _print_findings(result.findings)
        return 1
    _print_findings(result.warnings)
    if replacing:
        print(f"replaced existing {out}")
    print(f"✓ Rendered {form} -> {out}")
    return 0


@declaratii_app.command(name="status")
async def declaratii_status(
    index: str,
    cui: str,
    *,
    ghiseu: bool = False,
) -> int:
    """Check a filed declaration's processing status (public, no login).

    Args:
        index: Upload index from the portal (= the recipisa number).
        cui: The taxpayer's fiscal code.
        ghiseu: The document was filed at an ANAF counter; INDEX is the
            registration number.
    """
    from ..declaratii import DeclarationStatusClient

    async with DeclarationStatusClient() as client:
        result = await client.check_status(index, cui, filed_at_counter=ghiseu)
    if not result.found:
        print(f"No declaration found for index {index} / CUI {cui}.")
        print(f"({result.message})")
        return 1
    print(
        f"Documents filed by CUI {result.cui} "
        f"({result.period_start} → {result.period_end}):"
    )
    queried = index.strip()
    for document in result.documents:
        # With --ghiseu the query key is the counter registration number, which
        # lives in the registration column — the internet upload index in
        # document.index can never match it.
        matches_query = (
            queried in document.registration if ghiseu else document.index == queried
        )
        marker = " ←" if matches_query else ""
        receipt = "recipisa available" if document.receipt_available else "no recipisa"
        # Print ANAF's preserved wording, including future unclassified states.
        print(
            f"  {document.index}  {document.form:<8} {document.state_text:<40} "
            f"{document.upload_date}  {receipt}{marker}"
        )
    return 0


@declaratii_app.command(name="recipisa")
async def declaratii_recipisa(
    index: str,
    *,
    output: Annotated[
        Path,
        Parameter(
            name=["--output", "-o"],
            help="output PDF path (an existing file is overwritten, with a notice)",
        ),
    ],
) -> int:
    """Download the signed filing receipt PDF (public, no login).

    Args:
        index: Upload index from the portal.
    """
    from ..declaratii import DeclarationStatusClient

    async with DeclarationStatusClient() as client:
        pdf = await client.download_receipt(index)
    if pdf is None:
        print(
            f"No recipisa available for index {index} — it is unknown, or its "
            "~60-day availability window has lapsed.",
            file=sys.stderr,
        )
        return 1
    out = output.expanduser()
    _write_bytes(out, pdf, "recipisa PDF")
    print(f"✓ Recipisa {index} -> {out}")
    return 0


@declaratii_app.command(name="sign")
async def declaratii_sign(
    pdf: Path,
    *,
    output: Annotated[
        Path | None,
        Parameter(
            name=["--output", "-o"],
            help="signed PDF path (default: <name>-semnat.pdf); an existing file "
            "is overwritten, with a notice",
        ),
    ] = None,
    identity: str | None = None,
    identity_file: _IdentityFileOption = DEFAULT_IDENTITY_PATH,
) -> int:
    """Sign a rendered PDF with the qualified certificate (macOS).

    Args:
        pdf: Path to the rendered PDF to sign.
        identity: Keychain identity name to sign with; overrides
            ANAFPY_SIGN_IDENTITY and the persisted SPV certificate selection.
    """
    from ..declaratii.signing import (
        KeychainRawSigner,
        default_signed_path,
        load_pdfsign,
        resolve_signing_label,
    )

    pdfsign = load_pdfsign()
    label = resolve_signing_label(identity, identity_path=identity_file)
    source = pdf.expanduser()
    out = output.expanduser() if output else default_signed_path(source)
    # Read the source and check the destination BEFORE the PIN/2FA prompt: a
    # bad path must not fire (or worse, discard the result of) an approval.
    pdf_bytes = _read_bytes(source, "PDF")
    if not out.parent.is_dir():
        raise AnafConfigError(f"output directory {str(out.parent)!r} does not exist")
    print(f"Signing with identity {label!r}.")
    print("Answer the certificate PIN / 2FA prompt when it appears.", flush=True)
    signer = KeychainRawSigner(label)
    result = await pdfsign.sign_pdf(pdf_bytes, signer)
    _write_bytes(out, result.pdf, "signed PDF")
    print(f"\n✓ Signed -> {out}")
    if not result.chain_complete and result.warning:
        print(f"  note: {result.warning}")
    print("  File it at anaf.ro → Depunere declarații → Transmitere declarații.")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        result = app(argv)
    except AnafError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    # --help/--version take the None branch; commands always return their code.
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
