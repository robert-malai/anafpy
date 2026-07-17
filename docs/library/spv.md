# SPV (Spațiul Privat Virtual)

`SpvClient` reads a taxpayer's **SPV** mailbox on `webserviced.anaf.ro` — list
inbox messages, download documents (receipts, decisions, notifications), and
request official reports (fiscal vector, outstanding obligations, filing
history, ...). It is **read-only by design**: no declaration submission, no
writes to ANAF of any kind.

SPV authenticates with the taxpayer's **qualified certificate** (USB token or
cloud HSM), not OAuth — a different world from the e-Factura/e-Transport
clients. The keys are non-exportable, so Python's TLS stack cannot present
them; anafpy drives the **OS-shipped curl** against the platform key store for
the one step that needs the certificate, and everything else is ordinary HTTP.

## The session model

ANAF fronts SPV with an F5 APM **cookie session** (see the
[SPV reference](../anaf-reference/spv/api.md) §1.1):

1. **Login (interactive, certificate + PIN/2FA).** One redirect chain performs
   the client-certificate TLS handshake. Your token middleware prompts — on
   *every* login, authorizations are not cached between runs.
2. **Everything else rides the cookies.** Listing, downloads, and report
   requests are plain HTTPS with the session cookies — no certificate, no
   prompts. Polling never wakes your token.

The session is a bearer credential, persisted like the OAuth tokens: an
owner-only (`0600`) JSON file, `~/.anafpy/spv-session.json` by default. The
layering mirrors the OAuth clients exactly — `SpvClient` takes an
`SpvSessionProvider` the way `EFacturaClient` takes a `TokenProvider`, and an
`SpvAuth` (`httpx.Auth`) flow attaches the cookies to every request. When the
session expires, the next call raises `AnafAuthError` telling you to log in
again — the client never re-runs the interactive login on its own.

## Logging in

The CLI owns the interactive step (like `anafpy auth login` does for OAuth):

```bash
anafpy spv certs                  # list usable certificates (token/cloud incl.)
anafpy spv select <thumbprint>    # persist which one to use
anafpy spv login                  # certificate handshake — answer the PIN/2FA
anafpy spv status                 # session + authorization inventory
anafpy spv logout                 # remove the stored session (local only)
```

Programmatically, the same flow is `discover_identities()` +
`SpvClient(SpvSessionProvider(store=FileSessionStore(), bootstrapper=CurlBootstrapper(...)))`
and `await spv.login()`. `CurlBootstrapper` takes the Keychain identity **name**
on macOS and the certificate's SHA-1 **thumbprint** on Windows
(`CurrentUser\MY` store). The login is occasionally flaky on ANAF's side even
with a prompt answered promptly; it fails with an actionable `AnafAuthError`
rather than hanging, and retrying (which re-fires the prompt) is safe.

**Windows on ARM caveat**: certificate vendors may ship x64-only middleware
(certSIGN Paperless vToken does, as of 2026-07), which the ARM64 System32
curl cannot load — the login then fails instantly with
`SEC_E_UNKNOWN_CREDENTIALS`, before any network traffic. Point the bootstrap
at an **x64** curl with Schannel support — Git for Windows'
`mingw64\bin\curl.exe` is a known-good one — via the `ANAFPY_CURL`
environment variable (honored by the CLI, the MCP server, and
`CurlBootstrapper` alike) or the `curl_path` argument.

## Reading the inbox

```python
from anafpy.spv import FileSessionStore, SpvClient, SpvSessionProvider

provider = SpvSessionProvider(store=FileSessionStore())
async with SpvClient(provider) as spv:
    listing = await spv.list_messages(30)
    print("certificate may query:", listing.authorized_cuis)
    for message in listing.messages:
        print(message.created_at, message.kind, message.details)
    document = await spv.download_document(listing.messages[0].id)
    assert document.is_pdf
```

`list_messages` also returns the certificate's **authorization inventory**
(`authorized_cuis` — every CUI/CNP it has SPV rights for) plus `cnp` and
`certificate_serial`. A window with no messages yields empty `messages` with
ANAF's note in `note`, not an error. Message `type_` is an open string on the
wire (ANAF emits values like `RECIPISA`, `PLATA`, even `"DECLARATIE "` with a
trailing space) — compare against `message.kind`, the trimmed form.

## Requesting reports

Reports are **asynchronous**: `cerere` files a request, ANAF generates the
report (no SLA), and it lands in the inbox as a message answering your
`request_id`.

```python
from anafpy.spv import ReportRequest, ReportType

request = ReportRequest(type_=ReportType.VECTOR_FISCAL, cui="12345678")
result = await spv.request_report(request)
document = await spv.wait_for_report(result.request_id, timeout=600)
```

`ReportRequest` encodes ANAF's **per-type parameter requirements** — a `D300`
without `year`+`month`, a `D208` with a month other than 6/12, or an
`Adeverinte Venit` whose `reason` is not in the fixed `motiv` list
(`INCOME_CERTIFICATE_REASONS`) fail at construction, before any wire call.
`wait_for_report` polls with generous, growing intervals (15 s → 120 s); on
timeout it raises `TimeoutError` and the `request_id` stays valid — call it
again later.

## Error model

The [hybrid model](errors.md) applies. SPV's Romanian `eroare` texts are
surfaced **verbatim** inside `AnafResponseError`, with a best-effort English
hint appended (missing rights, invalid CUI, missing parameters, technical
codes). Two SPV-specific notes:

- a "no messages in the window" note is a value (`MessageList.note`), never an
  exception;
- an expired APM session raises `AnafAuthError` — log in again.

Unlike the OAuth clients, the SPV **reads** (`list_messages`,
`download_document`) retry transient network failures with exponential backoff
— every SPV operation is an idempotent GET. `request_report` stays single-shot
and files a request on every call — a repeat yields a second inbox message,
nothing worse; agent-facing layers own their own dedupe.
