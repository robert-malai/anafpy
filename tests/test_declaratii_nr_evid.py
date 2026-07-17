"""Tests for the D300 ``nr_evid`` payment-evidence composer.

Both known vectors are exercised: the validation annex example
(``tip_decont="L"``, 01/2011) and the live ``-v``-accepted 06/2026 case.
"""

from __future__ import annotations

import pytest

from anafpy.declaratii import payment_evidence_number


def test_annex_example_vector() -> None:
    # The validation annex's worked example (v10 = XSD v12).
    assert (
        payment_evidence_number(tip_decont="L", month=1, year=2011)
        == "10301010111250211000020"
    )


def test_live_validated_vector() -> None:
    # Accepted by DUKIntegrator -v on 2026-07-15.
    assert (
        payment_evidence_number(tip_decont="L", month=6, year=2026)
        == "10301010626250726000042"
    )


def test_result_is_23_chars() -> None:
    number = payment_evidence_number(tip_decont="T", month=3, year=2026)
    assert len(number) == 23
    assert number.isdigit()


@pytest.mark.parametrize(
    ("tip_decont", "cod_imp"),
    [("L", "301"), ("T", "302"), ("S", "303"), ("A", "304")],
)
def test_cod_imp_mapping(tip_decont: str, cod_imp: str) -> None:
    number = payment_evidence_number(tip_decont=tip_decont, month=6, year=2026)
    assert number[2:5] == cod_imp


def test_december_due_date_wraps_into_january() -> None:
    # 12/2026 -> due 25 January 2027: MM=01, YY=27.
    number = payment_evidence_number(tip_decont="L", month=12, year=2026)
    assert number[7:11] == "1226"  # reporting period MMYY
    assert number[11:17] == "250127"  # due date 25 + 01 + 27


def test_check_digit_is_sum_of_first_21() -> None:
    number = payment_evidence_number(tip_decont="L", month=6, year=2026)
    assert int(number[21:23]) == sum(int(d) for d in number[:21])


def test_special_settlement_rejected() -> None:
    with pytest.raises(ValueError, match="special settlement"):
        payment_evidence_number(tip_decont="1", month=6, year=2026)


def test_unknown_tip_decont_lists_valid_values() -> None:
    with pytest.raises(ValueError, match="A, L, S, T"):
        payment_evidence_number(tip_decont="X", month=6, year=2026)


@pytest.mark.parametrize("month", [0, 13, -1])
def test_out_of_range_month_rejected(month: int) -> None:
    with pytest.raises(ValueError, match="month must be"):
        payment_evidence_number(tip_decont="L", month=month, year=2026)
