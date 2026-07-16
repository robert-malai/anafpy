---
name: anafpy-setup
description: >
  Install, configure, verify, or repair anafpy on this computer — the local MCP
  server that lets Claude talk to Romania's ANAF (e-Factura, e-Transport, SPV,
  registry lookups). Use when the user wants to set up / install / configure
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

- **macOS** (`Darwin`) or **Windows** + a `Claude` config directory → good, continue.
- **`Linux`**, or no `Claude` directory anywhere → you are almost certainly in a
  cloud/remote session. **Stop.** Tell the user: *"This session is running on
  Anthropic's servers, not on your computer, so I can't reach your certificate or
  your Claude settings from here. Start a new session in the Code tab and pick the
  **Local** environment, then run this again."* Do not proceed.

## Step 1 — Probe everything, then report

Run these together and build a picture before touching anything:

```bash
git --version; command -v uv && uv --version
ls -d ~/anafpy ~/Projects/anafpy 2>/dev/null          # common clone locations
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json 2>/dev/null \
  || cat "$APPDATA/Claude/claude_desktop_config.json" 2>/dev/null
```

If you find an anafpy folder, probe the install itself from inside it:

```bash
cd <anafpy folder> && uv run anafpy auth status
```

Then give the user a short checklist of what is done and what is missing — six
lines, not a wall of text. Something like:

> - ANAF application registered: **I need to ask you**
> - git and uv installed: **yes**
> - anafpy downloaded: **yes**, at `/Users/ana/anafpy`
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

## Step 3 — git and uv

Only install what the probe said is missing.

**macOS**

```bash
xcode-select --install                            # git; skip if `git --version` works
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
```

**Windows (PowerShell)**

```powershell
winget install --id Git.Git -e
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

On Windows, git is usually already there — the Code tab requires Git for Windows
to run at all. `uv` brings its own Python; do not install Python separately.

A freshly installed `uv` will not be on this session's `PATH`. Use its absolute
path (`~/.local/bin/uv`) rather than telling the user to restart anything.

## Step 4 — Download anafpy

Ask where they want it, defaulting to `~/anafpy`. If the folder already exists,
update instead of re-cloning.

```bash
git clone https://github.com/robert-malai/anafpy ~/anafpy   # or: cd ~/anafpy && git pull
cd ~/anafpy && uv sync --frozen --extra mcp
```

Record the absolute path — step 5 needs it.

## Step 5 — Log in to ANAF (the user runs this)

This step needs their browser, their certificate, and possibly their PIN, and in
paste mode it needs a URL pasted back within ~60 seconds. **You cannot drive it.**
Compose the exact command with their values filled in, then ask them to open the
integrated terminal (**Views → Terminal**, or `` Ctrl+` ``) and run it there:

```bash
cd ~/anafpy && uv run anafpy auth login \
  --client-id <THEIR_CLIENT_ID> --client-secret <THEIR_CLIENT_SECRET> \
  --redirect-uri https://localhost:9002/callback --paste
```

Tell them what to expect: the browser opens on ANAF's login page and asks for the
certificate; afterwards it lands on **an error page — that is expected**; they copy
the full URL from the address bar into the terminal, promptly.

If they'd rather not paste, `mkcert` makes the automatic capture work — see
[step 4, option A of the guide](https://anafpy.readthedocs.io/en/latest/mcp/setup/#option-a-automatic-capture).
Don't lead with it; paste mode needs no extra install.

Then verify it yourself:

```bash
cd ~/anafpy && uv run anafpy auth status
```

Tokens refresh automatically for about a year, so this step recurs roughly
annually.

## Step 6 — Connect the server to Claude (this is the valuable part)

This is the step that actually needs you: merging JSON, resolving `uv`'s absolute
path, and getting Windows backslashes right is exactly what an accountant should
never have to do by hand.

The file is:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Do this carefully:

1. **Read** the existing file if there is one. It may hold other connectors — keep
   every one of them.
2. **Back it up** (`claude_desktop_config.json.bak-<something>`) before writing.
3. **Merge** an `anafpy` entry into `mcpServers`, leaving siblings untouched.
4. Use the **absolute path to `uv`** (`command -v uv`), not the bare name — Claude
   Desktop does not inherit the shell `PATH` the way a terminal does, and
   `"command": "uv"` is the single most common reason the server shows as failed.
5. On Windows, write paths with **doubled backslashes** in JSON.

```json
{
  "mcpServers": {
    "anafpy": {
      "command": "/Users/ana/.local/bin/uv",
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

`ANAFPY_CIF` is the firm's CUI, digits only. To practice against ANAF's TEST
environment, add `"ANAFPY_ENV": "test"`.

Before writing, sanity-check that the server actually starts:

```bash
cd ~/anafpy && uv run --frozen --extra mcp anafpy-mcp </dev/null; echo "exit: $?"
```

It is a stdio server: closing its input makes it start, see end-of-input, and exit
**0** with no output. That is success. A traceback or a non-zero exit is not.
(Don't reach for `timeout` here — macOS doesn't ship it.)

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
It is read-only: nothing can be filed through it.

```bash
cd ~/anafpy && uv run anafpy spv certs        # you can run this
cd ~/anafpy && uv run anafpy spv select <thumbprint>
```

`spv login` fires the PIN/2FA prompt on their device. Ask first, then run it and
let them approve on the token. It can fail on ANAF's side for no reason — just run
it again. SPV sessions idle out in under an hour, which is normal and not a broken
install; from then on they can just say *"log me in to SPV"* in Cowork.

On **Windows on ARM** (e.g. Parallels), or with curl 8.13–8.15, `spv login` fails
with `SEC_E_UNKNOWN_CREDENTIALS` or `SEC_E_CONTEXT_EXPIRED`. Both are fixed by
pointing at Git for Windows' curl — add
`"ANAFPY_SPV_CURL": "C:\\Program Files\\Git\\mingw64\\bin\\curl.exe"` to the `env`
block from step 6. Since the Code tab already required Git for Windows, it is
almost certainly installed; check before making them install anything.

## When something fails

Read the
[troubleshooting table](https://anafpy.readthedocs.io/en/latest/mcp/setup/#troubleshooting)
rather than guessing — it covers the known failure modes and their fixes.

Two failures are **not** installation problems, and you should say so plainly
rather than trying to fix them:

- **ANAF rejects a filing** — that is ANAF's verdict on the document's content.
- **ANAF's service is down or flaky** — retry later; nothing here is broken.
