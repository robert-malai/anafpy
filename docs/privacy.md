# Privacy policy

*Last updated: 2026-08-03.*

This policy covers **anafpy** — the Python library, its command-line tools, and
the local MCP server (including the Claude Desktop extension built from it).
anafpy is free, open-source software that runs entirely on your own computer;
this page explains what that means for your data.

## The short version

anafpy collects **nothing**. There is no telemetry, no analytics, no account,
and no server operated by the author. Your data moves between **your computer
and ANAF** (Romania's tax authority) — nowhere else — and everything anafpy
stores, it stores on your own machine.

## What anafpy collects

Nothing. The author receives no data from your use of anafpy: no usage
statistics, no crash reports, no document contents, no identifiers.

## Where your data goes

anafpy talks only to services you ask it to talk to:

- **ANAF's services** (`api.anaf.ro`, `webservicesp.anaf.ro`, `www.anaf.ro`,
  and ANAF's SPV / declaration-portal and `static.anaf.ro` hosts) — the
  documents you file, the lookups you run, the mailbox you read, and the
  DUKIntegrator validator downloads. ANAF processes that data as the tax
  authority; its handling is governed by ANAF's own terms, not this policy.
- **PyPI** (`pypi.org`) — when you install or update anafpy, like any Python
  package.

No other destination exists in the code, and no request carries anything
beyond what the operation you invoked requires.

## If you use anafpy through an AI assistant

When the MCP server is connected to Claude or another AI client, whatever a
tool **returns** — invoice listings, statuses, document previews, lookup
results — becomes part of your conversation and is processed by that AI
provider under **its** terms and privacy policy. That data flow belongs to
your AI client, not to anafpy; review your provider's policy if it matters
for your practice. Two design choices limit it:

- Binary artifacts (PDFs, signed ZIPs) are written to your local disk, never
  returned into the conversation.
- Your certificate PIN is never asked for or accepted by any tool — PIN and
  2FA prompts happen in your operating system's own dialogs.

## What is stored on your computer

- **OAuth tokens** — in the operating system's credential store (macOS
  Keychain, Windows Credential Manager, Linux Secret Service) by default, or
  in `~/.anafpy/tokens.json` if you opt into the file backend.
- **Your ANAF Client ID and Secret** — where you configured them: the MCP
  client's configuration file, or the Claude Desktop extension's settings
  (which keeps the secret in the credential store).
- **The SPV session cookie** — a file readable only by your user account,
  valid for under an hour of idle time.
- **Documents you download or produce** — invoices, receipts, rendered PDFs —
  at the paths you chose.
- **ANAF's DUKIntegrator validator** — under `~/.anafpy/duk-dist`, downloaded
  from ANAF's official update feed.

Your qualified certificate's private key is never read, copied, or exported —
signing and certificate logins are delegated to the operating system and the
token's own middleware.

## Retention and deletion

The author retains nothing, because nothing is collected. Everything listed
above stays on your machine until you remove it: `anafpy auth logout` deletes
the stored tokens, deleting the files above removes the rest, and uninstalling
anafpy leaves no other trace. What ANAF retains on its side (filed documents,
SPV messages) follows ANAF's own rules.

## Third-party sharing

None. anafpy shares data with no third party — ANAF is the *intended
recipient* of what you explicitly file or query, and your AI provider sees
what its conversation carries (see above). There are no advertisers, brokers,
or analytics services involved.

## Changes to this policy

Changes are published on this page, with the date above updated; the history
is public in the [project repository](https://github.com/robert-malai/anafpy).

## Contact

Questions about privacy — or anything else — are welcome on the
[GitHub issue tracker](https://github.com/robert-malai/anafpy/issues), or by
email to the maintainer at `robert.malai@gmail.com`.
