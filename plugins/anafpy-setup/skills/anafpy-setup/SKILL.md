---
name: anafpy-setup
description: >
  Install, configure, verify, or repair anafpy on this computer — the local MCP
  server that lets Claude talk to Romania's ANAF (e-Factura, e-Transport, SPV,
  registry lookups, and local tax-declaration authoring/signing). Use when the
  user wants to set up / install / configure
  anafpy, connect ANAF to Claude, or when the anafpy tools have stopped working
  ("Claude can't see my ANAF tools", "e-Factura tools are missing", "it says run
  anafpy auth login"). Probes what is already in place, installs only what is
  missing, and hands off to the Cowork tab. Safe to re-run at any time.
---

# Set up anafpy on this computer

You are installing a tax-filing tool on someone's computer. Assume the user is an
accountant, not a programmer: never show them a stack trace, never ask them to
edit JSON, and explain each step in one plain sentence before you run it.

The full human-readable walkthrough is
[the setup guide](https://anafpy.readthedocs.io/en/latest/mcp/setup/) — this skill
is the automated version of it. When the two disagree, the guide is right.

This skill is a **diagnostic, not a script**. Probe first, report what is already
done, then do only what is missing. A first-time install and a six-months-later
repair are the same flow.

This file is the **spine**: what each step is for, the rules, and what to tell
the user. The exact commands live in the platform files — [macos.md](macos.md)
and [windows.md](windows.md). Step 0 tells you which one applies; read it once,
in full, and take **every command from that file only**. Never run a command
block written for the other platform.

## Rules that override everything else

1. **Never ask for, accept, or echo the certificate PIN.** The USB token's PIN and
   2FA are between the user and their device. If a step needs the PIN, the *user*
   runs that command and tells you the outcome.
2. **Never overwrite a config file without backing it up first**, and never drop
   an existing `mcpServers` entry that isn't ours. Read, merge, back up, write.
3. **Verify, never assume.** After each step, run the probe that proves it worked.
   "The user said they did it" is not evidence.

## Step 0 — Preflight: are you actually on their computer?

This is not optional and it comes first. The Code tab can run sessions on
Anthropic's cloud, over SSH, or in WSL — none of which can see the user's USB
token, Keychain, or Claude Desktop config. Everything below would appear to
succeed and then be useless.

Run:

```bash
uname -s 2>/dev/null || echo "windows?"
ls -d ~/Library/Application\ Support/Claude 2>/dev/null || ls -d "$APPDATA/Claude" 2>/dev/null
```

- **macOS** (`Darwin`) + a `Claude` config directory → read [macos.md](macos.md)
  now; it supplies every command for the steps below.
- **Windows** + a `Claude` config directory → read [windows.md](windows.md) now;
  same deal, and it also carries the Windows-specific curl handling.
- **`Linux`**, or no `Claude` directory anywhere → you are almost certainly in a
  cloud/remote session. **Stop.** Tell the user: *"This session is running on
  Anthropic's servers, not on your computer, so I can't reach your certificate or
  your Claude settings from here. Start a new session in the Code tab and pick the
  **Local** environment, then run this again."* Do not proceed.

## Step 1 — Probe everything, then report

Run the platform file's **step-1 probe block** and build a picture before
touching anything. You are establishing:

- is `uv` installed, and is anafpy installed as a uv tool (the `anafpy` and
  `anafpy-mcp` binaries)?
- what does the Claude Desktop config already hold (an `anafpy` entry? other
  connectors that must be preserved)?
- is the user logged in to ANAF (`auth status`)?
- **Windows only**: the curl verdict — the platform file explains the known
  ANAF TLS bug and what to do about it.

If the config's `anafpy` entry runs `uv run --directory <folder> … anafpy-mcp`,
that is the **old clone-based install**. It still works — but since you are here
to fix or change something, migrate it: install from PyPI (step 4), rewrite the
config entry to the `anafpy-mcp` binary (step 6), and leave the old folder alone
(it may hold the user's mkcert files). The login tokens live in the system
credential store, not in that folder, so nothing is lost.

Then give the user a short checklist of what is done and what is missing — six
lines, not a wall of text. Something like:

> - ANAF application registered: **I need to ask you**
> - uv installed: **yes**
> - anafpy installed: **yes** (version 0.4.2)
> - Logged in to ANAF: **no** — token expired
> - Connected to Claude: **yes**
> - SPV mailbox: **not set up** (optional)
>
> So we only need to redo the ANAF login. That's one command and your USB token.

Then do only the missing steps.

## Step 2 — ANAF application (user-only, you cannot do this)

Registering the OAuth application happens on ANAF's portal with their certificate.
You cannot drive it. If they don't have a **Client ID** and **Client Secret** yet,
point them at
[step 1 of the guide](https://anafpy.readthedocs.io/en/latest/mcp/setup/#step-1-register-an-oauth-application-on-anafs-portal)
and summarize it in three lines: enroll as an API user, create a *Profil Oauth*
with callback `https://localhost:9002/callback` (the `https://` matters — the
portal rejects `http://`), tick **E-Factura** and **E-Transport**, press *Generare
Client ID*.

Ask for the Client ID, the Client Secret, and the firm's **CUI** when you need
them in step 5 — not before.

**Before you ask for the secret, tell them plainly**: *"The Client Secret will be
visible in this conversation and saved in a settings file on this computer. That's
normal for this setup — it's how Claude authenticates to ANAF — but don't paste it
anywhere else."* Say this once, then ask.

## Step 3 — uv

Only needed if the probe said it is missing. Install it with the platform file's
**step-3 block**. `uv` brings its own Python; do not install Python separately.
A freshly installed `uv` will not be on this session's `PATH` — use the absolute
path the platform file gives, rather than telling the user to restart anything.

## Step 4 — Install anafpy

anafpy is on [PyPI](https://pypi.org/project/anafpy/); install it as a uv tool
with the platform file's **step-4 block**. This puts two commands next to `uv`
itself: `anafpy` (the CLI) and `anafpy-mcp` (the server Claude starts). Record
the absolute path of `anafpy-mcp` — step 6 needs it. To update anafpy later:
`uv tool upgrade anafpy`.

## Step 5 — Log in to ANAF (the user runs this)

This step needs their browser, their certificate, and possibly their PIN, and in
paste mode it needs a URL pasted back within ~60 seconds. **You cannot drive it.**
Compose the exact command from the platform file's **step-5 template** with their
values filled in, then ask them to open the integrated terminal
(**Views → Terminal**, or `` Ctrl+` ``) and run it there.

Tell them what to expect: the browser opens on ANAF's login page and asks for the
certificate; afterwards it lands on **an error page — that is expected**; they copy
the full URL from the address bar into the terminal, promptly.

If they'd rather not paste, `mkcert` makes the automatic capture work — see
[step 4, option A of the guide](https://anafpy.readthedocs.io/en/latest/mcp/setup/#option-a-automatic-capture).
Don't lead with it; paste mode needs no extra install.

Then verify it yourself with the platform file's **auth-status probe**. Tokens
refresh automatically for about a year, so this step recurs roughly annually.

## Step 6 — Connect the server to Claude (this is the valuable part)

This is the step that actually needs you: merging JSON, resolving absolute
paths, and getting Windows backslashes right is exactly what an accountant should
never have to do by hand. The config file location and the exact JSON shape are
in the platform file's **step-6 section**.

Do this carefully:

1. **Read** the existing file if there is one. It may hold other connectors — keep
   every one of them.
2. **Back it up** (`claude_desktop_config.json.bak-<something>`) before writing.
3. **Merge** an `anafpy` entry into `mcpServers`, leaving siblings untouched.
4. Use the **absolute path to `anafpy-mcp`** (from step 4), not the bare name —
   Claude Desktop does not inherit the shell `PATH` the way a terminal does, and
   a bare `"command"` is the single most common reason the server shows as failed.
5. Apply any platform-specific `env` additions the platform file calls for
   (e.g. the Windows `ANAFPY_CURL` line when the step-1 curl probe tripped).

`ANAFPY_CIF` is the firm's CUI, digits only. To practice against ANAF's TEST
environment, add `"ANAFPY_ENV": "test"`.

Before writing, sanity-check that the server actually starts with the platform
file's **step-6 sanity check**: it is a stdio server, so closing its input makes
it start, see end-of-input, and exit **0** with no output. That is success. A
traceback or a non-zero exit is not.

Then tell them: **quit Claude Desktop completely and reopen it** (closing the
window is not enough), because it reads this file only at startup.

## Step 7 — Verify, then hand off to Cowork

The tools live in the **Cowork tab**, not here. After they restart, ask them to
open Cowork and try, in order:

1. *"Look up CUI 14399840 in the ANAF taxpayer registry."* — proves the server runs
   (this one needs no login at all).
2. *"What's my ANAF authentication status?"* — proves the login from step 5.
3. *"List my e-Factura messages from the last 7 days."* — proves the whole chain.

If Cowork can't see the tools at all, the likeliest causes are: Claude Desktop
wasn't fully quit; `"command"` isn't an absolute path; or their Cowork session is
running remotely rather than on this computer — a cloud Cowork session cannot reach
a local server.

Close by telling them what they now have: *"Setup is done. From now on you work in
the **Cowork** tab — just ask for what you need in plain language. You only come
back here if something breaks or when the yearly ANAF login expires."*

## Step 8 (optional) — SPV mailbox

Only offer this if they want to read their SPV mailbox or pull official reports.
It is read-only: nothing can be filed through it. List and select the certificate
with the platform file's **step-8 commands**.

`spv login` fires the PIN/2FA prompt on their device. Ask first, then run it and
let them approve on the token. It can fail on ANAF's side for no reason — just run
it again. SPV sessions idle out in under an hour, which is normal and not a broken
install; from then on they can just say *"log me in to SPV"* in Cowork.

On Windows, the platform file has two curl loose ends for this step — read them
there.

## Step 9 (optional) — Declaration tools

Only offer this if they want Claude to fill in, validate, render, and **sign** a
tax declaration (D300 VAT return first) on this computer. Nothing is filed with
ANAF through these tools — Claude produces a signed PDF they then upload on the
portal manually. **Signing is macOS-only** right now; on Windows, offer only the
validate/render half and say signing isn't available yet.

These tools drive ANAF's own desktop validator, **DUKIntegrator**, which you can
install for them:

1. Download and extract
   [`dist_javaInclus20200203.zip`](https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip)
   — it yields a `dist/` folder, which is what the server points at.
2. For each form they file, drop that form's `…Validator.jar` and `…Pdf.jar` (from
   ANAF's declaration page, e.g. the D300 page under `static.anaf.ro/.../Declaratii_R/`)
   into `dist/lib/`. Ask which forms they need before fetching anything.
3. Confirm **Java** is present (`java -version`, JRE/JDK 8+). anafpy only runs DUK's
   *validate*/*render*, which work on any modern JVM.

Then add one line to the `env` block from step 6, pointing at the extracted
folder (on Windows: a doubled-backslash path, e.g.
`C:\\Users\\ana\\DUKIntegrator\\dist`):

```json
        "ANAFPY_DUK_DIR": "/Users/you/DUKIntegrator/dist"
```

After they restart Claude, verify by asking Cowork *"check the declaration setup"*
— it runs `declaratie_duk_status`, which confirms the install and flags an
out-of-date validator (command-line DUK does not auto-update). Signing reuses the
**same qualified certificate** as SPV (step 8): if they selected one there, the
signer picks it up; otherwise set `"ANAFPY_SIGN_IDENTITY"` to the certificate's
Keychain name. Signing fires the PIN/2FA on their device — the same human gate as
everywhere else; you never handle the PIN.

## When something fails

Read the
[troubleshooting table](https://anafpy.readthedocs.io/en/latest/mcp/setup/#troubleshooting)
rather than guessing — it covers the known failure modes and their fixes.

Two failures are **not** installation problems, and you should say so plainly
rather than trying to fix them:

- **ANAF rejects a filing** — that is ANAF's verdict on the document's content.
- **ANAF's service is down or flaky** — retry later; nothing here is broken.
