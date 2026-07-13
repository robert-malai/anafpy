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
- `AnafConfigError` — configuration problems (missing credentials, bad env).

## Typed values: business outcomes

Outcomes of the *filing itself* are returned, never raised:

- an upload rejection (e-Factura `nok`, BR-RO findings) is
  `UploadResult.accepted is False` with the findings attached;
- a rejected message's processing state is `MessageStatus.state`;
- a validation verdict is a `RemoteValidationResult`.

The rationale: a rejection is a *successful* API call telling you something about
your document. Code that catches exceptions to handle rejections conflates "ANAF
said no" with "the network is down".

## The 200-with-error-note split

ANAF's listing endpoints (e-Factura `list_messages` / `list_notifications`,
e-Transport `info`) overload a single response note — e-Factura's `eroare`,
e-Transport's `Errors[].errorMessage` (for `info`, also a top-level `error`
string) — for both "no results in this window" and genuine errors. anafpy
classifies the note:

- a **no-results** note yields an **empty iterator** (for `info`: an empty
  `InfoList` with the note preserved in `.error`);
- a **genuine error** raises `AnafResponseError` (with `status_code=200`).

So an empty loop body means "nothing there", and you don't have to parse
Romanian error strings yourself.

## No transport retry (one documented exception)

Every discrete method on the OAuth and public clients makes exactly one HTTP
call: one call, one result-or-raise. This is a hard rule so the non-idempotent
`upload` POST is never silently repeated. Bring your own retry policy (and make
it idempotency-aware). The built-in `upload_and_wait` loop polls on the
*business* "still processing" state only — a transport error inside it
propagates immediately.

The one deliberate exception is the [SPV client](spv.md): its reads
(`list_messages`, `download_document`) retry transient *network* failures with
backoff, because every SPV operation is an idempotent GET. Received HTTP
answers — including 429 — still surface immediately, and `request_report`
stays single-shot.
