# e-Transport

`ETransportClient` covers Romania's goods-transport declaration service: filing
declarations and obtaining UIT codes, correcting/deleting/confirming them,
changing vehicles, and reading back notifications and statuses.

## Fully translated — no XML in sight

Unlike [e-Factura](efactura.md) (XML pass-through), e-Transport is a **full
translation** of ANAF's schema: there is usually no upstream software producing
declaration XML, and ANAF's XSD is small and fully enumerated. The flat models
are **bidirectional** — the same models author a filing and view a parsed one —
and cover all four operations:

| Operation | Model |
|---|---|
| Declaration (or correction, via `correction_of_uit`) | `FlatTransport` |
| Deletion of a UIT | `FlatDeletion` |
| Arrival confirmation | `FlatConfirmation` |
| Vehicle change | `FlatVehicleChange` |

Enum-coded fields (counties, countries, border points, customs offices, operation
types, …) are typed with the enums generated from ANAF's XSD and accept either
the ANAF code or the descriptive name.

## Authoring and filing a declaration

```python
import datetime as dt
from decimal import Decimal

from anafpy.etransport import (
    ETransportClient, FlatDeletion, FlatTransport, FlatTransportAddress,
    FlatTransportDocument, FlatTransportGood, FlatTransportLocation,
    FlatTransportPartner, FlatTransportVehicle,
)
from anafpy.etransport.schema.schema_etr_v2_20230126 import (
    CodJudetType, CodScopOperatiuneType, CodTaraType, CodTipOperatiuneType,
    TipDocumentType,
)

declaration = FlatTransport(
    operation_type=CodTipOperatiuneType.TTN,           # domestic transport
    partner=FlatTransportPartner(
        name="Partener SRL", country=CodTaraType.ROMANIA, code="12345678",
    ),
    vehicle=FlatTransportVehicle(
        plate="CJ01ABC", carrier_name="Transport SRL", carrier_code="23456789",
        carrier_country=CodTaraType.ROMANIA, transport_date=dt.date(2026, 7, 10),
    ),
    start_location=FlatTransportLocation(address=FlatTransportAddress(
        county=CodJudetType.CLUJ, locality="Cluj-Napoca", street="Memorandumului",
    )),
    end_location=FlatTransportLocation(address=FlatTransportAddress(
        county=CodJudetType.MUNICIPIUL_BUCURESTI, locality="Bucuresti",
        street="Calea Victoriei",
    )),
    goods=[FlatTransportGood(
        operation_scope=CodScopOperatiuneType.COMERCIALIZARE,
        name="Materiale constructii", quantity=Decimal("100"), unit_code="KGM",
        gross_weight=Decimal("110"), net_weight=Decimal("100"),
        value_ron=Decimal("2500"), tariff_code="6810",
    )],
    documents=[FlatTransportDocument(
        doc_type=TipDocumentType.CMR, date=dt.date(2026, 7, 9), number="FAC-001",
    )],
)

async with ETransportClient(provider) as etransport:
    result = await etransport.upload_document(declaration, cif="12345678")
    print(result.uit)  # the UIT code, issued at upload time
    # later: delete / confirm / change vehicle on that UIT the same way, e.g.
    await etransport.upload_document(FlatDeletion(uit=result.uit), cif="12345678")
```

`upload_document` renders the flat model to ANAF's XML and files it in one step.
The pieces are also available separately: `build_etransport` composes the
generated schema document, `render_etransport` serializes it, and the plain
`upload` files ready-made XML bytes.

## Reading back

- `get_status` / `upload_and_wait` — track an upload's processing, same shape as
  e-Factura's.
- `list_notifications` — an async iterator over recent notifications (empty
  window → empty iterator; real errors raise — see the
  [error model](errors.md)).
- `info` — active declarations / UIT lookups, returned as an `InfoList`.
- `read_flat_transport` — project any parsed e-Transport document back into the
  same flat models you author with.

## Field-level shape checks

The flat models enforce, at construction time, the XSD constraints plus the
*unconditional* rules of ANAF's e-Transport Schematron — UIT check digits,
gross ≥ net weight, `ALTELE` requiring a note, and so on. This is data hygiene,
not validation: e-Transport has no standalone validator, ANAF validates on
upload, and the operation-type *conditional* rules stay ANAF's (they appear only
as field descriptions). There is deliberately no local rule engine.
