# anafpy setup — macOS commands

Command blocks for [SKILL.md](SKILL.md), keyed by its step numbers. Use these
and only these on macOS.

## Step 1 — probe block

```bash
command -v uv && uv --version
ls ~/.local/bin/anafpy ~/.local/bin/anafpy-mcp 2>/dev/null   # the uv tool install
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json 2>/dev/null
```

If anafpy is installed, probe the login state:

```bash
~/.local/bin/anafpy auth status
```

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

## Step 5 — login template (the user runs this)

```bash
~/.local/bin/anafpy auth login \
  --client-id <THEIR_CLIENT_ID> --client-secret <THEIR_CLIENT_SECRET> \
  --redirect-uri https://localhost:9002/callback --paste
```

Auth-status probe (you run this to verify):

```bash
~/.local/bin/anafpy auth status
```

## Step 6 — Claude Desktop config

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

Sanity check before writing (exit **0** with no output = success; don't reach
for `timeout` — macOS doesn't ship it):

```bash
~/.local/bin/anafpy-mcp </dev/null; echo "exit: $?"
```

## Step 8 — SPV commands

```bash
~/.local/bin/anafpy spv certs                 # you can run this
~/.local/bin/anafpy spv select <thumbprint>
```

Certificates come from the **Keychain** (USB-token and cloud certificates appear
via their vendor middleware, same as for SPV in the browser). No curl concerns
on macOS — the system curl works with ANAF.
