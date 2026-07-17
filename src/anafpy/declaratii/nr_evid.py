"""The D300 ``nr_evid`` payment-evidence number ("numărul de evidență a plății").

A required 23-character field on the D300 VAT return, fully decoded from the
form validator's bytecode (``D300Validator.jar`` v10, matching XSD v12) and
confirmed both against the validation annex example
(``10301010111250211000020``) and against a live ``-v`` acceptance
(2026-07-15). The layout (all positions, 0-indexed):

===========  ==========================================================
positions    content
===========  ==========================================================
``[0:2]``    fixed ``10``
``[2:5]``    ``cod_imp``, correlated with ``tip_decont``
``[5:7]``    fixed ``01``
``[7:11]``   reporting period ``MMYY`` (zero-padded month + last 2 of year)
``[11:17]``  payment due date ``25`` + next month (wrapping) + ``YY``
``[17:21]``  fixed ``0000``
``[21:23]``  check: the two-digit sum of the first 21 digits
===========  ==========================================================

This is composition, not validation — DUK owns validation. The check digit is
computed here so the model never has to; do not let the model compute it.
"""

from __future__ import annotations

__all__ = ["payment_evidence_number"]

# tip_decont -> cod_imp (positions [2:5]), from the validator bytecode:
# 301 = L (monthly), 302 = T (quarterly), 303 = S, 304 = A.
_COD_IMP: dict[str, str] = {"L": "301", "T": "302", "S": "303", "A": "304"}


def payment_evidence_number(*, tip_decont: str, month: int, year: int) -> str:
    """Compose the 23-character D300 ``nr_evid`` for a reporting period.

    Args:
        tip_decont: the D300 wire attribute and settlement code — one of
            ``L`` (monthly), ``T``
            (quarterly), ``S``, ``A``. ``1`` (special settlement) has no known
            ``cod_imp`` mapping and is rejected. The Romanian identifier is
            retained because translating this ANAF-coded attribute would hide
            its direct correspondence to the form.
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
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1..12, got {month}")

    period = f"{month:02d}{year % 100:02d}"
    # Payment due date: the 25th of the following month; December wraps to
    # January of the next year.
    due_month = month + 1
    due_year = year
    if due_month > 12:
        due_month = 1
        due_year = year + 1
    due_date = f"25{due_month:02d}{due_year % 100:02d}"

    body = f"10{cod_imp}01{period}{due_date}0000"
    check = sum(int(digit) for digit in body)  # first 21 digits; always < 100
    return f"{body}{check:02d}"
