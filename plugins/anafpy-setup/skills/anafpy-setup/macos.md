# anafpy setup — macOS commands

Command blocks for [SKILL.md](SKILL.md), keyed by its step numbers. Use these
and only these on macOS.

## Step 1 — probe block

```bash
command -v uv && uv --version
ls ~/.local/bin/anafpy ~/.local/bin/anafpy-mcp 2>/dev/null   # the uv tool install
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json 2>/dev/null
ls ~/.anafpy 2>/dev/null                                     # prior-state signals
```

**Read `~/.anafpy` as a map of what was set up before**, even when anafpy
itself is missing:

- `spv-identity.json` → an SPV certificate was selected (step 8 is done)
- `duk-dist/` → the declaration tools are installed (step 9 is done)
- `ca-cache/` → a previous ANAF login ran on this machine

**Login state outlives the binary.** Tokens live in the macOS Keychain
(service `anafpy`, account `tokens`), not next to the install — so "anafpy is
not installed" does NOT mean "not logged in". If anafpy is installed, probe
now; on a fresh install, probe **immediately after step 4** and only plan
step 5 if it reports not authenticated. A surviving login saves the user the
whole certificate ceremony.

```bash
~/.local/bin/anafpy auth status
```

The Keychain entry holds **tokens only — never the Client ID or Secret**.
Don't go digging with `security dump-keychain`; there is nothing more to find
there. If you need the client credentials, recover them per the note below or
ask the user.

**Before asking the user for Client ID / Secret / CUI**, check whether a
previous run of this skill already recorded them — the config backups this
skill itself creates are the first place to look:

```bash
grep -h '"ANAFPY_' ~/Library/Application\ Support/Claude/claude_desktop_config.json.bak-* 2>/dev/null
```

If step 1 found an old clone-based install (or the user points you at a
project folder), its `.env` may hold `ANAFPY_CLIENT_ID` / `ANAFPY_CLIENT_SECRET`
/ `ANAFPY_CIF` — mention what you found and confirm the values are current
before reusing them. Only if nothing turns up do you send the user back to
the ANAF portal.

## Step 3 — install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

A freshly installed `uv` lands at `~/.local/bin/uv` — use that absolute path for
the rest of this session.

## Step 4 — install anafpy

```bash
~/.local/bin/uv tool install "anafpy[mcp]"    # or plain `uv` if the probe found it
```

The binaries land next to `uv`: `~/.local/bin/anafpy` and
`~/.local/bin/anafpy-mcp` (the absolute path step 6 needs).

**Immediately after installing, run the auth-status probe** (step 1 above) —
a Keychain login from a previous install may still be valid, making step 5
unnecessary.

## Step 5 — login template (the user runs this)

```bash
~/.local/bin/anafpy auth login \
  --client-id <THEIR_CLIENT_ID> --client-secret <THEIR_CLIENT_SECRET> \
  --redirect-uri https://localhost:9002/callback
```

Auth-status probe (you run this to verify):

```bash
~/.local/bin/anafpy auth status
```

## Step 6A — the extension (route A)

```bash
curl -fL -o ~/Downloads/anafpy.mcpb \
  https://github.com/robert-malai/anafpy/releases/latest/download/anafpy.mcpb
open -a Claude ~/Downloads/anafpy.mcpb || open ~/Downloads/anafpy.mcpb
```

A **404** on the download means the latest release predates the extension —
fall back to route B. If `open` produces no install dialog in Claude Desktop,
the user drags `anafpy.mcpb` from **Downloads** onto **Settings → Extensions**.

## Step 6 — Claude Desktop config (route B)

The file is `~/Library/Application Support/Claude/claude_desktop_config.json`.
The entry to merge into `mcpServers`:

```json
{
  "mcpServers": {
    "anafpy": {
      "command": "/Users/ana/.local/bin/anafpy-mcp",
      "env": {
        "ANAFPY_CLIENT_ID": "...",
        "ANAFPY_CLIENT_SECRET": "...",
        "ANAFPY_CIF": "12345678"
      }
    }
  }
}
```

No platform-specific `env` additions on macOS.

Sanity check before writing — run it **with the same env the config will
set**, so it proves the server starts the way Claude Desktop will launch it
(exit **0** with no output = success; don't reach for `timeout` — macOS
doesn't ship it):

```bash
ANAFPY_CLIENT_ID=<id> ANAFPY_CLIENT_SECRET=<secret> ANAFPY_CIF=<cui> \
  ~/.local/bin/anafpy-mcp </dev/null; echo "exit: $?"
```

## Step 8 — SPV commands

```bash
~/.local/bin/anafpy spv certs                 # you can run this
~/.local/bin/anafpy spv select <thumbprint>
```

A selected identity is recorded in `~/.anafpy/spv-identity.json` — if the
step-1 probe saw that file, this step is already done; re-run `spv select`
only if the user wants a different certificate.

Certificates come from the **Keychain** (USB-token and cloud certificates appear
via their vendor middleware, same as for SPV in the browser). No curl concerns
on macOS — the system curl works with ANAF.