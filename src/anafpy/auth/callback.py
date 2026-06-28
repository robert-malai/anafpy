"""Localhost OAuth callback listener for the one-time ``auth login`` bootstrap.

ANAF redirects the browser (after the certificate step) to the registered callback URL
with ``?code=...``. This spins up a tiny local HTTP server on that URL's host/port,
captures the code, and shuts down.

Note: if you registered an ``https://localhost`` callback, terminate TLS in front of
this listener (or register an ``http://localhost`` callback) — this server speaks HTTP.
"""

from __future__ import annotations

import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..exceptions import AnafAuthError, AnafConfigError

__all__ = ["capture_authorization_code"]

_PAGE = (
    b"<!doctype html><meta charset=utf-8><title>anafpy</title>"
    b"<body style='font-family:sans-serif;padding:2rem'>"
    b"<h2>%s</h2><p>You can close this tab and return to the terminal.</p>"
)


def capture_authorization_code(redirect_uri: str, *, timeout: float = 180.0) -> str:
    """Block until ANAF redirects to ``redirect_uri`` with a code; return that code.

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
