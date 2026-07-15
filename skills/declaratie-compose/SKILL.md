---
name: declaratie-compose
description: >
  Compose, validate, render, and sign a Romanian tax declaration (D300 VAT return
  first; the flow is per-form generic) from unstructured information. Use when the
  user wants to prepare, fill in, validate, or sign a declaration (declarație) for
  ANAF. Drives the anafpy declaration MCP tools (declaratie_validate loop →
  declaratie_render → declaratie_sign). Filing with ANAF is manual in this release.
---

# Compose and sign a tax declaration

You are preparing a legal tax declaration for Romania's tax authority (ANAF). The
flow is entirely local — nothing is filed with ANAF here:

extract the facts → author the XML from the form's XSD → `declaratie_validate` in a
loop until ANAF's validator says `ok` → `declaratie_render` to the official PDF →
**show the summary and get the user's review** → warn the approval prompt is coming →
`declaratie_sign` with `confirm=true` → hand back the signed PDF for the user to file
manually.

Two rules override everything else:

- **Never invent a value.** Every field must come from the source or the user. If a
  required value is missing, ask — do not guess amounts, CUI, period, bank details,
  or the settlement type. ANAF's validator (not you) is the authority on correctness.
- **Never self-approve the signature.** `declaratie_sign` fires the user's
  certificate PIN/2FA prompt on their device and produces a legally signed document.
  Call it only after the user has reviewed the rendered PDF and explicitly approved
  in this conversation.

## Step 1 — orient

Call `declaratie_duk_status`. It confirms DUKIntegrator is configured and reports
whether the form's validator is up to date. If a validator is stale, tell the user
and continue with a caveat (ANAF may reject a document the stale validator passes).
If the tool reports DUK is not configured, stop and tell the user to install
DUKIntegrator and set `ANAFPY_DUK_DIR` (see the setup guide).

## Step 2 — get the form's XSD (the authoring template)

DUKIntegrator does **not** generate templates or skeleton XML — its only operations
are validate / render / sign. The **XSD is the authoring template**. Fetch the
current one from the form's page,
`https://static.anaf.ro/static/10/Anaf/Declaratii_R/<nnn>.html` (for D300, `662`),
which links the `d<nnn>_v<NN>_<date>.xml` file — despite the extension, that file is
the XSD. Author the XML directly from it.

For **D300** (VAT return), the shape is one root element `declaratie300` in namespace
`mfp:anaf:dgti:d300:declaratie:v12` with **everything as attributes**, no children. A
validated nil example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<declaratie300 xmlns="mfp:anaf:dgti:d300:declaratie:v12"
  luna="6" an="2026" depusReprezentant="0" bifa_interne="1" temei="0"
  nume_declar="..." prenume_declar="..." functie_declar="Administrator"
  cui="..." den="..." adresa="..." banca="-" cont="-" caen="..."
  tip_decont="L" pro_rata="100.0" bifa_cereale="N" bifa_mob="N" bifa_disp="N"
  bifa_cons="N" solicit_ramb="N" nr_evid="..." totalPlata_A="0"/>
```

## Step 3 — compute `nr_evid`

D300 requires `nr_evid` (numărul de evidență a plății), a 23-character
payment-evidence number. **Always** compute it with `declaratie_nr_evid`
(`tip_decont`, `luna`, `an`) — never by hand; it has a check digit.

## Step 4 — validate in a loop

Call `declaratie_validate` with `form` (e.g. `"D300"`) and the XML. On `ok=false`,
the `findings` are DUK's own error/warning messages — read them, fix the XML, and
call again. Convergence is typically under six rounds; the messages are precise
enough (rule ids, attribute names) to guide each fix. Do not proceed until `ok=true`.

## Step 5 — render and review

Call `declaratie_render` with the validated XML and a `save_pdf_as` path the user
chose. Summarise the declaration for the user (period, CUI, settlement type, key
amounts) and ask them to open and review the PDF.

## Step 6 — sign (only on explicit go)

When the user explicitly approves, tell them the certificate approval prompt (token
PIN / phone 2FA) is about to fire on their device, then call `declaratie_sign` with
`pdf_path` (the rendered PDF) and `confirm=true`. One attempt per call: if it returns
`signed=false` (a dismissed or timed-out approval, a missing certificate), relay the
`guidance` and, with the user's go-ahead, try again.

## Step 7 — hand off

Give the user the signed PDF path and tell them to file it at
**anaf.ro → Depunere declarații → Transmitere declarații** (portal upload is
automated in a later release). If `chain_complete` was false, mention the signature
is leaf-only and portal acceptance of that is unverified.
