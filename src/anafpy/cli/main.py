"""``anafpy`` CLI — host-side OAuth bootstrap and token inspection.

The interactive ``auth login`` runs where your certificate is (browser + USB token).
After that, tokens refresh headlessly, so this is needed only ~once a year.
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
from ..exceptions import AnafConfigError, AnafError

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

    return parser


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
