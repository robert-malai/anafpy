# anafpy-connector-test (throwaway)

A **temporary** plugin that answers one question: can a plugin-declared stdio MCP
server run under Cowork **and read the local anafpy login** (the OAuth token store
that `anafpy auth login` writes to the OS keychain)?

## Round 2 — isolate launch from credentials

Round 1 surfaced two problems: `command: "uvx"` didn't resolve (the Desktop plugin
launcher doesn't inherit the shell PATH, so `~/.local/bin` isn't seen), and the
`userConfig` credential prompt never appeared (that flow is a Claude Code feature,
not wired into the Desktop/Cowork plugins UI). This round removes both variables:

- `command` is the **absolute** `uvx` path so the server actually launches.
- No `env` / `userConfig` — the server runs **credential-less**, which is enough to
  answer the architectural question. anafpy starts without credentials: it serves the
  public `anaf_*` lookups plus `auth_status` (which reads the local token store).

The absolute path is machine-specific (fine for a throwaway); a shipped plugin would
need a bundled launcher script that discovers `uvx` itself.

## Running the test (Cowork)

1. `/plugin marketplace update` then update/reinstall this plugin; restart the app so
   the connector re-launches.
2. Ask: **"Look up CUI 14399840 in the ANAF registry."** — a public, no-auth lookup.
   A real answer proves the plugin **launched the server under Cowork**.
3. Ask: **"What's my ANAF authentication status?"** — if it reports your token, the
   plugin-launched server read your **local** login (the decisive check).

## Interpreting

- Public lookup works → plugin connectors DO run in Cowork. Credential injection is
  then the only remaining problem to solve.
- `auth_status` sees your token → the server runs where your local credentials live —
  the connector could ship as a plugin.
- Still no tools → the server isn't launching even with the absolute path (Cowork may
  not start plugin stdio servers, or runs them in a sandbox); the
  `claude_desktop_config.json` path stays.

## Remove after testing

Delete `plugins/anafpy-connector-test/` and its marketplace entry once done.
