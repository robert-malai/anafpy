"""The translated EN 16931 / CIUS-RO cross-aggregate rule set (tier 2).

Each test provokes one rule family and asserts the finding's official id, so a
regression here means the local report would diverge from what ANAF's
``validare`` endpoint answers.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from _authoring import make_address, make_buyer, make_invoice, make_line, make_seller
from anafpy.efactura.authoring import (
    CreditTransfer,
    DeliveryInformation,
    InvoiceDocument,
    InvoiceValidationError,
    Payee,
    PaymentCard,
    PaymentInstructions,
    Period,
    Severity,
    Totals,
    VatBreakdownEntry,
    VatCategory,
    render_invoice,
    validate,
)


def rules_of(document: InvoiceDocument) -> set[str]:
    return {finding.rule for finding in validate(document).findings}


def test_minimal_invoice_is_clean() -> None:
    report = validate(make_invoice())
    assert report.ok
    assert report.findings == []


def test_exempt_invoice_with_reason_is_clean() -> None:
    doc = make_invoice(
        lines=[make_line(vat_category=VatCategory.EXEMPT, vat_rate=None)],
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.EXEMPT, exemption_reason="art. 292 CF"
            )
        ],
    )
    assert validate(doc).ok


# --- document rules ---------------------------------------------------------------


def test_br53_tax_currency_needs_vat_total_in_it() -> None:
    doc = make_invoice(currency="EUR", tax_currency="RON")
    assert "BR-53" in rules_of(doc)
    doc = make_invoice(
        currency="EUR",
        tax_currency="RON",
        totals=Totals(vat_total_tax_currency=Decimal("95.00")),
    )
    assert "BR-53" not in rules_of(doc)


def test_br_co_25_positive_payable_needs_due_date_or_terms() -> None:
    doc = make_invoice(due_date=None)
    assert "BR-CO-25" in rules_of(doc)
    with_terms = make_invoice(due_date=None, payment_terms="30 zile")
    assert "BR-CO-25" not in rules_of(with_terms)


def test_br_co_26_seller_needs_an_identifier() -> None:
    doc = make_invoice(seller=make_seller(vat_id=None))
    assert "BR-CO-26" in rules_of(doc)
    doc = make_invoice(
        seller=make_seller(vat_id=None, legal_registration_id="J12/345/2020")
    )
    assert "BR-CO-26" not in rules_of(doc)


def test_br17_payee_must_differ_from_seller() -> None:
    doc = make_invoice(payee=Payee(name="Furnizor Test SRL"))
    assert "BR-17" in rules_of(doc)
    assert "BR-17" not in rules_of(make_invoice(payee=Payee(name="Factor SRL")))


def test_br61_credit_transfer_means_needs_an_account() -> None:
    doc = make_invoice(payment_instructions=PaymentInstructions(means_code="30"))
    assert "BR-61" in rules_of(doc)
    doc = make_invoice(
        payment_instructions=PaymentInstructions(
            means_code="30",
            credit_transfers=[CreditTransfer(account_id="RO49AAAA1B31007593840000")],
        )
    )
    assert "BR-61" not in rules_of(doc)
    # Non-transfer means don't require an account.
    doc = make_invoice(payment_instructions=PaymentInstructions(means_code="42"))
    assert "BR-61" not in rules_of(doc)


def test_br51_card_number_is_capped_at_ten_characters() -> None:
    # ANAF enforces string-length(BT-87) <= 10 and rejects the invoice
    # (live-confirmed against validare 2026-07-08), unlike EN 16931's own
    # digit-count warning wording.
    doc = make_invoice(
        payment_instructions=PaymentInstructions(
            means_code="48", card=PaymentCard(number="411111**1111")
        )
    )
    report = validate(doc)
    assert not report.ok
    (finding,) = [f for f in report.findings if f.rule == "BR-51"]
    assert finding.severity is Severity.FATAL
    doc = make_invoice(
        payment_instructions=PaymentInstructions(
            means_code="48", card=PaymentCard(number="4111111111")
        )
    )
    assert "BR-51" not in rules_of(doc)


def test_buyer_with_seller_only_terms_is_flagged() -> None:
    buyer = make_seller(name="Client SRL", tax_registration_id="87654321")
    doc = make_invoice(buyer=buyer)
    assert "UBL-CR" in rules_of(doc)


# --- VAT regime rules --------------------------------------------------------------


def test_br_s_02_seller_vat_evidence_for_standard_rate() -> None:
    doc = make_invoice(
        seller=make_seller(vat_id=None, legal_registration_id="J12/1/2020")
    )
    assert "BR-S-02" in rules_of(doc)
    # BT-32 (tax registration) is acceptable evidence for S.
    doc = make_invoice(
        seller=make_seller(
            vat_id=None,
            legal_registration_id="J12/1/2020",
            tax_registration_id="12345678",
        )
    )
    assert "BR-S-02" not in rules_of(doc)


def test_br_ro_120_buyer_needs_identification() -> None:
    doc = make_invoice(buyer=make_buyer(vat_id=None))
    assert "BR-RO-120" in rules_of(doc)
    doc = make_invoice(
        buyer=make_buyer(vat_id=None, legal_registration_id="J40/1/2019")
    )
    assert "BR-RO-120" not in rules_of(doc)


def test_reverse_charge_needs_buyer_identifier_and_zero_breakdown() -> None:
    doc = make_invoice(
        lines=[make_line(vat_category=VatCategory.REVERSE_CHARGE, vat_rate=None)],
        buyer=make_buyer(vat_id=None),
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.REVERSE_CHARGE, exemption_reason="taxare inversa"
            )
        ],
    )
    rules = rules_of(doc)
    assert "BR-AE-02" in rules  # buyer needs VAT or legal registration id
    assert "BR-RO-120" in rules


def test_intra_community_supply_rules() -> None:
    doc = make_invoice(
        lines=[make_line(vat_category=VatCategory.INTRA_COMMUNITY, vat_rate=None)],
        buyer=make_buyer(
            vat_id="DE811193231", address=make_address(country="DE", county=None)
        ),
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.INTRA_COMMUNITY, exemption_reason="livrare IC"
            )
        ],
    )
    rules = rules_of(doc)
    assert "BR-IC-11" in rules  # no delivery date, no invoicing period
    assert "BR-IC-12" in rules  # no deliver-to address
    doc = make_invoice(
        lines=[make_line(vat_category=VatCategory.INTRA_COMMUNITY, vat_rate=None)],
        buyer=make_buyer(
            vat_id="DE811193231", address=make_address(country="DE", county=None)
        ),
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.INTRA_COMMUNITY, exemption_reason="livrare IC"
            )
        ],
        delivery=DeliveryInformation(
            date=dt.date(2026, 7, 7),
            address=make_address(country="DE", county="Bayern"),
        ),
    )
    rules = rules_of(doc)
    assert "BR-IC-11" not in rules
    assert "BR-IC-12" not in rules


def test_intra_community_needs_buyer_vat_id() -> None:
    doc = make_invoice(
        lines=[make_line(vat_category=VatCategory.INTRA_COMMUNITY, vat_rate=None)],
        buyer=make_buyer(vat_id=None, legal_registration_id="HRB 1234"),
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.INTRA_COMMUNITY, exemption_reason="livrare IC"
            )
        ],
        invoicing_period=Period(start=dt.date(2026, 7, 1)),
        delivery=DeliveryInformation(address=make_address()),
    )
    assert "BR-IC-02" in rules_of(doc)


def test_not_subject_regime_forbids_vat_identifiers_and_mixing() -> None:
    doc = make_invoice(
        lines=[
            make_line(vat_category=VatCategory.NOT_SUBJECT, vat_rate=None),
            make_line(vat_category=VatCategory.STANDARD, vat_rate=Decimal("19")),
        ],
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.NOT_SUBJECT, exemption_reason="neimpozabil"
            ),
        ],
    )
    rules = rules_of(doc)
    assert "BR-O-02" in rules  # seller/buyer VAT ids present
    assert "BR-O-12" in rules  # S line coexists
    assert "BR-S-01" in rules  # S is used but has no breakdown entry
    # With both categories in the breakdown, the coexistence rule fires too.
    doc = make_invoice(
        lines=[
            make_line(vat_category=VatCategory.NOT_SUBJECT, vat_rate=None),
            make_line(vat_category=VatCategory.STANDARD, vat_rate=Decimal("19")),
        ],
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.NOT_SUBJECT, exemption_reason="neimpozabil"
            ),
            VatBreakdownEntry(category=VatCategory.STANDARD, rate=Decimal("19")),
        ],
    )
    assert "BR-O-11" in rules_of(doc)


def test_split_payment_category_is_rejected() -> None:
    doc = make_invoice(
        lines=[
            make_line(vat_category=VatCategory.SPLIT_PAYMENT, vat_rate=Decimal("22")),
            make_line(vat_category=VatCategory.STANDARD, vat_rate=Decimal("19")),
        ]
    )
    rules = rules_of(doc)
    assert "BR-B-01" in rules
    assert "BR-B-02" in rules


def test_breakdown_presence_per_category() -> None:
    # An explicit breakdown that lacks the used category (BR-S-01), and carries a
    # duplicate single-entry category (BR-E-01).
    doc = make_invoice(
        lines=[make_line(vat_category=VatCategory.EXEMPT, vat_rate=None)],
        vat_breakdown=[
            VatBreakdownEntry(category=VatCategory.EXEMPT, exemption_reason="scutit"),
            VatBreakdownEntry(
                category=VatCategory.EXEMPT, exemption_reason="scutit din nou"
            ),
        ],
    )
    assert "BR-E-01" in rules_of(doc)


# --- arithmetic -------------------------------------------------------------------


def test_br_co_10_explicit_lines_total_mismatch() -> None:
    doc = make_invoice(totals=Totals(lines_total=Decimal("101.00")))
    rules = rules_of(doc)
    assert "BR-CO-10" in rules
    assert "BR-CO-13" in rules  # the chain breaks with it


def test_br_co_16_payable_formula() -> None:
    doc = make_invoice(totals=Totals(payable=Decimal("100.00")))
    assert "BR-CO-16" in rules_of(doc)
    doc = make_invoice(
        totals=Totals(prepaid=Decimal("19.00"), payable=Decimal("100.00"))
    )
    assert "BR-CO-16" not in rules_of(doc)


def test_br_co_17_tax_formula_with_slack() -> None:
    # 0.50 off is within the Schematron's +/-1 slack; 1.00 off is not.
    doc = make_invoice(
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.STANDARD,
                rate=Decimal("19"),
                taxable_amount=Decimal("100.00"),
                tax_amount=Decimal("19.50"),
            )
        ],
        totals=Totals(vat_total=Decimal("19.50")),
    )
    assert "BR-CO-17" not in rules_of(doc)
    doc = make_invoice(
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.STANDARD,
                rate=Decimal("19"),
                taxable_amount=Decimal("100.00"),
                tax_amount=Decimal("20.00"),
            )
        ],
        totals=Totals(vat_total=Decimal("20.00")),
    )
    assert "BR-CO-17" in rules_of(doc)


def test_br_s_08_taxable_amount_vs_group_sum() -> None:
    doc = make_invoice(
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.STANDARD,
                rate=Decimal("19"),
                taxable_amount=Decimal("150.00"),  # lines say 100.00
                tax_amount=Decimal("28.50"),
            )
        ],
        totals=Totals(vat_total=Decimal("28.50")),
    )
    assert "BR-S-08" in rules_of(doc)


def test_breakdown_entry_matching_no_lines_is_flagged() -> None:
    doc = make_invoice(
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.STANDARD,
                rate=Decimal("19"),
                taxable_amount=Decimal("100.00"),
                tax_amount=Decimal("19.00"),
            ),
            VatBreakdownEntry(
                category=VatCategory.STANDARD,
                rate=Decimal("9"),
                taxable_amount=Decimal("50.00"),
                tax_amount=Decimal("4.50"),
            ),
        ]
    )
    assert "BR-S-08" in rules_of(doc)


def test_br45_explicit_entry_without_amounts_or_lines() -> None:
    doc = make_invoice(
        vat_breakdown=[
            VatBreakdownEntry(
                category=VatCategory.STANDARD, rate=Decimal("19")
            ),  # filled: has lines
            VatBreakdownEntry(
                category=VatCategory.ZERO_RATED, exemption_reason=None
            ),  # no lines: None
        ]
    )
    assert "BR-45" in rules_of(doc)


# --- render gate ------------------------------------------------------------------


def test_render_invoice_raises_on_fatal_findings() -> None:
    doc = make_invoice(totals=Totals(payable=Decimal("1.00")))
    with pytest.raises(InvoiceValidationError, match="BR-CO-16") as excinfo:
        render_invoice(doc)
    assert not excinfo.value.report.ok
    xml = render_invoice(doc, skip_validation=True)
    assert b"Invoice" in xml


def test_findings_sort_fatal_first() -> None:
    doc = make_invoice(
        totals=Totals(payable=Decimal("1.00")),
        payment_instructions=PaymentInstructions(
            means_code="48", card=PaymentCard(number="4111111111111111")
        ),
    )
    report = validate(doc)
    severities = [finding.severity for finding in report.findings]
    assert severities == sorted(
        severities, key=lambda s: 0 if s is Severity.FATAL else 1
    )
