# Quickstart

## Install

From [PyPI](https://pypi.org/project/anafpy/):

```bash
pip install anafpy        # or: uv add anafpy
pip install 'anafpy[mcp]' # with the MCP server
```

## The shape of the library

There are three async clients, one per ANAF service family:

- [`EFacturaClient`](../api/efactura.md) — electronic invoicing: upload, status,
  the message list, and the three-tier download.
- [`ETransportClient`](../api/etransport.md) — goods-transport declarations,
  authored from typed flat models (no XML handling).
- [`PublicClient`](../api/public.md) — ANAF's unauthenticated public services:
  registry lookups, financial statements, and the stateless e-Factura document
  services (server-side validation, PDF rendering). **No credentials needed.**

The first two require ANAF's OAuth2 flow, wrapped by the
[auth layer](auth.md): a one-time interactive `anafpy auth login` with your
qualified certificate, then headless token refresh for about a year.

All clients are async context managers and own their `httpx.AsyncClient` unless
you inject one.

## First calls

The public services work immediately, with no setup at all:

```python
import asyncio

from anafpy.public import PublicClient


async def main() -> None:
    async with PublicClient() as public:
        lookup = await public.lookup_taxpayers(["RO12345678"])
        if lookup.found:
            record = lookup.found[0]
            print(record.name, record.vat_registered, record.efactura_registered)


asyncio.run(main())
```

For the authenticated services, build a `TokenProvider` over the token store that
`anafpy auth login` wrote (see [authentication](auth.md) for the login itself):

```python
from anafpy.auth import KeyringTokenStore, TokenProvider
from anafpy.efactura import EFacturaClient

provider = TokenProvider(
    client_id="<ID>",
    client_secret="<SECRET>",
    store=KeyringTokenStore(),  # OS credential store (the default backend)
    # or FileTokenStore("~/.anafpy/tokens.json") for headless/Docker hosts
)

async with EFacturaClient(provider) as efactura:
    result = await efactura.upload(invoice_xml, cif="RO12345678")
    status = await efactura.get_status(result.upload_id)
    # or, in one call: status = await efactura.upload_and_wait(invoice_xml, cif=...)
```

## Two rules worth knowing up front

**Discrete methods make a single call — no transport retry.** One call, one
result-or-raise, so the non-idempotent `upload` POST is never silently repeated.
Bring your own retry policy if you want one. The only built-in polling is
`upload_and_wait`, which retries on the *business* processing state ("still
processing"), never on transport errors.

**Errors are split between exceptions and values.** Transport, auth, and
programming errors raise `AnafError` subclasses; **business outcomes** (a `nok`
rejection, BR-RO findings) come back as typed values, never raised. On HTTP 429
the client raises `AnafRateLimitError` exposing `retry_after` rather than backing
off itself. The details are in the [error model](errors.md).

## Environments

`EFacturaClient` and `ETransportClient` take an `environment` argument — the
`Environment` enum, `PROD` (default) or `TEST` for ANAF's TEST endpoints:

```python
from anafpy import Environment

async with EFacturaClient(provider, environment=Environment.TEST) as client:
    ...
```

`PublicClient` has no environment: the public services exist only in production.
