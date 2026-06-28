"""``anafpy`` CLI — host-side OAuth bootstrap and token inspection.

The interactive ``auth login`` runs where your certificate is (browser + USB token).
After that, tokens refresh headlessly, so this is needed only ~once a year.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import webbrowser
from pathlib import Path

import httpx

from .. import __version__
from ..auth import (
    FileTokenStore,
    build_authorize_url,
    capture_authorization_code,
    exchange_code,
)
from ..exceptions import AnafError

DEFAULT_STORE = Path(os.environ.get("ANAFPY_TOKEN_STORE", "~/.anafpy/tokens.json"))


def _env(name: str) -> str | None:
    return os.environ.get(name)


async def _do_login(
    client_id: str, client_secret: str, redirect_uri: str, store_path: Path
) -> int:
    url = build_authorize_url(client_id, redirect_uri)
    print("Opening your browser for ANAF authorization (select your certificate)...")
    print(f"  If it doesn't open, visit:\n  {url}\n")
    webbrowser.open(url)

    print(f"Waiting for the callback on {redirect_uri} ...")
    code = capture_authorization_code(redirect_uri)

    async with httpx.AsyncClient(timeout=30.0) as http:
        tokens = await exchange_code(
            http,
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )

    FileTokenStore(store_path).save(tokens)
    print(f"\n✓ Authenticated. Tokens saved to {store_path}.")
    if tokens.access_expires_at:
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
    return asyncio.run(
        _do_login(
            client_id, client_secret, args.redirect_uri, Path(args.store).expanduser()
        )
    )


def _cmd_status(args: argparse.Namespace) -> int:
    tokens = FileTokenStore(Path(args.store).expanduser()).load()
    if tokens is None:
        print("not authenticated — run `anafpy auth login`")
        return 1
    now = time.time()
    acc = (tokens.access_expires_at - now) / 86400 if tokens.access_expires_at else None
    ref = (
        (tokens.refresh_expires_at - now) / 86400 if tokens.refresh_expires_at else None
    )
    acc_str = "expired" if tokens.access_expired() else f"~{acc:.0f} days left"
    print("authenticated")
    print(f"  access token : {acc_str}")
    if ref is not None:
        print(f"  refresh token: ~{ref:.0f} days left")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anafpy", description="ANAF e-Factura / e-Transport client"
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
        "--redirect-uri", required=True, help="must match the registered Callback URL"
    )
    login.add_argument("--store", default=str(DEFAULT_STORE))
    login.set_defaults(func=_cmd_login)

    status = auth.add_parser("status", help="show stored token validity")
    status.add_argument("--store", default=str(DEFAULT_STORE))
    status.set_defaults(func=_cmd_status)

    return parser


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
