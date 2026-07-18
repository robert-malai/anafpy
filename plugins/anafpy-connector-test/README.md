# anafpy-connector-test (throwaway)

A **temporary** plugin that answers one question: can a plugin-declared stdio MCP
server run under Cowork **and read the local anafpy login** (the OAuth token store
that `anafpy auth login` writes to the OS keychain)?

If yes, the connector could ship as a plugin — install one plugin, get prompted for
credentials, done — and the `anafpy-setup` skill would no longer need to hand-write
`claude_desktop_config.json`. If the server launches but can't see the token store
(because Cowork runs it in an isolated/remote sandbox rather than on the local
machine), the setup-writes-config path stays.

## How it works

- `.mcp.json` declares a server named `anafpy-test` (deliberately not `anafpy`, so it
  can't collide with a real connector) launched via `uvx --from anafpy[mcp] anafpy-mcp`
  — path-independent, pulls from PyPI.
- `userConfig` (in `plugin.json`) prompts for the Client ID / Secret / CUI at enable
  time; the secret is `sensitive` (secure storage). The values substitute into the
  server's `env` as `${user_config.*}`.

## Running the test

1. Ensure you have logged in on this machine: `uv run anafpy auth status` shows a
   valid token, and `uv`/`uvx` is on your PATH.
2. In Cowork, install this plugin and fill in the three prompted values.
3. Ask: **"What ANAF tools do you have?"** — confirms the plugin launched the server.
4. Ask: **"What's my ANAF authentication status?"** — the decisive check: a valid
   token means the plugin-launched server read your **local** login.

## Remove after testing

This plugin is not part of the shipped product. Once the question is answered, delete
`plugins/anafpy-connector-test/` and its marketplace entry.
