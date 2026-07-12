# SPV tool evaluations — 10 read-only questions

Evaluation set for the `spv_*` MCP tools, in the question/expected-answer style
of the mcp-builder evaluation format. Every question is **read-only**: answering
must never file a declaration or write anything to ANAF (an accepted `cerere`
report request is the one permitted ANAF-side effect, and only where stated).

How to run: connect the anafpy MCP server to a Claude client on a machine with
an established SPV session (`anafpy spv login`), ask each question in a fresh
conversation, and grade against the criteria. Answers depend on the live
taxpayer data, so the criteria check *tool trajectory and answer shape*, not
fixed values. Questions use the Romanian report/message names deliberately —
that is what real users say.

---

**Q1.** "Is my SPV connection working? Which companies can I query?"

- Expected trajectory: `spv_status` (single call — not `spv_lista_mesaje`).
- Pass: reports reachable/active, and lists the `authorized_cuis` inventory
  (plus CNP/serial) — or, with no session, relays "run `anafpy spv login`"
  without treating it as a crash.

**Q2.** "What arrived in my SPV in the last two weeks?"

- Expected trajectory: `spv_lista_mesaje` with `zile=14`.
- Pass: summarizes the messages (kind, date, subject CUI) without dumping raw
  JSON; a no-messages answer states that plainly (the `note`), not as an error.

**Q3.** "Show me only the recipise from the last 30 days for CUI <one of the
authorized CUIs>."

- Expected trajectory: `spv_lista_mesaje` with `zile=30`, `cif=...`,
  `tip="RECIPISA"` — server-side filtering, not client-side elimination in
  prose.
- Pass: only RECIPISA entries for that CUI are presented, with their ids.

**Q4.** "My inbox is huge — how many messages did I get in the last 60 days,
and show me just the first five."

- Expected trajectory: `spv_lista_mesaje` with `zile=60`, `limit=5` (paging
  parameters, not fetching everything into context).
- Pass: reports `total` and five entries; mentions more pages exist
  (`has_more`) rather than pretending the five are everything.

**Q5.** "Download the document for message <id from a previous listing> into
~/Documents/anaf as receipt.pdf."

- Expected trajectory: `spv_descarca` with `mesaj_id` and
  `save_as=~/Documents/anaf/receipt.pdf` (or `dest_dir`) — never base64 into
  the conversation.
- Pass: answers with the saved path and size; if the file already exists,
  surfaces the refusal and asks before using `overwrite=true`.

**Q6.** "Get me the VECTOR FISCAL for CUI <authorized CUI>." *(permitted
`cerere` effect)*

- Expected trajectory: `spv_cerere` with `tip="VECTOR FISCAL"` → then
  `spv_asteapta_raport` with the returned `id_solicitare` and a destination
  path.
- Pass: explains the report is generated asynchronously; on delivery reports
  the saved PDF path; on a `pending` timeout relays "valid request — retry
  later with the same id" instead of re-filing.

**Q7.** "Ask for the Istoric declaratii for <authorized CUI> for 2025 — twice."
*(dedupe check; permitted `cerere` effect once)*

- Expected trajectory: `spv_cerere(tip="Istoric declaratii", cui=..., an=2025)`
  twice; the second returns `deduplicated=true` with the same `id_solicitare`.
- Pass: recognizes the second answer as the same request (no `force=true`
  unless the user explicitly asks to re-file).

**Q8.** "Request the D300 duplicate for <authorized CUI>."

- Expected trajectory: `spv_cerere` fails fast client-side (D300 needs `an` and
  `luna`); the model asks the user for year and month — or supplies them if the
  conversation already said — rather than guessing.
- Pass: no blind retry loop; the clarifying question names the missing
  parameters.

**Q9.** "Get me an Adeverinta de venit for 2024, reason: pension."

- Expected trajectory: maps the reason onto ANAF's fixed `motiv` list
  (`Pensie`), or asks which of the accepted reasons applies; `spv_cerere` with
  `tip="Adeverinte Venit"`, `an=2024`, `motiv="Pensie"`.
- Pass: uses a value from the exact list (the validation error message carries
  it) — never invents free-text reasons.

**Q10.** "Check SPV for company 99999999." *(a CUI outside the certificate's
rights)*

- Expected trajectory: `spv_lista_mesaje` (or `spv_cerere`) with
  `cif=99999999`; ANAF answers with a rights `eroare`.
- Pass: relays the verbatim Romanian error plus the English hint (no SPV
  rights), points at the `authorized_cuis` inventory from `spv_status`, and
  does not retry in a loop.
