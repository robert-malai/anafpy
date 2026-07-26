# anafpy setup — Windows commands

Command blocks for [SKILL.md](SKILL.md), keyed by its step numbers. Use these
and only these on Windows. Blocks you run yourself are written for your bash
shell (the Code tab runs Git Bash on Windows); commands the **user** runs are
given in PowerShell form, since that is what their terminal will be.

## Step 1 — probe block

```bash
command -v uv && uv --version
ls "$USERPROFILE/.local/bin/anafpy.exe" "$USERPROFILE/.local/bin/anafpy-mcp.exe" 2>/dev/null
cat "$APPDATA/Claude/claude_desktop_config.json" 2>/dev/null
```

If anafpy is installed, probe the login state:

```bash
"$USERPROFILE/.local/bin/anafpy.exe" auth status
```

**Also probe curl — this is a known setup blocker.** The certificate logins
(SPV, declaration portal) go through curl, and Windows' built-in curl
**8.13–8.15** breaks ANAF's TLS renegotiation
([curl bug #18029](https://github.com/curl/curl/issues/18029)). **Windows on
ARM** (e.g. Parallels) needs Git's x64 curl regardless of version, because
vendor certificate drivers (certSIGN vToken) are x64-only.

```bash
curl --version | head -1                                    # 8.13-8.15 = known ANAF TLS bug
ls "C:\Program Files\Git\mingw64\bin\curl.exe" 2>/dev/null  # the replacement, if needed
uname -m                                                    # aarch64/arm64 = Windows on ARM
```

Put the verdict on the checklist. If it tripped, the fix is applied proactively
in step 6 — don't wait for a login to fail and burn the user's PIN/2FA attempt
on it.

## Step 3 — install uv (PowerShell, you can run it via `powershell -c`)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

A freshly installed `uv` lands at `$USERPROFILE/.local/bin/uv.exe` — use that
absolute path for the rest of this session.

## Step 4 — install anafpy

```bash
"$USERPROFILE/.local/bin/uv.exe" tool install "anafpy[mcp]"   # or plain `uv` if the probe found it
```

The binaries land next to `uv`: `%USERPROFILE%\.local\bin\anafpy.exe` and
`%USERPROFILE%\.local\bin\anafpy-mcp.exe` (the absolute path step 6 needs).

## Step 5 — login template (the user runs this, PowerShell)

```powershell
& "$env:USERPROFILE\.local\bin\anafpy.exe" auth login --client-id <THEIR_CLIENT_ID> --client-secret <THEIR_CLIENT_SECRET> --redirect-uri https://localhost:9002/callback
```

Auth-status probe (you run this to verify):

```bash
"$USERPROFILE/.local/bin/anafpy.exe" auth status
```

## Step 6 — Claude Desktop config

The file is `%APPDATA%\Claude\claude_desktop_config.json`. Write paths with
**doubled backslashes** in JSON. The entry to merge into `mcpServers`:

```json
{
  "mcpServers": {
    "anafpy": {
      "command": "C:\\Users\\ana\\.local\\bin\\anafpy-mcp.exe",
      "env": {
        "ANAFPY_CLIENT_ID": "...",
        "ANAFPY_CLIENT_SECRET": "...",
        "ANAFPY_CIF": "12345678"
      }
    }
  }
}
```

**When the step-1 curl probe tripped** (built-in curl 8.13–8.15, or Windows on
ARM): add to the `env` block, now, proactively —

```json
        "ANAFPY_CURL": "C:\\Program Files\\Git\\mingw64\\bin\\curl.exe"
```

One line covers both certificate logins (SPV and the declaration portal — both
read it). If Git's curl isn't at that path, install it yourself: tell the user
first — *"I need to install a small tool from Git that talks to ANAF correctly —
Windows will ask you to confirm"* — then run
`winget install --id Git.Git -e` and let them answer the UAC prompt. It is
almost always already there (Claude Code on Windows requires Git for Windows),
so probe before installing. We want exactly one file out of that package — an
x64 curl whose TLS stack handles ANAF's login — not git or Git Bash; don't
remove this dependency as unused.

Sanity check before writing (exit **0** with no output = success):

```bash
"$USERPROFILE/.local/bin/anafpy-mcp.exe" </dev/null; echo "exit: $?"
```

## Step 8 — SPV commands

```bash
"$USERPROFILE/.local/bin/anafpy.exe" spv certs                # you can run this
"$USERPROFILE/.local/bin/anafpy.exe" spv select <thumbprint>
```

Certificates come from the **Windows certificate store** (USB-token and cloud
certificates appear via their vendor middleware, same as for SPV in the
browser). Two curl loose ends:

- The config `env` reaches only the server. When the user runs
  `anafpy spv login` in their own terminal, set the variable in that session
  too: `$env:ANAFPY_CURL = "C:\Program Files\Git\mingw64\bin\curl.exe"`
  (PowerShell, before the login).
- If a login still fails with `SEC_E_UNKNOWN_CREDENTIALS` or
  `SEC_E_CONTEXT_EXPIRED`, that is the same curl bug reaching a login anyway —
  go back and apply the step-6 fix rather than retrying.

## Step 9 — declarations

Signing is **not available on Windows** yet: offer the validate/render half
plus the no-login status/recipisa tools, and say plainly that signing, and
therefore the signed-PDF filing flow, need a Mac for now.

Java probe (JRE/JDK 8+; DUKIntegrator needs it):

```bash
java -version 2>&1 | head -1
```

If that fails, anafpy also finds a JVM through `JAVA_HOME` (Windows JRE
installers often set it without touching `PATH`) — probe
`ls "$JAVA_HOME/bin/java.exe" 2>/dev/null` before declaring Java missing. When
it truly is missing, tell the user first, then install one yourself with
`winget install --id EclipseAdoptium.Temurin21.JRE -e` and let them answer the
UAC prompt.

DUKIntegrator install (managed, from ANAF's update feed — as in SKILL.md):

```bash
"$USERPROFILE/.local/bin/anafpy.exe" duk install
```

The dist lands at `%USERPROFILE%\.anafpy\duk-dist`; no `env` entry is needed —
the server finds the managed install by itself. Verify by asking Cowork
*"check the declaration setup"* (`declaratie_duk_status`).
