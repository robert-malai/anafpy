"""The UIT's statutory validity window — the law's default, not ANAF's word.

ANAF reports the real end of a UIT's window as ``data_exp_uit``, but only on the
``info`` endpoint, which it scopes to the transport **organizer** (``cui_op``).
A declarant who is not also the carrier therefore never reads it back: the
lookup answers *"Nu exista informatii pentru aceasta solicitare"* and the card
handed to the driver would carry no validity at all.

The window is not ANAF's discretion, though. OUG 41/2022 art. 11 fixes it at
**5 calendar days counted from the declared transport date**, 15 for the
operations listed in :data:`_EXTENDED`, and ANAF applies it mechanically — its
own info example pairs ``data_transp`` 2024-06-24 with ``data_exp_uit``
2024-06-29 (docs/anaf-reference/etransport/api.md §4). So the window can be
derived from a filing anafpy already holds. What must never happen is the
derived date being passed off as ANAF's: it is labelled as an estimate wherever
it is shown, and :attr:`~anafpy.etransport.card.UitCard.uit_expiry` keeps
holding ANAF's value alone (:class:`~anafpy.etransport.card.UitValidity` is
where the two meet, and ANAF always wins).

Counting, in ANAF's own terms: the transport date is day 1, so the last valid
day is ``transport_date + days - 1`` and the first expired day —
``data_exp_uit``'s definition — is ``transport_date + days``.

Where the sources leave room for doubt the **shorter** window is encoded. The
two errors are not symmetric: an estimate that runs long puts a driver on the
road with a lapsed UIT, which is a contravention (fines 20,000-100,000 RON),
while one that runs short makes a card announce itself early and prompts a
check. Only the first is dangerous.
"""

from __future__ import annotations

import datetime as dt

from .schema.schema_etr_v2_20230126 import CodTipOperatiuneType

__all__ = [
    "EXTENDED_VALIDITY_DAYS",
    "STANDARD_VALIDITY_DAYS",
    "statutory_first_expired_day",
    "statutory_last_valid_day",
    "statutory_validity_days",
]

#: The rule for every operation but the ones below (OUG 41/2022 art. 11).
STANDARD_VALIDITY_DAYS = 5

#: The longer window art. 11 grants intra-community acquisitions and the
#: operations at art. 2 pct. 9 lit. g) and j).
EXTENDED_VALIDITY_DAYS = 15

# AIC (intra-community acquisition), the lohn legs, the call-off stock legs, and
# DIN (transit entering for storage / new-consignment formation).
#
# DIE (70), DIN's outbound counterpart, is deliberately NOT here: neither the
# guide (docs/anaf-reference/etransport/legal.md §5) nor the ordinance text we
# have vendored names it, and an unverified 15 would be the dangerous direction
# to guess in. It gets the standard 5 until the ordinance's own text is read.
_EXTENDED = frozenset(
    {
        CodTipOperatiuneType.AIC,
        CodTipOperatiuneType.LHI,
        CodTipOperatiuneType.LHE,
        CodTipOperatiuneType.SCI,
        CodTipOperatiuneType.SCE,
        CodTipOperatiuneType.DIN,
    }
)


def statutory_validity_days(operation: CodTipOperatiuneType) -> int:
    """How many calendar days art. 11 gives a UIT for ``operation``."""
    return EXTENDED_VALIDITY_DAYS if operation in _EXTENDED else STANDARD_VALIDITY_DAYS


def statutory_last_valid_day(
    operation: CodTipOperatiuneType, transport_date: dt.date
) -> dt.date:
    """The last day the UIT may still be used, counting the transport date in."""
    return transport_date + dt.timedelta(days=statutory_validity_days(operation) - 1)


def statutory_first_expired_day(
    operation: CodTipOperatiuneType, transport_date: dt.date
) -> dt.date:
    """The day the UIT counts as expired — the shape ANAF's ``data_exp_uit`` has."""
    return transport_date + dt.timedelta(days=statutory_validity_days(operation))
