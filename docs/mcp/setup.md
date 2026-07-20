# Installing anafpy on a new computer

> 🇷🇴 Acest ghid este disponibil și [în limba română](setup.ro.md).

This guide takes you from a brand-new computer to talking to ANAF from
[Claude Cowork](https://claude.com) — listing your e-Factura inbox, filing
e-Transport declarations, looking up business partners. It is written for an
accountant, not a programmer: every command is given in full, and every step says
what you should see.

You will do five things, in order:

1. Register an application on ANAF's portal (one-time, on ANAF's website).
2. Install two small tools: `git` and `uv`.
3. Download anafpy.
4. Log in to ANAF once with your qualified certificate.
5. Connect the server to Claude, and check that it works.

Steps 1–4 are one-time. Plan for about 30 minutes, plus however long ANAF's portal
takes.

## Let Claude do it for you (optional)

If you have the [Claude Desktop app](https://claude.ai/download), Claude can walk
through most of this guide with you — checking what is already installed,
installing what is missing, and writing the configuration file in step 5 for you.

In the app's **Code** tab, start a session and make sure its environment is
**Local** (a cloud session runs on Anthropic's servers and cannot see your USB
token). Then click the **+** button next to the prompt box, choose
**Plugins → Add plugin**, and add this marketplace:

```text
robert-malai/anafpy
```

Install the **anafpy setup** plugin from it, then simply ask: *"set up anafpy on
this computer"*.

You still do the two things nobody can do for you: registering the application on
ANAF's portal (step 1) and the certificate login (step 4). Everything else is
handled. The steps below remain the reference — follow them if you prefer to do it
by hand, or if the assisted setup gets stuck.

## Before you start

You need:

- **Your qualified digital certificate** (the USB token you already use for SPV /
  ANAF declarations), plugged in and working in your browser. If you can log in to
  SPV with it today, you are ready.
- **SPV enrollment** for the firm (SPV PJ role) — again, if you already file for
  the firm through SPV, this is done.
- The firm's **CUI** (fiscal code).

One thing to know up front: anafpy is free and provided **as-is**, and support is
best-effort. The application you register on ANAF's portal in step 1 is **your
own** — it identifies you to ANAF, nobody operates it on your behalf, and keeping
it (and your certificate) in order is your responsibility.

## Step 1 — Register an OAuth application on ANAF's portal

ANAF requires every program that calls its APIs to be registered. You do this once,
on the portal, with your certificate:

1. **Enroll as an API user**: on [anaf.ro](https://www.anaf.ro), go to *Servicii
   Online → Înregistrare utilizatori → Dezvoltatori aplicații → Înregistrare pentru
   API-uri*. ANAF emails you a security code to confirm.
2. **Create an OAuth application profile** (*Profil Oauth*):
   - **Denumire aplicație**: any name, e.g. `anafpy`.
   - **Callback URL 1**: exactly `https://localhost:9002/callback` — note the
     **`https://`**; the portal rejects `http://`. This URL never needs a public
     server; only your own browser uses it.
   - **Serviciu**: tick **E-Factura** and **E-Transport**.
3. Press **Generare Client ID**. The portal shows a **Client ID** and a **Client
   Secret**.

Copy both into a password manager (or write them somewhere safe). They identify
*your* application to ANAF and you will need them in steps 4 and 5. They are not
your SPV password and they don't replace the certificate.

## Step 2 — Install git and uv

Open a terminal — **Terminal** on macOS, **PowerShell** on Windows (press Start,
type "PowerShell") — and run:

**macOS**

```bash
xcode-select --install                                 # installs git (skip if git --version already works)
curl -LsSf https://astral.sh/uv/install.sh | sh        # installs uv
```

**Windows (PowerShell)**

```powershell
winget install --id Git.Git -e
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen the terminal, then check both answer:

```bash
git --version
uv --version
```

`uv` manages Python for you — you do **not** need to install Python separately; the
right version is downloaded automatically on first use.

## Step 3 — Download anafpy

Still in the terminal:

```bash
git clone https://github.com/robert-malai/anafpy
cd anafpy
uv sync --frozen --extra mcp
```

The last command builds the environment from the locked dependency list; it takes a
minute the first time. Remember where the folder ended up (run `pwd` on macOS or
`cd` on Windows to print it) — you'll paste that path in step 5. To update anafpy
later: `git pull` in this folder, then `uv sync --frozen --extra mcp` again.

(anafpy is also on PyPI — `pip install 'anafpy[mcp]'` — but this walkthrough
deliberately uses the downloaded folder: the ANAF reference documentation and the
workflow skills that the server offers to Claude ship with the folder, not with
the PyPI package.)

## Step 4 — Log in to ANAF (one-time, with your certificate)

This is the only step that uses the certificate. After you confirm the certificate
in the browser, ANAF sends your computer a one-time code — and there are two ways
to catch it:

- **Option A — automatic (recommended).** A one-time certificate setup makes
  `https://localhost` real on your computer; the login then completes in the
  browser by itself, nothing to copy.
- **Option B — paste mode (no setup).** The browser ends on an error page and you
  copy its address into the terminal within ~60 seconds.

### Option A — automatic capture

First, install [mkcert](https://github.com/FiloSottile/mkcert) — a small tool that
makes certificates your own computer trusts:

**macOS** (via [Homebrew](https://brew.sh); install Homebrew first if
`brew --version` doesn't answer):

```bash
brew install mkcert
```

**Windows (PowerShell)**:

```powershell
winget install FiloSottile.mkcert
```

Then — same on both systems — reopen the terminal, go to the `anafpy` folder from
step 3, and create the `localhost` certificate (once):

```bash
mkcert -install          # one-time; adds mkcert's authority to this computer's trust store — confirm the password/UAC prompt
mkcert localhost 127.0.0.1
```

This writes `localhost+1.pem` and `localhost+1-key.pem` into the current folder.
The certificates mkcert makes are trusted **only on this computer** — nothing
leaves it.

Then plug in the USB token and run (one line, with your values from step 1):

```bash
uv run anafpy auth login --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET> \
  --redirect-uri https://localhost:9002/callback \
  --tls-cert localhost+1.pem --tls-key localhost+1-key.pem
```

Your **browser opens** on ANAF's login page and asks for your **certificate** —
pick it and confirm (enter the token PIN if prompted). After that the browser lands
on a page saying **"You can close this tab and return to the terminal"** — done,
the code was captured automatically, no warnings, nothing to copy. If the listener
can't start for any reason, the command falls back to paste mode (Option B) by
itself.

### Option B — paste mode

```bash
uv run anafpy auth login --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET> \
  --redirect-uri https://localhost:9002/callback --paste
```

What happens, in order:

1. Your **browser opens** on ANAF's login page and asks for your **certificate** —
   pick it and confirm (enter the token PIN if prompted).
2. The browser then lands on an error page ("can't connect to localhost" or
   similar). **This is expected** — there is nothing running at that address; the
   code you need is in the address bar.
3. **Copy the full URL from the browser's address bar** and **paste it into the
   terminal**, which is waiting for it. Do this promptly — the code expires in
   about **60 seconds**. (If it expires, just run the command again.)

### Either way

The command exchanges the code for tokens and stores them in the computer's own
secure credential store (macOS Keychain / Windows Credential Manager). Check it
worked:

```bash
uv run anafpy auth status
```

It should report a valid token. From here on, everything is automatic: the access
token refreshes by itself for about **a year**, without the certificate. You only
repeat this step when the refresh token expires (~365 days) or if you revoke the
application on ANAF's portal — so the USB token is needed roughly **once a year**.

## Step 5 — Connect the server to Claude

anafpy ships a local MCP server — a small program Claude starts on your computer
and talks to. It never sends your credentials anywhere except to ANAF.

### Claude Desktop / Cowork

Cowork reaches local servers through the Claude Desktop app installed on the same
computer, so the configuration lives in Claude Desktop:

1. Install and sign in to [Claude Desktop](https://claude.ai/download).
2. Open its config file (create it if missing):
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
     (in Claude Desktop: *Settings → Developer → Edit Config*)
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
3. Add this (replace the three `...` values and the folder path from step 3; on
   Windows write the path with doubled backslashes, e.g. `C:\\Users\\ana\\anafpy`):

```json
{
  "mcpServers": {
    "anafpy": {
      "command": "uv",
      "args": [
        "run", "--directory", "/Users/ana/anafpy",
        "--frozen", "--extra", "mcp", "anafpy-mcp"
      ],
      "env": {
        "ANAFPY_CLIENT_ID": "...",
        "ANAFPY_CLIENT_SECRET": "...",
        "ANAFPY_CIF": "12345678"
      }
    }
  }
}
```

`ANAFPY_CIF` is the firm's CUI (digits only) — the default fiscal code used when
you don't say otherwise in conversation.

4. Quit Claude Desktop fully and reopen it. The anafpy tools appear under the
   app's connectors/tools, and Cowork sessions on this computer can use them.

### Claude Code (alternative)

If you use Claude Code in a terminal instead:

```bash
claude mcp add anafpy \
  -e ANAFPY_CLIENT_ID=... -e ANAFPY_CLIENT_SECRET=... -e ANAFPY_CIF=... \
  -- uv run --directory /Users/ana/anafpy --frozen --extra mcp anafpy-mcp
```

## Step 6 — Check that it works

Ask Claude, in a new conversation:

1. *"What's my ANAF authentication status?"* — should report a valid token (this
   reads the login from step 4).
2. *"Look up CUI 14399840 in the ANAF taxpayer registry."* — the public lookups
   work even before login, so this confirms the server itself runs.
3. *"List my e-Factura messages from the last 7 days."* — confirms the
   authenticated e-Factura connection end to end.

For e-Transport, filing is deliberately two-step: Claude prepares the declaration
and shows you a preview, and **nothing is filed until you explicitly approve it**
— then it submits and reports the UIT. Try it by asking Claude to declare a
transport from an invoice or CMR you have at hand.

## Step 7 (optional) — Unlock the SPV mailbox tools

The `spv_*` tools let Claude read your **SPV mailbox** (receipts, decisions,
notifications) and request official reports — fiscal vector, outstanding
obligations, filing history, declaration duplicates, income certificates. They
are **read-only**: nothing can be submitted through them.

SPV authenticates with your **qualified certificate directly** (the same one
you used in step 4's browser login), so this is a separate, equally one-time-ish
step — the difference is that SPV sessions are short-lived (under an hour of
idle time), so you re-run the login when you next need SPV, not yearly.

In a terminal, in the anafpy folder:

```bash
uv run anafpy spv certs                  # lists your certificates
uv run anafpy spv select <thumbprint>    # pick yours (the hex id from `certs`)
uv run anafpy spv login                  # answer your token's PIN / 2FA prompt
```

USB-token and cloud certificates (e.g. certSIGN vToken) appear in `certs` via
their own middleware — it must be installed and running, exactly as for SPV in
the browser. The login can occasionally fail on ANAF's side; just run it again
(your PIN/2FA prompt fires on every attempt — that is normal).

Then ask Claude: *"What's my SPV status?"* — it should report your certificate
and the list of companies (CUIs) it may query. When the session expires (they
idle out in under an hour), you can simply tell Claude *"log me in to SPV"* —
it asks for your confirmation, then your token's PIN/2FA prompt fires as usual;
approving it on your device completes the login. The terminal command keeps
working too.

## Step 8 (optional) — Unlock the declaration tools

The `declaratie_*` tools let Claude fill in, validate, render, **sign**, and —
with your explicit approval at every consequential step — **file** a tax
declaration (the D300 VAT return, D100, D112, and any other form ANAF's
validator covers). Filing goes to ANAF's real declaration portal (declarations
have no test environment) through a two-step confirmation flow, and you can
opt out of it entirely with `ANAFPY_DECLARATII_UPLOAD: "off"` in the `env`
block — Claude then hands you the signed PDF to upload on the portal yourself.
Signing is macOS-only for now.

These tools run ANAF's own desktop validator, **DUKIntegrator**, so you install
it once:

1. Download
   [`dist_javaInclus20200203.zip`](https://static.anaf.ro/static/DUKIntegrator/dist_javaInclus20200203.zip)
   and extract it. You get a `dist/` folder — that is what Claude points at.
2. Add the validator for each form you file. From ANAF's declaration pages (e.g.
   the D300 page under `static.anaf.ro/.../Declaratii_R/`), download the form's
   `…Validator.jar` and `…Pdf.jar` and drop them into `dist/lib/`.
3. Make sure you have **Java** (a JRE/JDK, version 8 or newer) installed —
   `java -version` in a terminal should print a version. (anafpy only runs
   DUKIntegrator's *validate* and *render* steps, which work on any modern JVM;
   the Java-8-only limitation you may read about applies to DUK's own signing,
   which anafpy does not use.)

   On macOS, the community [nokeect/duk-integrator-macos](https://github.com/nokeect/duk-integrator-macos)
   project automates this whole install (Java, the kit download, and config fixes)
   — a useful reference, though anafpy signs through your certificate itself rather
   than through DUKIntegrator.

Then point the server at the `dist/` folder by adding one line to the `env` block
from step 5:

```json
        "ANAFPY_DUK_DIR": "/Users/you/DUKIntegrator/dist"
```

Restart Claude and ask *"check the declaration setup"* — Claude runs
`declaratie_duk_status`, which confirms the install and warns if a validator is
out of date (the command-line DUKIntegrator does not auto-update, unlike its
desktop window). Signing uses the **same qualified certificate** as SPV (step 7):
if you selected one there, the declaration signer reuses it; otherwise set
`"ANAFPY_SIGN_IDENTITY"` to the certificate's Keychain name. When Claude signs, it
warns you first, then your token's PIN/2FA prompt fires — approving it on your
device produces the signed PDF.

## Good to know

- **Production vs. test**: the server talks to **production** ANAF by default. To
  practice against ANAF's TEST environment instead, add `"ANAFPY_ENV": "test"`
  next to the other `env` entries (test filings issue real-looking UITs that are
  legally meaningless).
- **Your credentials stay on this computer**: the Client Secret sits in the config
  file above and the tokens in the system's credential store (macOS Keychain /
  Windows Credential Manager) — protect the computer account like you protect
  SPV access.
- **Tokens in a file instead of the keychain**: only needed on hosts without a
  credential store (e.g. a Linux server or Docker). Run the step-4 login with
  `--store-backend file` added and put `"ANAFPY_TOKEN_STORE_BACKEND": "file"`
  next to the other `env` entries in the Claude config; the tokens then live in
  `~/.anafpy/tokens.json` — protect that folder.
- **SPV sessions are short**: unlike the OAuth tokens (yearly), the SPV cookie
  session idles out in well under an hour. That is ANAF's setting, not yours;
  `anafpy spv login` any time the `spv_*` tools ask for it.
- **Yearly renewal**: when tools start failing with a "run `anafpy auth login`"
  message after ~a year, repeat step 4. Nothing else needs to change.
- **Signing out** (leaving a shared computer, handing it back to IT): run
  `uv run anafpy auth logout` from the `anafpy` folder. It deletes the tokens
  from this computer — afterwards the tools answer "run `anafpy auth login`"
  until someone signs in again with the certificate. (ANAF offers no way for a
  program to revoke the tokens on its side; they expire on their own. To cut
  everything off at ANAF's side too, use *Renunțare Oauth* in the ANAF portal,
  which deletes the whole app registration.)

## Troubleshooting

| Symptom | Fix |
|---|---|
| `mkcert: command not found` right after installing it | Close and reopen the terminal so the new tool is picked up, then retry. |
| Login says it can't read `localhost+1.pem` (option A) | Run the login command from the `anafpy` folder — that's where `mkcert` wrote the certificate files — or pass their full path. |
| *"Connection is not private"* warning at `localhost` (option A) | `mkcert -install` didn't complete (it needs the password/UAC confirmation). Run it again, then retry the login; you can also just click **Advanced → Proceed to localhost** once. |
| Browser error page after the certificate step (option B) | Normal in `--paste` mode — copy the URL from the address bar into the terminal (step 4). |
| "expired" / invalid code when pasting | You waited past ~60 s. Run the login command again and paste promptly. |
| No certificate prompt in the browser | The token's driver/software isn't installed or the browser doesn't see the certificate. Test by logging in to SPV first; fix that, then retry. |
| Claude Desktop shows the server as failed / `uv` not found | Desktop apps don't always see the terminal's PATH. In the config, replace `"command": "uv"` with the full path — macOS: `/Users/<you>/.local/bin/uv`; Windows: `C:\\Users\\<you>\\.local\\bin\\uv.exe` (run `where.exe uv` / `which uv` to confirm). |
| Tools answer "run `anafpy auth login`" | Step 4 wasn't completed on this computer, or the token expired (~1 year). Run step 4 again. |
| Filing rejected by ANAF | That's ANAF's verdict on the document's content, not an installation problem — the error text comes back in the tool result; fix the data and prepare again. |
| `anafpy spv login` fails instantly with `SEC_E_UNKNOWN_CREDENTIALS` on a Windows-on-ARM computer (e.g. Parallels on a Mac) | The certificate vendor's software is Intel-only (certSIGN vToken is), so Windows' built-in curl can't use the certificate. Install [Git for Windows](https://git-scm.com/download/win) (the **64-bit** version, not ARM64) and add `"ANAFPY_CURL": "C:\\Program Files\\Git\\mingw64\\bin\\curl.exe"` next to the other `env` entries; set the same variable in PowerShell before `anafpy spv login`. |
| `anafpy spv login` fails with `schannel: failed to read data from server: SEC_E_CONTEXT_EXPIRED (0x80090317)` on Windows | Windows' built-in curl (`C:\Windows\System32\curl.exe`) versions **8.13–8.15** have a [Schannel bug](https://github.com/curl/curl/issues/18029) that breaks ANAF's TLS renegotiation with a certificate-store cert. Check with `curl --version`; if it's in that range, install [Git for Windows](https://git-scm.com/download/win) (its bundled curl is newer) and point `ANAFPY_CURL` at `C:\\Program Files\\Git\\mingw64\\bin\\curl.exe` — in the `env` block and in PowerShell before `anafpy spv login` (run `cygpath -w "$(command -v curl)"` in Git Bash to get the exact path). anafpy pins the Schannel backend for you. |
