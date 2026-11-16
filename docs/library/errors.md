# Error model

anafpy deliberately splits "something went wrong" into two channels. Knowing the
split is the difference between robust and subtly broken integration code — read
this page before shipping.

## Exceptions: transport, auth, programming errors

The `AnafError` hierarchy covers failures of the *machinery*:

- `AnafAuthError` — the OAuth layer could not produce a usable token.
- `AnafTransportError` — the request never completed (connection, timeout).
- `AnafResponseError` — ANAF answered, but not in a shape anafpy accepts.
- `AnafRateLimitError` — HTTP 429, exposing `retry_after`. The client does
  **not** auto-back-off; scheduling the retry is yours.
- `AnafWafRejectionError` — ANAF's firewall refused the request *body*; carries
  the block page's `support_id`. See below.
- `AnafDownloadExpiredError` — the message left ANAF's 60-day download window;
  carries `message_id`. **Terminal**. See below.
- `AnafConfigError` — configuration problems (missing credentials, bad env).
- `InvoiceValidationError` — raised by `render_invoice` / `upload_invoice` when
  the local rule set reports fatal findings; carries them on `.report`.

`AnafRateLimitError`, `AnafWafRejectionError` and `AnafDownloadExpiredError` all
subclass `AnafResponseError`, so code that already catches that keeps working.
`AnafResponseError` itself subclasses `AnafTransportError` — catch the response
classes first when you need to tell "never completed" from "ANAF answered".

## The firewall block page

ANAF fronts `webservicesp.anaf.ro` with a WAF that scans the invoice XML you post
to `validare`/`transformare`, and answers a `Request Rejected` HTML page **with
HTTP 200** when the document matches an attack signature. Real, ANAF-accepted
invoices do — a relative path in `xsi:schemaLocation` looks like path traversal,
a `;CP ` in a street address looks like a shell command.

anafpy never hands that page back as if it were a result: it raises
`AnafWafRejectionError` (in the shared transport, so every client is covered).
It also defuses what can be defused — `xsi:schemaLocation` is advisory and is
dropped before posting, and a `render_invoice_pdf(validate=False)` that gets
blocked is retried once on the validating path, which is not subject to the same
policy. You see a warning when that happens, and the PDF you asked for.

## The closed download window

ANAF keeps an e-Factura message downloadable for 60 days. Past that, `descarcare`
answers **HTTP 200** with `{"eroare": "Fisierul nu mai poate fi descarcat pentru
ca a trecut perioada de 60 de zile in care este disponibil", …}` instead of the
ZIP — see the [reference](../anaf-reference/efactura/api.md) §4.1.

`download` raises `AnafDownloadExpiredError` for exactly that note, with the id
on `message_id`. It means **stop**: the file is gone from the SPV, and no retry
will ever succeed. Every other non-ZIP body — an unknown id, a malformed request
— stays a plain `AnafResponseError`, which is worth retrying or fixing. The
recognizer under-matches on purpose (it reads the parsed `eroare` field and one
accent-insensitive core phrase), because a false positive would make an archiver
drop an invoice for good.

You meet this in normal operation, not just through caller error: `listaMesaje`
and `descarcare` anchor their 60 days differently, so ANAF lists messages it then
refuses to hand over. A first sync — or one catching up after a gap — with a
60-day lookback lands in that boundary band:

```python
try:
    message = await client.download(item.id)
except AnafDownloadExpiredError:
    mark_permanently_unavailable(item.id)  # never ask again
```

## Typed values: business outcomes

Outcomes of the *filing itself* are returned, never raised:

- an upload ANAF refuses at submission is `UploadResult.accepted is False`,
  with ANAF's messages in `.errors`;
- a document rejected after processing (e-Factura `nok`, BR-RO findings) is
  `MessageStatus.state is MessageState.NOK`, with `.errors` and the errors file
  behind `.download_id`;
- a validation verdict is a `RemoteValidationResult`.

The rationale: a rejection is a *successful* API call telling you something about
your document. Code that catches exceptions to handle rejections conflates "ANAF
said no" with "the network is down".

## The 200-with-error-note split

ANAF's listing endpoints (e-Factura `list_messages`; e-Transport
`list_notifications` and `info`) overload a single response note — e-Factura's `eroare`,
e-Transport's `Errors[].errorMessage` (for `info`, also a top-level `error`
string) — for both "no results in this window" and genuine errors. anafpy
classifies the note:

- a **no-results** note yields an **empty iterator** (for `info`: an empty
  `InfoList` with the note preserved in `.error`);
- a **genuine error** raises `AnafResponseError` (with `status_code=200`).

So an empty loop body means "nothing there", and you don't have to parse
Romanian error strings yourself.

## No transport retry (the documented exceptions)

Discrete methods on the OAuth and public clients do no transport retry: one
call, one result-or-raise. This is a hard rule so a failed `upload` POST is
never silently repeated. Bring your own retry policy (and make it
idempotency-aware). The built-in poll loops (`upload_and_wait`, and SPV's
`wait_for_report`) wait on the *business* "still processing" state only — a
transport error inside them propagates immediately.

The deliberate exceptions:

- **The auth layer.** A 401 triggers one token refresh and one re-send of the
  same request — ANAF refused it unprocessed, so nothing is filed twice.
- **The [SPV client](spv.md).** Its reads (`list_messages`,
  `download_document`) retry transient *network* failures with backoff, because
  every SPV operation is an idempotent GET. Received HTTP answers — including
  429 — still surface immediately, and `request_report` stays single-shot.
- **`render_invoice_pdf(validate=False)`.** A firewall block on the
  skip-validation URL is followed by one attempt at the validating URL (a
  different endpoint, on a stateless public service that files nothing) instead
  of losing the PDF.
- **e-Factura `list_messages`.** When ANAF rejects a `days` window by quoting
  its own clock, the page is re-asked once on that clock — a correction, not a
  retry (see the [e-Factura guide](efactura.md)).
