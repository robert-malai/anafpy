"""Authorization-code capture for the one-time ``auth login`` bootstrap.

ANAF redirects the browser (after the certificate step) to the registered callback URL
with ``?code=...``. The ANAF developer portal **rejects ``http://`` callback URLs**
(HTTP 400 at registration — verified 2026-07-02), so the registered URL is ``https://``
and there are two ways to capture the code:

- **Listener** (:class:`CallbackListener` / ``capture_authorization_code``): a tiny
  local server on the callback URL's host/port. Plain HTTP by default (put a TLS
  terminator in front), or pass an ``ssl.SSLContext`` to serve TLS directly with a
  certificate you supply. The listener **binds on construction** so the browser can be
  opened only once the port is actually listening — a fast redirect (cached
  certificate/session) must never outrun the bind.
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

__all__ = ["CallbackListener", "capture_authorization_code", "parse_redirect_url"]

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


class CallbackListener:
    """A bound-and-listening receiver for the OAuth redirect.

    Binding happens in the constructor (raising :class:`AnafConfigError` when the
    host/port cannot be bound), so callers can open the browser only *after* the
    listener is provably up, then :meth:`wait` for the redirect. Use as a context
    manager (or call :meth:`close`) to stop the server.
    """

    def __init__(
        self, redirect_uri: str, *, ssl_context: ssl.SSLContext | None = None
    ) -> None:
        parsed = urllib.parse.urlparse(redirect_uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        expected_path = parsed.path or "/"

        result: dict[str, str] = {}
        done = threading.Event()
        self._result = result
        self._done = done

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                pass  # silence default request logging

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
            self._server = ThreadingHTTPServer((host, port), Handler)
            if ssl_context is not None:
                self._server.socket = ssl_context.wrap_socket(
                    self._server.socket, server_side=True
                )
        except OSError as exc:
            raise AnafConfigError(
                f"cannot bind callback listener on {host}:{port}: {exc}"
            ) from exc
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def __enter__(self) -> CallbackListener:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def wait(self, timeout: float = 180.0) -> str | None:
        """Block until the redirect arrives; the code, or ``None`` on timeout.

        Raises ``AnafAuthError`` on an OAuth error redirect.
        """
        if not self._done.wait(timeout):
            return None
        if "error" in self._result:
            raise AnafAuthError(f"authorization failed: {self._result['error']}")
        return self._result["code"]

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def capture_authorization_code(
    redirect_uri: str,
    *,
    timeout: float = 180.0,
    ssl_context: ssl.SSLContext | None = None,
) -> str:
    """Block until ANAF redirects to ``redirect_uri`` with a code; return that code.

    Bind-and-wait in one call, for callers that already opened the browser (prefer
    :class:`CallbackListener` to bind *before* opening it). Plain HTTP unless
    ``ssl_context`` is given, in which case it serves TLS with that context (use
    this when the browser must reach the callback over ``https://`` and no
    external TLS terminator is in front).

    Raises ``AnafAuthError`` on an OAuth error redirect or on timeout.
    """
    with CallbackListener(redirect_uri, ssl_context=ssl_context) as listener:
        code = listener.wait(timeout)
    if code is None:
        raise AnafAuthError(
            f"timed out waiting for the OAuth callback ({timeout:.0f}s)"
        )
    return code
