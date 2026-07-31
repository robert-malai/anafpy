"""Human-readable Romanian labels for the e-Transport nomenclatures.

The generated schema enums carry ANAF's codes and ASCII member names
(``CodJudetType.TIMIS`` = 35); neither is what a person reads on a document.
This module is the one home for the display text, used by the card renderer
(:mod:`anafpy.etransport.cardpdf`) and re-exported to the model through the MCP
``etransport_nomenclature`` tool.

The operation-type, scope, document-type and confirmation-type labels are
carried **verbatim from the XSD's ``xs:documentation``** — including ANAF's own
inconsistent mix of cedilla and comma-below diacritics — because the codegen
keeps that text as source comments rather than runtime data, and quoting ANAF
exactly is what makes them checkable against the schema. The county labels have
no XSD counterpart (that enum is documented only by number), so they are spelled
the way Romanian spells them.
"""

from __future__ import annotations

from enum import Enum

from .schema.schema_etr_v2_20230126 import (
    CodJudetType,
    CodScopOperatiuneType,
    CodTipOperatiuneType,
    TipConfirmareType,
    TipDocumentType,
)

__all__ = [
    "CONFIRMATION_TYPE_LABELS",
    "COUNTY_LABELS",
    "DOCUMENT_TYPE_LABELS",
    "LABELS_BY_ENUM",
    "OPERATION_SCOPE_LABELS",
    "OPERATION_TYPE_LABELS",
    "country_text",
    "label_for",
]

OPERATION_TYPE_LABELS = {
    "AIC": "Achiziţie intracomunitară",
    "LHI": "Operațiuni în sistem lohn (UE) - intrare",
    "SCI": "Stocuri la dispoziția clientului (Call-off stock) - intrare",
    "LIC": "Livrare intracomunitară",
    "LHE": "Operațiuni în sistem lohn (UE) - ieșire",
    "SCE": "Stocuri la dispoziția clientului (Call-off stock) - ieșire",
    "TTN": "Transport pe teritoriul naţional",
    "IMP": "Import",
    "EXP": "Export",
    "DIN": "Tranzacţie intracomunitară - Intrare pentru depozitare/formare "
    "nou transport",
    "DIE": "Tranzacţie intracomunitară - Ieşire după depozitare/formare nou transport",
}

OPERATION_SCOPE_LABELS = {
    "COMERCIALIZARE": "Comercializare",
    "PRODUCTIE": "Producție",
    "GRATUITATI": "Gratuități",
    "ECHIPAMENT_COMERCIAL": "Echipament comercial",
    "MIJLOACE_FIXE": "Mijloace fixe",
    "CONSUM_PROPRIU": "Consum propriu",
    "OPERATIUNI_DE_LIVRARE_CU_INSTALARE": "Operațiuni de livrare cu instalare",
    "TRANSFER_INTRE_GESTIUNI": "Transfer între gestiuni",
    "BUNURI_PUSE_LA_DISPOZITIA_CLIENTULUI": "Bunuri puse la dispoziția clientului",
    "LEASING_FINANCIAR_OPERATIONAL": "Leasing financiar/operațional",
    "BUNURI_IN_GARANTIE": "Bunuri în garanție",
    "OPERATIUNI_SCUTITE": "Operațiuni scutite",
    "INVESTITIE_IN_CURS": "Investiție in curs",
    "DONATII_AJUTOARE": "Donații, ajutoare",
    "ALTELE": "Altele",
    "ACELASI_CU_OPERATIUNEA": "Același cu operațiunea",
}

DOCUMENT_TYPE_LABELS = {
    "CMR": "CMR",
    "FACTURA": "Factura",
    "AVIZ_DE_INSOTIRE_A_MARFII": "Aviz de însoțire a mărfii",
    "ALTELE": "Altele",
}

CONFIRMATION_TYPE_LABELS = {
    "CONFIRMAT": "Confirmat",
    "CONFIRMAT_PARTIAL": "Confirmat parţial",
    "INFIRMAT": "Infirmat",
}

COUNTY_LABELS = {
    "ALBA": "Alba",
    "ARAD": "Arad",
    "ARGES": "Argeș",
    "BACAU": "Bacău",
    "BIHOR": "Bihor",
    "BISTRITA_NASAUD": "Bistrița-Năsăud",
    "BOTOSANI": "Botoșani",
    "BRASOV": "Brașov",
    "BRAILA": "Brăila",
    "BUZAU": "Buzău",
    "CARAS_SEVERIN": "Caraș-Severin",
    "CALARASI": "Călărași",
    "CLUJ": "Cluj",
    "CONSTANTA": "Constanța",
    "COVASNA": "Covasna",
    "DAMBOVITA": "Dâmbovița",
    "DOLJ": "Dolj",
    "GALATI": "Galați",
    "GIURGIU": "Giurgiu",
    "GORJ": "Gorj",
    "HARGHITA": "Harghita",
    "HUNEDOARA": "Hunedoara",
    "IALOMITA": "Ialomița",
    "IASI": "Iași",
    "ILFOV": "Ilfov",
    "MARAMURES": "Maramureș",
    "MEHEDINTI": "Mehedinți",
    "MURES": "Mureș",
    "NEAMT": "Neamț",
    "OLT": "Olt",
    "PRAHOVA": "Prahova",
    "SATU_MARE": "Satu Mare",
    "SALAJ": "Sălaj",
    "SIBIU": "Sibiu",
    "SUCEAVA": "Suceava",
    "TELEORMAN": "Teleorman",
    "TIMIS": "Timiș",
    "TULCEA": "Tulcea",
    "VASLUI": "Vaslui",
    "VALCEA": "Vâlcea",
    "VRANCEA": "Vrancea",
    "MUNICIPIUL_BUCURESTI": "Municipiul București",
}

LABELS_BY_ENUM: dict[type[Enum], dict[str, str]] = {
    CodTipOperatiuneType: OPERATION_TYPE_LABELS,
    CodScopOperatiuneType: OPERATION_SCOPE_LABELS,
    CodJudetType: COUNTY_LABELS,
    TipDocumentType: DOCUMENT_TYPE_LABELS,
    TipConfirmareType: CONFIRMATION_TYPE_LABELS,
}


def country_text(member: Enum) -> str:
    """``'Ungaria (HU)'`` — a country made readable, with its ISO code.

    ``CodTaraType`` carries ASCII Romanian names and ISO alpha-2 values for all
    254 entries, so there is nothing to hand-carry: title-casing the member name
    is enough, and appending the code keeps it unambiguous where the Romanian
    name differs from the English one.
    """
    return f"{member.name.replace('_', ' ').title()} ({member.value})"


def label_for(member: Enum) -> str:
    """The display label of one nomenclature member.

    Falls back to the member's own name when the enum has no label table — the
    large geographic lists (border points, customs offices, countries) name
    themselves well enough, and a missing label must never blank a document.
    """
    return LABELS_BY_ENUM.get(type(member), {}).get(member.name, member.name)
