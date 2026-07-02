"""Authorization-code capture for the one-time ``auth login`` bootstrap.

ANAF redirects the browser (after the certificate step) to the registered callback URL
with ``?code=...``. The ANAF developer portal **rejects ``http://`` callback URLs**
(HTTP 400 at registration — verified 2026-07-02), so the registered URL is ``https://``
and there are two ways to capture the code:

- **Listener** (``capture_authorization_code``): a tiny local server on the callback
  URL's host/port. Plain HTTP by default (put a TLS terminator in front), or pass an
  ``ssl.SSLContext`` to serve TLS directly with a certificate you supply.
- **Paste mode** (``parse_redirect_url``): run no listener at all. The browser lands on
  a connection error, but the address bar still holds the full redirect URL; the user
  pastes it (or just the code) into the CLI. Works everywhere, needs no certificate.
"""

from __future__ import annotations

import ssl
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..exceptions import AnafAuthError, AnafConfigError

__all__ = ["capture_authorization_code", "parse_redirect_url"]

_PAGE = (
    b"<!doctype html><meta charset=utf-8><title>anafpy</title>"
    b"<body style='font-family:sans-serif;padding:2rem'>"
    b"<h2>%s</h2><p>You can close this tab and return to the terminal.</p>"
)


def parse_redirect_url(pasted: str) -> str:
    """Extract the authorization code from a pasted redirect URL (paste mode).

    Accepts the full redirect URL from the browser address bar, a bare
    ``code=...&...`` query string, or the code value alone.

    Raises ``AnafAuthError`` on an OAuth error redirect or unrecognizable input.
    """
    text = pasted.strip().strip("'\"")
    if not text:
        raise AnafAuthError("empty input: paste the full redirect URL from the browser")

    query = urllib.parse.urlparse(text).query
    if not query and "=" in text:
        query = text.lstrip("?")
    if query:
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            return params["code"][0]
        if "error" in params:
            raise AnafAuthError(f"authorization failed: {params['error'][0]}")
        raise AnafAuthError("no `code` parameter in the pasted URL")

    if "/" in text or " " in text:
        raise AnafAuthError("no `code` parameter in the pasted URL")
    return text  # the bare code value


def capture_authorization_code(
    redirect_uri: str,
    *,
    timeout: float = 180.0,
    ssl_context: ssl.SSLContext | None = None,
) -> str:
    """Block until ANAF redirects to ``redirect_uri`` with a code; return that code.

    The listener binds the URI's host/port. It speaks plain HTTP unless
    ``ssl_context`` is given, in which case it serves TLS with that context (use
    this when the browser must reach the callback over ``https://`` and no
    external TLS terminator is in front).

    Raises ``AnafAuthError`` on an OAuth error redirect or on timeout.
    """
    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    expected_path = parsed.path or "/"

    result: dict[str, str] = {}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:  # silence default logging
            pass

        def do_GET(self) -> None:
            url = urllib.parse.urlparse(self.path)
            if url.path != expected_path:
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(url.query)
            if "code" in query:
                result["code"] = query["code"][0]
                msg = b"Authorization received."
            else:
                result["error"] = query.get("error", ["unknown_error"])[0]
                msg = b"Authorization failed."
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_PAGE % msg)
            done.set()

    try:
        server = ThreadingHTTPServer((host, port), Handler)
        if ssl_context is not None:
            server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    except OSError as exc:
        raise AnafConfigError(
            f"cannot bind callback listener on {host}:{port}: {exc}"
        ) from exc

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        if not done.wait(timeout):
            raise AnafAuthError(
                f"timed out waiting for the OAuth callback ({timeout:.0f}s)"
            )
    finally:
        server.shutdown()
        server.server_close()

    if "error" in result:
        raise AnafAuthError(f"authorization failed: {result['error']}")
    return result["code"]
