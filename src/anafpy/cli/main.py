"""``anafpy`` CLI — host-side OAuth bootstrap, token inspection, and SPV login.

The interactive ``auth login`` runs where your certificate is (browser + USB token).
After that, tokens refresh headlessly, so this is needed only ~once a year.

``spv login`` is SPV's equivalent interactive step: the certificate TLS handshake
plus the token PIN / cloud-HSM 2FA prompt, yielding the cookie session the SPV
client (and the MCP ``spv_*`` tools) then ride non-interactively.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import ssl
import sys
import time
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

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
    from ..declaratii import DeclarationStatusList, DukFinding, DukIntegrator

DEFAULT_STORE = "~/.anafpy/tokens.json"

#: How long the callback listener waits for the redirect before offering paste mode.
_CALLBACK_TIMEOUT = 180.0

_PASTE_HINT = (
    "After authorizing, your browser will show a connection error — that is\n"
    "expected. Copy the FULL URL from the address bar and paste it below\n"
    "(promptly: ANAF's code expires in ~60 seconds)."
)


def _env(name: str) -> str | None:
    return os.environ.get(name)


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


def _token_store(args: argparse.Namespace) -> tuple[TokenStore, str]:
    """The store selected by ``--store-backend``, plus a human label for messages.

    Validated here rather than by argparse ``choices``: the default comes from
    ``ANAFPY_TOKEN_STORE_BACKEND``, and argparse never checks defaults.
    """
    if args.store_backend == "keyring":
        store = KeyringTokenStore()
        return store, f"the OS credential store (service {store.service!r})"
    if args.store_backend != "file":
        raise AnafConfigError(
            f"unknown token store backend {args.store_backend!r} — "
            "use 'file' or 'keyring'"
        )
    path = Path(args.store).expanduser()
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


def _cmd_login(args: argparse.Namespace) -> int:
    client_id = args.client_id or _env("ANAFPY_CLIENT_ID")
    client_secret = args.client_secret or _env("ANAFPY_CLIENT_SECRET")
    if not client_id or not client_secret:
        print(
            "error: client id/secret required "
            "(--client-id/--client-secret or ANAFPY_CLIENT_ID/ANAFPY_CLIENT_SECRET)",
            file=sys.stderr,
        )
        return 2
    if args.paste and args.tls_cert:
        print("error: --paste and --tls-cert are mutually exclusive", file=sys.stderr)
        return 2
    if args.tls_key and not args.tls_cert:
        print("error: --tls-key requires --tls-cert", file=sys.stderr)
        return 2
    ssl_context = (
        _load_ssl_context(args.tls_cert, args.tls_key) if args.tls_cert else None
    )
    # Build the store before the browser flow so a missing keyring package or
    # backend fails fast, not after the user has authorized with the certificate.
    store, store_label = _token_store(args)
    return asyncio.run(
        _do_login(
            client_id,
            client_secret,
            args.redirect_uri,
            store,
            store_label,
            paste=args.paste,
            ssl_context=ssl_context,
        )
    )


def _cmd_status(args: argparse.Namespace) -> int:
    store, _ = _token_store(args)
    tokens = store.load()
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


def _cmd_logout(args: argparse.Namespace) -> int:
    # Purely local: ANAF's documented /revoke is not reachable headlessly (it
    # answers with the certificate login wall — live-probed 2026-07-05), so
    # deleting the refresh token from this machine IS the logout; server-side the
    # tokens end by expiry or the portal's "Renunțare Oauth".
    store, store_label = _token_store(args)
    try:
        tokens = store.load()
    except AnafConfigError:
        # An unreadable store is exactly what logout should get rid of.
        print("warning: token store unreadable — removing it anyway", file=sys.stderr)
    else:
        if tokens is None:
            print("not authenticated — nothing to remove")
            return 0
    store.clear()
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


def _cmd_spv_certs(args: argparse.Namespace) -> int:
    identities = discover_identities()
    if not identities:
        print("no usable TLS-client identities found — is the token plugged in?")
        return 1
    selected = load_selected_identity(args.identity_file)
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


def _cmd_spv_select(args: argparse.Namespace) -> int:
    identity = identity_by_thumbprint(args.thumbprint)
    save_selected_identity(identity, args.identity_file)
    print(f"✓ Selected {identity.name!r} ({identity.sha1_thumbprint}).")
    print("  Establish a session with `anafpy spv login`.")
    return 0


def _resolve_spv_identity(args: argparse.Namespace) -> str:
    """The ``--cert`` selector for the bootstrap, from args/selection/discovery."""
    if args.identity:
        return str(args.identity)
    if args.thumbprint:
        return identity_by_thumbprint(args.thumbprint).bootstrap_identity
    if (selected := load_selected_identity(args.identity_file)) is not None:
        return selected.bootstrap_identity
    identities = discover_identities()
    if len(identities) == 1:
        return identities[0].bootstrap_identity
    raise AnafConfigError(
        f"{len(identities)} identities found and none selected — run "
        "`anafpy spv certs` and `anafpy spv select <thumbprint>` first"
    )


def _cmd_spv_login(args: argparse.Namespace) -> int:
    identity = _resolve_spv_identity(args)

    async def run() -> MessageList | AnafError:
        provider = SpvSessionProvider(
            store=FileSessionStore(args.session),
            bootstrapper=CurlBootstrapper(identity, timeout=args.timeout),
        )
        async with SpvClient(provider) as spv:
            await spv.login()
            # 60-day window: the identity fields (CNP/serial/authorized CUIs)
            # only ride responses that contain messages. Best-effort: the login
            # already succeeded and the session is saved — a probe hiccup must
            # not report it as failed (observed live 2026-07-13: the probe
            # raised right after a good login).
            try:
                return await spv.list_messages(60)
            except AnafError as exc:
                return exc

    print(f"Establishing SPV session with identity {identity!r}...", flush=True)
    print("Answer the certificate PIN / 2FA prompt when it appears.", flush=True)
    outcome = asyncio.run(run())
    print(f"\n✓ SPV session established; saved to {args.session}.")
    if isinstance(outcome, AnafError):
        print(f"(identity probe failed: {outcome} — `anafpy spv status` re-checks)")
    else:
        _print_spv_identity(outcome)
    return 0


def _cmd_spv_status(args: argparse.Namespace) -> int:
    async def run() -> MessageList:
        provider = SpvSessionProvider(store=FileSessionStore(args.session))
        async with SpvClient(provider) as spv:
            return await spv.list_messages(60)

    try:
        listing = asyncio.run(run())
    except AnafAuthError as exc:
        print(f"no usable SPV session ({exc})")
        print("run `anafpy spv login`")
        return 1
    print("SPV session active")
    _print_spv_identity(listing)
    return 0


def _cmd_spv_logout(args: argparse.Namespace) -> int:
    # Purely local, like `auth logout`: the APM session server-side ends by its
    # own idle timeout; removing the cookies ends this machine's access.
    FileSessionStore(args.session).clear()
    print(f"✓ SPV session removed from {args.session}.")
    return 0


# --- declaratii -------------------------------------------------------------------


def _duk(args: argparse.Namespace) -> DukIntegrator:
    """Build the DUKIntegrator wrapper from ``--duk-dir`` / ``ANAFPY_DUK_DIR``."""
    from ..declaratii import DukIntegrator

    if not args.duk_dir:
        raise AnafConfigError(
            "no DUKIntegrator directory — pass --duk-dir or set ANAFPY_DUK_DIR to "
            "the extracted dist/ folder"
        )
    return DukIntegrator(Path(args.duk_dir).expanduser(), java=args.java)


def _print_findings(findings: list[DukFinding]) -> None:
    for finding in findings:
        print(f"{finding.severity.upper()}: {finding.message}")


def _cmd_decl_validate(args: argparse.Namespace) -> int:
    duk = _duk(args)
    xml = Path(args.xml).expanduser().read_bytes()
    result = asyncio.run(duk.validate(args.form, xml, option=args.option))
    if result.ok:
        print(f"✓ {args.form} is valid.")
        return 0
    _print_findings(result.findings)
    return 1


def _cmd_decl_render(args: argparse.Namespace) -> int:
    duk = _duk(args)
    xml = Path(args.xml).expanduser().read_bytes()
    out = Path(args.output).expanduser()
    result = asyncio.run(duk.render(args.form, xml, out, option=args.option))
    if not result.ok:
        print("validation failed; no PDF written:", file=sys.stderr)
        _print_findings(result.findings)
        return 1
    print(f"✓ Rendered {args.form} -> {out}")
    return 0


def _cmd_decl_status(args: argparse.Namespace) -> int:
    from ..declaratii import DeclarationStatusClient

    async def query() -> DeclarationStatusList:
        async with DeclarationStatusClient() as client:
            return await client.check_status(
                args.index, args.cui, filed_at_counter=args.ghiseu
            )

    result = asyncio.run(query())
    if not result.found:
        print(f"No declaration found for index {args.index} / CUI {args.cui}.")
        print(f"({result.message})")
        return 1
    print(
        f"Documents filed by CUI {result.cui} "
        f"({result.period_start} → {result.period_end}):"
    )
    for document in result.documents:
        marker = " ←" if document.index == str(args.index).strip() else ""
        receipt = "recipisa available" if document.receipt_available else "no recipisa"
        print(
            f"  {document.index}  {document.form:<8} {document.state.value:<18} "
            f"{document.upload_date}  {receipt}{marker}"
        )
    return 0


def _cmd_decl_recipisa(args: argparse.Namespace) -> int:
    from ..declaratii import DeclarationStatusClient

    async def download() -> bytes | None:
        async with DeclarationStatusClient() as client:
            return await client.download_receipt(args.index)

    pdf = asyncio.run(download())
    if pdf is None:
        print(
            f"No recipisa available for index {args.index} — it is unknown, or its "
            "~60-day availability window has lapsed.",
            file=sys.stderr,
        )
        return 1
    out = Path(args.output).expanduser()
    out.write_bytes(pdf)
    print(f"✓ Recipisa {args.index} -> {out}")
    return 0


def _cmd_decl_sign(args: argparse.Namespace) -> int:
    try:
        from ..declaratii import pdfsign
    except ModuleNotFoundError as exc:
        raise AnafConfigError(
            "signing needs the anafpy[declaratii] extra — "
            "install it with `pip install 'anafpy[declaratii]'`"
        ) from exc
    from ..declaratii.signing import KeychainRawSigner, resolve_signing_label

    label = resolve_signing_label(args.identity, identity_path=args.identity_file)
    source = Path(args.pdf).expanduser()
    out = (
        Path(args.output).expanduser()
        if args.output
        else source.with_name(f"{source.stem}-semnat.pdf")
    )
    print(f"Signing with identity {label!r}.")
    print("Answer the certificate PIN / 2FA prompt when it appears.", flush=True)
    signer = KeychainRawSigner(label)
    result = asyncio.run(pdfsign.sign_pdf(source.read_bytes(), signer))
    out.write_bytes(result.pdf)
    print(f"\n✓ Signed -> {out}")
    if not result.chain_complete and result.warning:
        print(f"  note: {result.warning}")
    print("  File it at anaf.ro → Depunere declarații → Transmitere declarații.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anafpy",
        description="ANAF e-Factura / e-Transport / public-services client",
    )
    parser.add_argument("--version", action="version", version=f"anafpy {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="authentication").add_subparsers(
        dest="auth_cmd", required=True
    )

    login = auth.add_parser(
        "login", help="interactive OAuth bootstrap (browser + certificate)"
    )
    login.add_argument("--client-id")
    login.add_argument("--client-secret")
    login.add_argument(
        "--redirect-uri",
        required=True,
        help="must match the registered Callback URL (ANAF requires https://)",
    )
    login.add_argument(
        "--paste",
        action="store_true",
        help="run no listener; paste the redirect URL from the browser instead",
    )
    login.add_argument(
        "--tls-cert",
        help="PEM certificate: serve the callback listener over TLS directly",
    )
    login.add_argument(
        "--tls-key",
        help="PEM private key for --tls-cert (omit if the key is in the cert file)",
    )
    _add_store_args(login)
    login.set_defaults(func=_cmd_login)

    status = auth.add_parser("status", help="show stored token validity")
    _add_store_args(status)
    status.set_defaults(func=_cmd_status)

    logout = auth.add_parser(
        "logout", help="remove the stored tokens (ends this machine's access)"
    )
    _add_store_args(logout)
    logout.set_defaults(func=_cmd_logout)

    spv = sub.add_parser(
        "spv", help="SPV mailbox session (certificate mTLS)"
    ).add_subparsers(dest="spv_cmd", required=True)

    spv_certs = spv.add_parser("certs", help="list usable certificates")
    _add_spv_args(spv_certs)
    spv_certs.set_defaults(func=_cmd_spv_certs)

    spv_select = spv.add_parser("select", help="persist which certificate to use")
    spv_select.add_argument("thumbprint", help="SHA-1 thumbprint from `spv certs`")
    _add_spv_args(spv_select)
    spv_select.set_defaults(func=_cmd_spv_select)

    spv_login = spv.add_parser(
        "login",
        help="establish the SPV cookie session (interactive: certificate + 2FA)",
    )
    spv_login.add_argument(
        "--identity",
        help="certificate selector passed to curl verbatim (macOS Keychain name / "
        "Windows thumbprint); overrides the persisted selection",
    )
    spv_login.add_argument(
        "--thumbprint", help="pick the certificate by SHA-1 thumbprint"
    )
    spv_login.add_argument(
        "--timeout",
        type=float,
        default=240.0,
        help="seconds to wait for the handshake incl. the 2FA (default 240)",
    )
    _add_spv_args(spv_login)
    spv_login.set_defaults(func=_cmd_spv_login)

    spv_status = spv.add_parser("status", help="check the stored SPV session")
    _add_spv_args(spv_status)
    spv_status.set_defaults(func=_cmd_spv_status)

    spv_logout = spv.add_parser("logout", help="remove the stored SPV session")
    _add_spv_args(spv_logout)
    spv_logout.set_defaults(func=_cmd_spv_logout)

    decl = sub.add_parser(
        "declaratii",
        help="tax-declaration validation, rendering, signing, and filing status",
    ).add_subparsers(dest="declaratii_cmd", required=True)

    decl_validate = decl.add_parser(
        "validate", help="validate a declaration with DUKIntegrator"
    )
    decl_validate.add_argument("form", help="form name, e.g. D300")
    decl_validate.add_argument("xml", help="path to the declaration XML")
    _add_duk_args(decl_validate)
    decl_validate.set_defaults(func=_cmd_decl_validate)

    decl_render = decl.add_parser(
        "render", help="render the official PDF (validates first)"
    )
    decl_render.add_argument("form", help="form name, e.g. D300")
    decl_render.add_argument("xml", help="path to the declaration XML")
    decl_render.add_argument("-o", "--output", required=True, help="output PDF path")
    _add_duk_args(decl_render)
    decl_render.set_defaults(func=_cmd_decl_render)

    decl_status = decl.add_parser(
        "status",
        help="check a filed declaration's processing status (public, no login)",
    )
    decl_status.add_argument(
        "index", help="upload index from the portal (= the recipisa number)"
    )
    decl_status.add_argument("cui", help="the taxpayer's fiscal code")
    decl_status.add_argument(
        "--ghiseu",
        action="store_true",
        help="the document was filed at an ANAF counter; INDEX is the "
        "registration number",
    )
    decl_status.set_defaults(func=_cmd_decl_status)

    decl_recipisa = decl.add_parser(
        "recipisa", help="download the signed filing receipt PDF (public, no login)"
    )
    decl_recipisa.add_argument("index", help="upload index from the portal")
    decl_recipisa.add_argument("-o", "--output", required=True, help="output PDF path")
    decl_recipisa.set_defaults(func=_cmd_decl_recipisa)

    decl_sign = decl.add_parser(
        "sign", help="sign a rendered PDF with the qualified certificate (macOS)"
    )
    decl_sign.add_argument("pdf", help="path to the rendered PDF to sign")
    decl_sign.add_argument(
        "-o", "--output", help="signed PDF path (default: <name>-semnat.pdf)"
    )
    decl_sign.add_argument(
        "--identity",
        help="Keychain identity name to sign with; overrides ANAFPY_SIGN_IDENTITY "
        "and the persisted SPV certificate selection",
    )
    decl_sign.add_argument(
        "--identity-file",
        default=os.environ.get("ANAFPY_SPV_IDENTITY_FILE", DEFAULT_IDENTITY_PATH),
        help="persisted certificate selection; default from ANAFPY_SPV_IDENTITY_FILE",
    )
    decl_sign.set_defaults(func=_cmd_decl_sign)

    return parser


def _add_duk_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--duk-dir",
        default=os.environ.get("ANAFPY_DUK_DIR"),
        help="the extracted DUKIntegrator dist/ folder; default from ANAFPY_DUK_DIR",
    )
    parser.add_argument(
        "--java",
        default=os.environ.get("ANAFPY_DUK_JAVA"),
        help="the java binary to run DUKIntegrator with; default from ANAFPY_DUK_JAVA",
    )
    parser.add_argument(
        "--option", type=int, default=0, help="DUKIntegrator valOption (default 0)"
    )


def _add_spv_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--session",
        # Read at parse time (not import) so tests and wrappers can set the env.
        default=os.environ.get("ANAFPY_SPV_SESSION", DEFAULT_SESSION_PATH),
        help="SPV session store path; default from ANAFPY_SPV_SESSION",
    )
    parser.add_argument(
        "--identity-file",
        default=os.environ.get("ANAFPY_SPV_IDENTITY_FILE", DEFAULT_IDENTITY_PATH),
        help="persisted certificate selection; default from ANAFPY_SPV_IDENTITY_FILE",
    )


def _add_store_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--store",
        # Read at parse time (not import) so tests and wrappers can set the env.
        default=os.environ.get("ANAFPY_TOKEN_STORE", DEFAULT_STORE),
    )
    parser.add_argument(
        "--store-backend",
        choices=("file", "keyring"),
        # Read at parse time (not import) so tests and wrappers can set the env.
        default=os.environ.get("ANAFPY_TOKEN_STORE_BACKEND", "keyring"),
        help="where tokens live: the OS credential store (macOS Keychain / "
        "Windows Credential Manager; the default), or a JSON file at --store "
        "(for Docker/headless hosts); default from ANAFPY_TOKEN_STORE_BACKEND",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
        return result
    except AnafError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
