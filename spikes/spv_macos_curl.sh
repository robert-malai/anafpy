#!/bin/sh
# M0 spike (macOS, WORKING PATH): SPV listaMesaje via system curl + SecureTransport.
#
# THROWAWAY CODE — not part of the library. This is the approach that succeeded
# where NSURLSession hung (Apple's Network framework stalls on the F5 APM
# mid-connection TLS renegotiation; SecureTransport-backed curl handles it).
#
# Verified live 2026-07-12: the auth is an F5 BIG-IP APM cookie session —
#   GET api URL            -> 302 /my.policy + MRHSession cookie
#   GET /my.policy         -> TLS renegotiation, CLIENT CERT signs here (2FA fires)
#   GET /my.policy_nonce   -> authenticated MRHSession
#   -> 302 back to the api URL -> 200 JSON
# Subsequent requests need ONLY the cookie jar (no certificate, no PIN/2FA).
#
# Usage:
#   ./spikes/spv_macos_curl.sh ["<keychain identity name>"] [zile]
# Identity name = the certificate's name in Keychain (subject CN), e.g. from
#   uv run spikes/spv_macos_keychain.py --list

set -eu

IDENTITY="${1:-MIHAI-ROBERT MALAI}"
ZILE="${2:-5}"
JAR="${TMPDIR:-/tmp}/spv_spike_cookies.txt"
URL="https://webserviced.anaf.ro/SPVWS2/rest/listaMesaje?zile=${ZILE}"

echo "== request 1: cert-authenticated bootstrap (2FA may fire NOW) ==" >&2
rm -f "$JAR"
CURL_SSL_BACKEND=secure-transport /usr/bin/curl -s -L --max-time 240 \
    --cert "$IDENTITY" -c "$JAR" -b "$JAR" "$URL"
echo >&2

echo "== request 2: cookie jar only, NO certificate ==" >&2
/usr/bin/curl -s -L --max-time 60 -c "$JAR" -b "$JAR" "$URL"
echo >&2
