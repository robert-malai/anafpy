# Exchange rates (BNR)

`BnrClient` reads the **official exchange rates published by Banca Națională a
României** on `curs.bnr.ro`. It is the one client in anafpy that does not talk
to ANAF, and it exists because ANAF filings are denominated in lei: an invoice
in euro has to be converted before its value can be declared.

No credentials, no certificate, no test/prod split.

```python
from anafpy.bnr import BnrClient

async with BnrClient() as bnr:
    conversion = await bnr.convert("1234.56", "EUR")
    print(conversion.amount_ron)     # Decimal('6491.81')
    print(conversion.rate.quoted)    # Decimal('5.2584')
```

## The rate you get is the rate BNR published

BNR publishes once per **banking day**, just after 13:00. A Saturday, a public
holiday, or a call at nine in the morning therefore has no rate of its own —
so `get_rates` returns the latest set published **on or before** the day you
asked for, and tells you which day that was:

```python
async with BnrClient() as bnr:
    rates = await bnr.get_rates("2026-08-30")   # a Sunday
    print(rates.date)                           # 2026-08-28 — the Friday
```

Read `FxRateSet.date` rather than assuming the date you passed in. Presenting
Friday's rate as Sunday's is the one mistake this client is built to prevent.

Dates reach back to **2005**, the start of BNR's archive; anything earlier
raises `AnafConfigError`.

## Converting

`FxRateSet.convert` does the arithmetic, and there are two reasons not to do it
yourself:

- **The multiplier.** BNR quotes small-denomination currencies per 100 units —
  `<Rate currency="HUF" multiplier="100">1.4430</Rate>` means 100 HUF = 1.4430
  RON. `FxRate.quoted` and `FxRate.multiplier` stay exactly as published, and
  the division happens inside the conversion, so the factor of 100 cannot be
  lost in a rounded intermediate. `FxRate.lei_per_unit` is there when you want
  the per-unit figure to show someone.
- **The rounding.** Two decimals, half away from zero, applied once to the
  final figure — the Romanian fiscal convention, not Python's default banker's
  rounding.

To convert several amounts at one rate — an invoice's lines — fetch the set
once and call its `convert` per amount, so every line demonstrably shares a
rate:

```python
async with BnrClient() as bnr:
    rates = await bnr.get_rates()
    lines = [rates.convert(amount, "EUR") for amount in ("100.00", "250.50")]
```

An unquoted currency code raises `AnafConfigError` listing what BNR does quote.

## Where this is used

The conversion feeds values anafpy otherwise cannot compute:

- e-Transport `value_ron` on a goods line ([e-Transport](etransport.md));
- an invoice's BT-111, which `compute_totals` deliberately leaves explicit-only
  because it needs a rate ([invoice authoring](authoring.md));
- D301's `curs_valutar` ([declarations](declaratii.md)).

**Which day's rate a given filing must use is not this client's call.** It
returns what BNR published on a date you choose. The
[`etransport-declare` skill](../mcp/skills.md) states the declaration-day rule
it follows for UIT filings.

## Parsing

Documents are parsed through models generated from **BNR's own published XSD**
(`https://curs.bnr.ro/xsd/nbrfxrates.xsd`, vendored in `schemas/bnr/`), so the
schema is what enforces required fields and types rather than hand-written
checks. One BNR quirk is handled for you: the year archives through 2025 are
served with an `http://www.bnr.ro/xsd` namespace and 2026 onwards with
`https://…`, and the client folds the two together — so a date either side of
that boundary parses the same way.

## Caching and traffic

BNR asks callers to read these XML files rather than scrape its site pages, and
to store what they take. The client does both.

Each query uses the smallest document that can answer it — the one-day file
(~2 KB) for today, the ten-day file (~14 KB) for the recent past, the year
archive (~350 KB) only for older dates. And what is fetched is cached for as
long as BNR could still change it:

- a **closed year's archive** is final — BNR will never add a day to a year
  that has ended — so it is held for the life of the process;
- a document BNR is **still updating** (today's file, the ten-day window, the
  current year's archive) is re-read every 15 minutes, so a 13:00 publication
  is picked up promptly.

Either way, the reads of one filing — every line of an invoice — cost a single
fetch, concurrent reads share it, and a failed fetch is never cached.

The cache lives and dies with the process; nothing is written to disk.
