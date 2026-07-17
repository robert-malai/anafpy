"""Tests for the ``nr_evid`` payment-evidence composers.

The D300 vectors are the validation-annex example (``tip_decont="L"``,
01/2011) and the live ``-v``-accepted 06/2026 case. The sibling composers
(D100/D710, D101, D301) are pinned to the numbers DUK ``-v`` accepted while
building the per-form completion guides (2026-07-17/18).
"""

from __future__ import annotations

from datetime import date

import pytest

from anafpy.declaratii import (
    obligation_evidence_number,
    payment_evidence_number,
    profit_tax_evidence_number,
    special_vat_evidence_number,
)


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


# --- D100 / D710: the obligation code sits in the code slot (rule R16) ---


def test_obligation_puts_cod_oblig_in_the_code_slot() -> None:
    # DUK -v accepted this for a cod 604 dividend-withholding row (2026-07-17).
    number = obligation_evidence_number(
        cod_oblig="604", month=6, year=2026, due_date=date(2026, 7, 25)
    )
    assert number == "10604010626250726000048"
    assert number[2:5] == "604"  # not the D300 cod_imp


def test_obligation_micro_vector() -> None:
    assert (
        obligation_evidence_number(
            cod_oblig="121", month=6, year=2026, due_date=date(2026, 7, 25)
        )
        == "10121010626250726000042"
    )


def test_obligation_uses_the_supplied_scadenta() -> None:
    number = obligation_evidence_number(
        cod_oblig="604", month=6, year=2026, due_date=date(2026, 10, 15)
    )
    assert number[11:17] == "151026"  # DDMMYY of the passed scadență


def test_obligation_rejects_non_three_digit_code() -> None:
    with pytest.raises(ValueError, match="3-digit obligation code"):
        obligation_evidence_number(
            cod_oblig="6040", month=6, year=2026, due_date=date(2026, 7, 25)
        )


# --- D101: prefix 11, liquidation flag at position [17] ---


def test_profit_tax_prefix_and_vector() -> None:
    # DUK -v accepted for a cod 103 profit-tax advance return (FY2025).
    number = profit_tax_evidence_number(
        cod_obligatie="103", month=12, year=2025, due_date=date(2026, 6, 25)
    )
    assert number == "11103011225250626000038"
    assert number[0:2] == "11"


def test_profit_tax_liquidation_flag_sets_position_17() -> None:
    plain = profit_tax_evidence_number(
        cod_obligatie="103", month=12, year=2025, due_date=date(2026, 6, 25)
    )
    liq = profit_tax_evidence_number(
        cod_obligatie="103",
        month=12,
        year=2025,
        due_date=date(2026, 6, 25),
        in_liquidation=True,
    )
    assert plain[17] == "0"
    assert liq[17] == "1"
    assert int(liq[21:23]) == sum(int(d) for d in liq[:21]) % 100


# --- D301: code 301, position [17] mirrors mijl_trans ---


def test_special_vat_no_transport_vector() -> None:
    assert special_vat_evidence_number(month=6, year=2026) == "10301010626250726000042"


def test_special_vat_new_transport_sets_position_17() -> None:
    # DUK -v accepted position [17]=1 for a mijl_trans="1" filing (rule R16).
    number = special_vat_evidence_number(month=6, year=2026, new_transport=True)
    assert number == "10301010626250726100043"
    assert number[17] == "1"


@pytest.mark.parametrize(
    "compose",
    [
        lambda m: obligation_evidence_number(
            cod_oblig="604", month=m, year=2026, due_date=date(2026, 7, 25)
        ),
        lambda m: profit_tax_evidence_number(
            cod_obligatie="103", month=m, year=2026, due_date=date(2026, 6, 25)
        ),
        lambda m: special_vat_evidence_number(month=m, year=2026),
    ],
)
def test_siblings_reject_out_of_range_month(compose) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="month must be"):
        compose(13)


def test_all_composers_are_23_digit_and_checksum_valid() -> None:
    numbers = [
        payment_evidence_number(tip_decont="T", month=3, year=2026),
        obligation_evidence_number(
            cod_oblig="750", month=12, year=2026, due_date=date(2026, 12, 25)
        ),
        profit_tax_evidence_number(
            cod_obligatie="105", month=12, year=2025, due_date=date(2026, 6, 25)
        ),
        special_vat_evidence_number(month=12, year=2026, new_transport=True),
    ]
    for number in numbers:
        assert len(number) == 23 and number.isdigit()
        assert int(number[21:23]) == sum(int(d) for d in number[:21]) % 100
