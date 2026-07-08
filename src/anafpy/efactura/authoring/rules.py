"""The cross-aggregate EN 16931 / CIUS-RO rule set over :class:`InvoiceDocument`.

:func:`validate` hand-translates the Schematron rules that construction-time
shape checks cannot express — totals arithmetic (BR-CO-10..17), VAT breakdown
consistency (BR-S/Z/E/AE/K/G/O/L/M-01..09), regime-dependent identifier
requirements, and the RO-specific document rules — and returns a
:class:`ValidationReport` of findings instead of raising. Rule ids and
severities match the official CIUS-RO 1.0.9 Schematron so findings line up with
what ANAF's ``validare`` endpoint reports; numeric comparisons mirror the
Schematron's own tolerances (the per-rate sums and the tax formula accept a
strict ±1 slack, the BR-CO totals are exact).

ANAF's validator remains the authority: a clean local report is a strong signal,
never a guarantee.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel

from ...exceptions import AnafError
from .codes import VatCategory
from .models import (
    InvoiceDocument,
    Seller,
    VatBreakdownEntry,
    round2,
)

__all__ = [
    "Finding",
    "InvoiceValidationError",
    "Severity",
    "ValidationReport",
    "validate",
]

#: Categories that make the seller/buyer identifier rules bite (BR-RO-065/120).
_IDENTIFIED_CATEGORIES = frozenset(
    {
        VatCategory.STANDARD,
        VatCategory.ZERO_RATED,
        VatCategory.EXEMPT,
        VatCategory.REVERSE_CHARGE,
        VatCategory.INTRA_COMMUNITY,
        VatCategory.EXPORT,
        VatCategory.IGIC,
        VatCategory.IPSI,
    }
)
#: Categories whose VAT breakdown entry must be unique (BR-Z/E/AE/G/IC/O-01);
#: S, L and M group per rate and may appear several times.
_SINGLE_ENTRY_CATEGORIES = frozenset(
    {
        VatCategory.ZERO_RATED,
        VatCategory.EXEMPT,
        VatCategory.REVERSE_CHARGE,
        VatCategory.EXPORT,
        VatCategory.INTRA_COMMUNITY,
        VatCategory.NOT_SUBJECT,
    }
)
#: Categories whose breakdown tax amount is fixed at zero (BR-*-09).
_ZERO_TAX_CATEGORIES = _SINGLE_ENTRY_CATEGORIES

#: The per-category rule-id families: (breakdown-presence, seller-ids at
#: line/allowance/charge level).
_CATEGORY_RULES: dict[VatCategory, str] = {
    VatCategory.STANDARD: "BR-S",
    VatCategory.ZERO_RATED: "BR-Z",
    VatCategory.EXEMPT: "BR-E",
    VatCategory.REVERSE_CHARGE: "BR-AE",
    VatCategory.INTRA_COMMUNITY: "BR-IC",
    VatCategory.EXPORT: "BR-G",
    VatCategory.NOT_SUBJECT: "BR-O",
    VatCategory.IGIC: "BR-IG",
    VatCategory.IPSI: "BR-IP",
}
#: Payment means codes meaning a credit transfer (BR-61: 30 = credit transfer,
#: 58 = SEPA credit transfer).
_CREDIT_TRANSFER_MEANS = frozenset({"30", "58"})


class Severity(StrEnum):
    """Finding severity, matching the Schematron ``flag``."""

    FATAL = "fatal"
    WARNING = "warning"


class Finding(BaseModel):
    """One rule violation."""

    rule: str
    message: str
    severity: Severity = Severity.FATAL
    location: str = ""


class ValidationReport(BaseModel):
    """The outcome of :func:`validate`: all findings, worst first."""

    findings: list[Finding] = []

    @property
    def ok(self) -> bool:
        """True when no *fatal* finding was raised (warnings may remain)."""
        return all(f.severity is not Severity.FATAL for f in self.findings)

    @property
    def fatal(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.FATAL]


class InvoiceValidationError(AnafError):
    """Raised by :func:`~.build.render_invoice` when the document fails
    :func:`validate` and validation was not explicitly skipped."""

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        rules = ", ".join(sorted({f.rule for f in report.fatal}))
        super().__init__(f"invoice fails {len(report.fatal)} CIUS-RO rule(s): {rules}")


class _Rules:
    """One validation pass; collects findings over a document."""

    def __init__(self, document: InvoiceDocument) -> None:
        self.doc = document
        self.findings: list[Finding] = []
        self.breakdown = document.effective_vat_breakdown()
        self.groups = document._group_amounts()
        self.totals = document.effective_totals()
        # Where each category appears: line (-02 rules), allowance (-03),
        # charge (-04).
        self.usage: dict[VatCategory, set[str]] = {}
        for line in document.lines:
            self.usage.setdefault(line.vat_category, set()).add("line")
        for allowance in document.allowances:
            self.usage.setdefault(allowance.vat_category, set()).add("allowance")
        for charge in document.charges:
            self.usage.setdefault(charge.vat_category, set()).add("charge")

    def flag(
        self,
        rule: str,
        message: str,
        *,
        severity: Severity = Severity.FATAL,
        location: str = "",
    ) -> None:
        self.findings.append(
            Finding(rule=rule, message=message, severity=severity, location=location)
        )

    # -- generic document rules ------------------------------------------------

    def document_rules(self) -> None:
        doc = self.doc
        if doc.tax_currency and self.totals.vat_total_tax_currency is None:
            self.flag(
                "BR-53",
                "tax_currency (BT-6) is set, so the VAT total in that currency "
                "(BT-111) must be supplied in totals.vat_total_tax_currency — it "
                "needs your exchange rate and cannot be computed",
            )
        payable = self.totals.payable or Decimal(0)
        if payable > 0 and doc.due_date is None and doc.payment_terms is None:
            self.flag(
                "BR-CO-25",
                "a positive amount due (BT-115) requires a due date (BT-9) or "
                "payment terms (BT-20)",
            )
        seller = doc.seller
        if not (seller.identifiers or seller.legal_registration_id or seller.vat_id):
            self.flag(
                "BR-CO-26",
                "the seller needs an identifier (BT-29), a legal registration "
                "identifier (BT-30) or a VAT identifier (BT-31)",
            )
        if doc.payee is not None and doc.payee.name == seller.name:
            self.flag(
                "BR-17",
                "the payee (BG-10) is only given when different from the seller",
            )
        if isinstance(doc.buyer, Seller) and (
            doc.buyer.tax_registration_id or doc.buyer.additional_legal_info
        ):
            self.flag(
                "UBL-CR",
                "the buyer cannot carry a tax registration identifier (BT-32) or "
                "additional legal information (BT-33) — those are seller-only "
                "terms in EN 16931",
            )
        instructions = doc.payment_instructions
        if instructions is not None:
            if (
                instructions.means_code in _CREDIT_TRANSFER_MEANS
                and not instructions.credit_transfers
            ):
                self.flag(
                    "BR-61",
                    "a credit-transfer payment means requires the payment account "
                    "identifier (BT-84): add a credit_transfers entry",
                )
            card = instructions.card
            if card and len(card.number) > 10:
                # EN 16931 words BR-51 as a warning about digits, but ANAF's
                # validator enforces string-length(BT-87) <= 10 and rejects the
                # invoice (live-confirmed against validare 2026-07-08).
                self.flag(
                    "BR-51",
                    "the card number (BT-87) must be at most 10 characters — "
                    "e.g. the first 6 and last 4 digits",
                )

    # -- VAT regime rules -------------------------------------------------------

    def _seller_vat_evidence(self, *, vat_only: bool) -> bool:
        seller, rep = self.doc.seller, self.doc.tax_representative
        if vat_only:
            return bool(seller.vat_id or (rep and rep.vat_id))
        return bool(seller.vat_id or seller.tax_registration_id or (rep and rep.vat_id))

    def category_rules(self) -> None:
        doc = self.doc
        entries: dict[VatCategory, list[VatBreakdownEntry]] = {}
        for entry in self.breakdown:
            entries.setdefault(entry.category, []).append(entry)

        for category, places in sorted(self.usage.items(), key=lambda i: i[0].value):
            if category is VatCategory.SPLIT_PAYMENT:
                self.flag(
                    "BR-B-01",
                    "VAT category B (split payment) is only valid on a domestic "
                    "Italian invoice",
                )
                if VatCategory.STANDARD in self.usage:
                    self.flag(
                        "BR-B-02",
                        "VAT categories B (split payment) and S (standard) cannot "
                        "be mixed",
                    )
                continue
            family = _CATEGORY_RULES[category]
            count = len(entries.get(category, []))
            if count == 0 or (category in _SINGLE_ENTRY_CATEGORIES and count > 1):
                need = (
                    "exactly one"
                    if category in _SINGLE_ENTRY_CATEGORIES
                    else "at least one"
                )
                self.flag(
                    f"{family}-01",
                    f"VAT category {category.value} is used, so the VAT breakdown "
                    f"(BG-23) must contain {need} {category.value} entry "
                    f"(found {count})",
                )
            for place, suffix in (
                ("line", "02"),
                ("allowance", "03"),
                ("charge", "04"),
            ):
                if place not in places:
                    continue
                self._identifier_rules(category, f"{family}-{suffix}")

        # BR-O-11..14: O tolerates no other category anywhere.
        if VatCategory.NOT_SUBJECT in entries:
            others = sorted(
                category.value
                for category in entries
                if category is not VatCategory.NOT_SUBJECT
            )
            if others:
                self.flag(
                    "BR-O-11",
                    "a VAT breakdown with category O (not subject to VAT) cannot "
                    f"coexist with other categories ({', '.join(others)})",
                )
            for rule, place in (
                ("BR-O-12", "line"),
                ("BR-O-13", "allowance"),
                ("BR-O-14", "charge"),
            ):
                if any(
                    place in places and category is not VatCategory.NOT_SUBJECT
                    for category, places in self.usage.items()
                ):
                    self.flag(
                        rule,
                        f"an invoice not subject to VAT cannot carry a {place} "
                        "with another VAT category",
                    )

        if VatCategory.INTRA_COMMUNITY in entries:
            delivered = self.doc.delivery is not None and (
                self.doc.delivery.date is not None
            )
            if not delivered and doc.invoicing_period is None:
                self.flag(
                    "BR-IC-11",
                    "an intra-community supply requires the actual delivery date "
                    "(BT-72) or the invoicing period (BG-14)",
                )
            if doc.delivery is None or doc.delivery.address is None:
                self.flag(
                    "BR-IC-12",
                    "an intra-community supply requires the deliver-to country "
                    "(BT-80): set delivery.address",
                )

        # BR-RO-120: the buyer must be identifiable whenever VAT applies.
        if _IDENTIFIED_CATEGORIES & set(self.usage):
            buyer = doc.buyer
            if not (buyer.legal_registration_id or buyer.vat_id):
                self.flag(
                    "BR-RO-120",
                    "the buyer needs a legal registration identifier (BT-47) "
                    "and/or a VAT identifier (BT-48)",
                )

    def _identifier_rules(self, category: VatCategory, rule: str) -> None:
        doc = self.doc
        if category is VatCategory.NOT_SUBJECT:
            # BR-O-02/03/04: the O regime *forbids* the VAT identifiers.
            present = [
                name
                for name, value in (
                    ("seller vat_id (BT-31)", doc.seller.vat_id),
                    (
                        "tax representative vat_id (BT-63)",
                        doc.tax_representative.vat_id
                        if doc.tax_representative
                        else None,
                    ),
                    ("buyer vat_id (BT-48)", doc.buyer.vat_id),
                )
                if value
            ]
            if present:
                self.flag(
                    rule,
                    "an invoice not subject to VAT (category O) cannot carry "
                    + ", ".join(present),
                )
            return
        vat_only = category in (VatCategory.INTRA_COMMUNITY, VatCategory.EXPORT)
        if not self._seller_vat_evidence(vat_only=vat_only):
            wanted = (
                "the seller VAT identifier (BT-31) or the tax representative VAT "
                "identifier (BT-63)"
                if vat_only
                else "a seller VAT identifier (BT-31), tax registration identifier "
                "(BT-32) or tax representative VAT identifier (BT-63)"
            )
            self.flag(rule, f"VAT category {category.value} requires {wanted}")
        if category is VatCategory.REVERSE_CHARGE and not (
            doc.buyer.vat_id or doc.buyer.legal_registration_id
        ):
            self.flag(
                rule,
                "reverse charge (AE) requires the buyer VAT identifier (BT-48) "
                "or legal registration identifier (BT-47)",
            )
        if category is VatCategory.INTRA_COMMUNITY and not doc.buyer.vat_id:
            self.flag(
                rule,
                "an intra-community supply (K) requires the buyer VAT "
                "identifier (BT-48)",
            )

    # -- VAT breakdown arithmetic ----------------------------------------------

    def breakdown_rules(self) -> None:
        for index, entry in enumerate(self.breakdown):
            location = f"vat_breakdown[{index}]"
            family = _CATEGORY_RULES.get(entry.category)
            if family is None:
                continue  # split payment (B): already fatal via BR-B-01
            if entry.taxable_amount is None:
                self.flag(
                    "BR-45",
                    f"VAT breakdown entry {entry.category.value} has no taxable "
                    "amount (BT-116) and no matching lines to compute it from",
                    location=location,
                )
                continue
            if entry.tax_amount is None:
                self.flag(
                    "BR-46",
                    f"VAT breakdown entry {entry.category.value} has no tax "
                    "amount (BT-117)",
                    location=location,
                )
                continue
            key = (
                entry.category,
                None if entry.rate is None else entry.rate.normalize(),
            )
            expected = self.groups.get(key)
            if expected is None:
                self.flag(
                    f"{family}-08",
                    f"VAT breakdown entry {entry.category.value} at rate "
                    f"{entry.rate} matches no line, allowance or charge",
                    location=location,
                )
            else:
                expected = round2(expected)
                exact = entry.category in _SINGLE_ENTRY_CATEGORIES
                delta = abs(entry.taxable_amount - expected)
                if (exact and delta != 0) or (not exact and delta >= 1):
                    self.flag(
                        f"{family}-08",
                        f"VAT breakdown {entry.category.value} taxable amount "
                        f"{entry.taxable_amount} does not match the sum of its "
                        f"lines, allowances and charges ({expected})",
                        location=location,
                    )
            if entry.category in _ZERO_TAX_CATEGORIES:
                if entry.tax_amount != 0:
                    self.flag(
                        f"{family}-09",
                        f"VAT category {entry.category.value} carries a zero tax "
                        f"amount, got {entry.tax_amount}",
                        location=location,
                    )
            else:
                rate = entry.rate or Decimal(0)
                computed = round2(abs(entry.taxable_amount) * rate / 100)
                if abs(abs(entry.tax_amount) - computed) >= 1:
                    self.flag(
                        "BR-CO-17",
                        f"VAT amount {entry.tax_amount} is not taxable amount "
                        f"{entry.taxable_amount} x {rate}% (expected ~{computed})",
                        location=location,
                    )

    # -- totals arithmetic (BG-22) ----------------------------------------------

    def totals_rules(self) -> None:
        computed = self.doc.compute_totals()
        totals = self.totals

        def mismatch(rule: str, name: str, term: str) -> None:
            explicit = getattr(totals, name)
            expected = getattr(computed, name)
            if explicit is not None and expected is not None and (explicit != expected):
                self.flag(
                    rule,
                    f"totals.{name} ({term}) is {explicit}, computed {expected}",
                    location="totals",
                )

        mismatch("BR-CO-10", "lines_total", "BT-106")
        mismatch("BR-CO-11", "allowance_total", "BT-107")
        mismatch("BR-CO-12", "charge_total", "BT-108")
        mismatch("BR-CO-14", "vat_total", "BT-110")

        # The chained formulas run on the effective totals themselves, so two
        # explicit members that disagree with each other are caught even when
        # each matches its own computed sum.
        lines_total = totals.lines_total or Decimal(0)
        tax_exclusive = round2(
            lines_total
            - (totals.allowance_total or Decimal(0))
            + (totals.charge_total or Decimal(0))
        )
        if totals.tax_exclusive != tax_exclusive:
            self.flag(
                "BR-CO-13",
                f"totals.tax_exclusive (BT-109) is {totals.tax_exclusive}; lines "
                f"minus allowances plus charges is {tax_exclusive}",
                location="totals",
            )
        tax_inclusive = round2(
            (totals.tax_exclusive or Decimal(0)) + (totals.vat_total or Decimal(0))
        )
        if totals.tax_inclusive != tax_inclusive:
            self.flag(
                "BR-CO-15",
                f"totals.tax_inclusive (BT-112) is {totals.tax_inclusive}; "
                f"BT-109 + BT-110 is {tax_inclusive}",
                location="totals",
            )
        payable = round2(
            (totals.tax_inclusive or Decimal(0))
            - (totals.prepaid or Decimal(0))
            + (totals.rounding or Decimal(0))
        )
        if totals.payable != payable:
            self.flag(
                "BR-CO-16",
                f"totals.payable (BT-115) is {totals.payable}; BT-112 - BT-113 "
                f"+ BT-114 is {payable}",
                location="totals",
            )


def validate(document: InvoiceDocument) -> ValidationReport:
    """Run the translated EN 16931 + CIUS-RO rule set and report findings.

    Covers the cross-aggregate rules construction cannot enforce: totals
    arithmetic, VAT breakdown presence/consistency per category, VAT-regime
    identifier requirements, payment-instruction coherence. Field formats,
    lengths, code lists and decimal budgets were already enforced when the
    models were constructed.

    Returns:
        A :class:`ValidationReport`; ``report.ok`` is ``True`` when no fatal
        finding remains. ANAF's server-side ``validare`` stays authoritative.
    """
    rules = _Rules(document)
    rules.document_rules()
    rules.category_rules()
    rules.breakdown_rules()
    rules.totals_rules()
    order = {Severity.FATAL: 0, Severity.WARNING: 1}
    rules.findings.sort(key=lambda f: (order[f.severity], f.rule))
    return ValidationReport(findings=rules.findings)
