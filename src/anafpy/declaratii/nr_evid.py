"""The ``nr_evid`` payment-evidence number ("numărul de evidență a plății").

A required 23-character field on the D300 VAT return and its self-assessed
siblings (D100, D710, D101, D301). One layout underlies all of them, decoded
from the form validators' bytecode and the validation annexes and confirmed
against live ``-v`` acceptances (all positions, 0-indexed):

===========  ==========================================================
positions    content
===========  ==========================================================
``[0:2]``    prefix — ``10`` for the decont/obligation forms, ``11`` for the
             annual profit-tax return (D101)
``[2:5]``    3-digit obligation/settlement code (D300 ``cod_imp`` derived from
             ``tip_decont``; D100/D710/D101 the ``cod_oblig``; D301 ``301``)
``[5:7]``    fixed ``01``
``[7:11]``   reporting period ``MMYY`` (zero-padded month + last 2 of year)
``[11:17]``  payment due date ``DDMMYY`` (the scadență; the decont forms use
             the 25th of the following month)
``[17]``     a per-form flag — ``0`` for D300/D100/D710, the **new-means-of-
             transport** flag for D301, the **liquidation** flag for D101
``[18:21]``  fixed ``000``
``[21:23]``  check: the **last two digits** of the sum of the first 21 digits
             ("se iau ultimele 2 cifre" — a modulo, though for real value
             ranges the sum stays under 100)
===========  ==========================================================

This is composition, not validation — DUK owns validation. The check digit is
computed here so the model never has to; do not let the model compute it. The
validator jars enforce the length and the checksum on every form; the code
slot is additionally checked against the obligation on **D100/D710** (rule
R16), and the position-``[17]`` flag against ``mijl_trans`` on **D301**.
"""

from __future__ import annotations

from datetime import date

__all__ = [
    "obligation_evidence_number",
    "payment_evidence_number",
    "profit_tax_evidence_number",
    "special_vat_evidence_number",
]

# tip_decont -> cod_imp (positions [2:5]), from the D300 validator bytecode:
# 301 = L (monthly), 302 = T (quarterly), 303 = S, 304 = A.
_COD_IMP: dict[str, str] = {"L": "301", "T": "302", "S": "303", "A": "304"}


def _compose(
    *, prefix: str, code: str, month: int, year: int, due: date, flag: int
) -> str:
    """Assemble the 23-character number from its decoded parts.

    ``flag`` occupies position ``[17]``; ``[18:21]`` is the constant ``000``.
    The check is the last two digits of the sum of the first 21 (a modulo).
    """
    period = f"{month:02d}{year % 100:02d}"
    due_str = f"{due.day:02d}{due.month:02d}{due.year % 100:02d}"
    body = f"{prefix}{code}01{period}{due_str}{flag:01d}000"
    check = sum(int(digit) for digit in body) % 100
    return f"{body}{check:02d}"


def _due_25th_of_following_month(month: int, year: int) -> date:
    """The 25th of the month after ``month`` — December wraps into January."""
    due_month, due_year = month + 1, year
    if due_month > 12:
        due_month, due_year = 1, year + 1
    return date(due_year, due_month, 25)


def _check_month(month: int) -> None:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1..12, got {month}")


def _check_code(code: str, *, name: str) -> None:
    if not (len(code) == 3 and code.isdigit()):
        raise ValueError(f"{name} must be a 3-digit obligation code, got {code!r}")


def payment_evidence_number(*, tip_decont: str, month: int, year: int) -> str:
    """Compose the 23-character **D300** ``nr_evid`` for a reporting period.

    Args:
        tip_decont: the D300 wire attribute and settlement code — one of
            ``L`` (monthly), ``T`` (quarterly), ``S``, ``A``. ``1`` (special
            settlement) has no known ``cod_imp`` mapping and is rejected. The
            Romanian identifier is retained because translating this
            ANAF-coded attribute would hide its direct correspondence to the
            form.
        month: reporting month, 1-12.
        year: reporting year (four digits).

    Returns:
        The 23-digit payment-evidence number.

    Raises:
        ValueError: on an unknown ``tip_decont`` or an out-of-range month.
    """
    if (cod_imp := _COD_IMP.get(tip_decont)) is None:
        valid = ", ".join(sorted(_COD_IMP))
        if tip_decont == "1":
            raise ValueError(
                "tip_decont '1' (special settlement) has no known cod_imp "
                f"mapping for nr_evid; expected one of: {valid}"
            )
        raise ValueError(f"unknown tip_decont {tip_decont!r}; expected one of: {valid}")
    _check_month(month)
    return _compose(
        prefix="10",
        code=cod_imp,
        month=month,
        year=year,
        due=_due_25th_of_following_month(month, year),
        flag=0,
    )


def obligation_evidence_number(
    *, cod_oblig: str, month: int, year: int, due_date: date
) -> str:
    """Compose the ``nr_evid`` for a **D100 / D710** budget-obligation row.

    Unlike D300 (whose code slot is the ``tip_decont``-derived ``cod_imp``),
    D100 and its rectifying sibling D710 put the **obligation code** itself in
    positions ``[2:5]`` — the validator jar checks the slot against
    ``cod_oblig`` (rule R16), so the D300 helper's number is rejected here.

    Args:
        cod_oblig: the 3-digit obligation code (the ``cod_oblig`` attribute on
            the ``<obligatie>`` row — e.g. ``604``, ``121``).
        month: reporting month, 1-12 (the last month of the period for a
            quarterly obligation).
        year: reporting year (four digits).
        due_date: the obligation's scadență (payment due date). Most
            obligations fall due on the 25th of the following month, but
            several (excise, specific taxes) differ — pass the actual date.

    Returns:
        The 23-digit payment-evidence number.

    Raises:
        ValueError: on a non-3-digit ``cod_oblig`` or an out-of-range month.
    """
    _check_code(cod_oblig, name="cod_oblig")
    _check_month(month)
    return _compose(
        prefix="10", code=cod_oblig, month=month, year=year, due=due_date, flag=0
    )


def profit_tax_evidence_number(
    *,
    cod_obligatie: str,
    month: int,
    year: int,
    due_date: date,
    in_liquidation: bool = False,
) -> str:
    """Compose the ``nr_evid`` for the annual profit-tax return **D101**.

    D101 differs from the decont forms in two places: the prefix is ``11``
    (not ``10``), and position ``[17]`` is a **liquidation** flag. The
    reporting period is the fiscal-year-end month (``12``/year for a calendar
    year); the scadență is the annual filing deadline (typically 25 June).

    Args:
        cod_obligatie: the 3-digit obligation code (e.g. ``102``/``103``/
            ``105`` for the advance-payment variants).
        month: the fiscal-year-end month, 1-12.
        year: the fiscal year (four digits).
        due_date: the annual filing/payment deadline.
        in_liquidation: set for a liquidation-period return (position
            ``[17]`` becomes ``1``).

    Returns:
        The 23-digit payment-evidence number.

    Raises:
        ValueError: on a non-3-digit ``cod_obligatie`` or an out-of-range month.
    """
    _check_code(cod_obligatie, name="cod_obligatie")
    _check_month(month)
    return _compose(
        prefix="11",
        code=cod_obligatie,
        month=month,
        year=year,
        due=due_date,
        flag=1 if in_liquidation else 0,
    )


def special_vat_evidence_number(
    *, month: int, year: int, new_transport: bool = False
) -> str:
    """Compose the ``nr_evid`` for the special VAT return **D301**.

    D301 is a monthly special decont (code ``301``, due the 25th of the
    following month). Its one twist is position ``[17]``: it mirrors the
    ``mijl_trans`` flag — ``1`` whenever the filing reports an intra-EU
    acquisition of new means of transport (a section-2 row), ``0`` otherwise
    (the validator enforces this correspondence, rule R16). The code slot
    itself is not checked by the D301 jar (only length + checksum), so ``301``
    is the form's own value rather than a validated key.

    Args:
        month: reporting month, 1-12.
        year: reporting year (four digits).
        new_transport: set when the return reports an intra-EU acquisition of
            new means of transport (``mijl_trans="1"``), so position ``[17]``
            becomes ``1``.

    Returns:
        The 23-digit payment-evidence number.

    Raises:
        ValueError: on an out-of-range month.
    """
    _check_month(month)
    return _compose(
        prefix="10",
        code="301",
        month=month,
        year=year,
        due=_due_25th_of_following_month(month, year),
        flag=1 if new_transport else 0,
    )
