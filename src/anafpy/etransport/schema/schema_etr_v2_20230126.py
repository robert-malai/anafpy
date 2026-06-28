from enum import Enum

from pydantic import BaseModel, ConfigDict
from xsdata.models.datatype import XmlDate, XmlDateTime
from xsdata_pydantic.fields import field

__NAMESPACE__ = "mfp:anaf:dgti:eTransport:declaratie:v2"


class CodBirouVamalType(Enum):
    VALUE_12801 = 12801
    VALUE_22801 = 22801
    VALUE_22901 = 22901
    VALUE_22902 = 22902
    VALUE_32801 = 32801
    VALUE_42801 = 42801
    VALUE_42901 = 42901
    VALUE_52801 = 52801
    VALUE_52901 = 52901
    VALUE_62801 = 62801
    VALUE_72801 = 72801
    VALUE_72901 = 72901
    VALUE_72902 = 72902
    VALUE_82801 = 82801
    VALUE_92901 = 92901
    VALUE_92902 = 92902
    VALUE_102801 = 102801
    VALUE_112801 = 112801
    VALUE_112901 = 112901
    VALUE_122801 = 122801
    VALUE_122901 = 122901
    VALUE_132901 = 132901
    VALUE_132902 = 132902
    VALUE_132903 = 132903
    VALUE_132904 = 132904
    VALUE_142801 = 142801
    VALUE_152801 = 152801
    VALUE_162801 = 162801
    VALUE_162901 = 162901
    VALUE_162902 = 162902
    VALUE_162903 = 162903
    VALUE_172901 = 172901
    VALUE_172902 = 172902
    VALUE_172903 = 172903
    VALUE_172904 = 172904
    VALUE_182801 = 182801
    VALUE_192801 = 192801
    VALUE_202801 = 202801
    VALUE_212801 = 212801
    VALUE_222901 = 222901
    VALUE_222902 = 222902
    VALUE_222903 = 222903
    VALUE_232801 = 232801
    VALUE_232901 = 232901
    VALUE_242801 = 242801
    VALUE_242901 = 242901
    VALUE_242902 = 242902
    VALUE_252901 = 252901
    VALUE_252902 = 252902
    VALUE_252903 = 252903
    VALUE_252904 = 252904
    VALUE_262801 = 262801
    VALUE_262901 = 262901
    VALUE_272801 = 272801
    VALUE_282801 = 282801
    VALUE_282802 = 282802
    VALUE_292801 = 292801
    VALUE_302801 = 302801
    VALUE_302901 = 302901
    VALUE_302902 = 302902
    VALUE_312801 = 312801
    VALUE_322801 = 322801
    VALUE_322901 = 322901
    VALUE_332801 = 332801
    VALUE_332901 = 332901
    VALUE_332902 = 332902
    VALUE_332903 = 332903
    VALUE_332904 = 332904
    VALUE_342801 = 342801
    VALUE_342901 = 342901
    VALUE_342902 = 342902
    VALUE_352802 = 352802
    VALUE_352901 = 352901
    VALUE_352902 = 352902
    VALUE_352903 = 352903
    VALUE_362901 = 362901
    VALUE_362902 = 362902
    VALUE_362903 = 362903
    VALUE_362904 = 362904
    VALUE_372801 = 372801
    VALUE_372901 = 372901
    VALUE_372902 = 372902
    VALUE_382801 = 382801
    VALUE_392801 = 392801
    VALUE_402801 = 402801
    VALUE_402802 = 402802
    VALUE_402901 = 402901
    VALUE_512801 = 512801
    VALUE_522801 = 522801
    VALUE_522901 = 522901


class CodJudetType(Enum):
    VALUE_1 = 1
    VALUE_2 = 2
    VALUE_3 = 3
    VALUE_4 = 4
    VALUE_5 = 5
    VALUE_6 = 6
    VALUE_7 = 7
    VALUE_8 = 8
    VALUE_9 = 9
    VALUE_10 = 10
    VALUE_11 = 11
    VALUE_51 = 51
    VALUE_12 = 12
    VALUE_13 = 13
    VALUE_14 = 14
    VALUE_15 = 15
    VALUE_16 = 16
    VALUE_17 = 17
    VALUE_52 = 52
    VALUE_18 = 18
    VALUE_19 = 19
    VALUE_20 = 20
    VALUE_21 = 21
    VALUE_22 = 22
    VALUE_23 = 23
    VALUE_24 = 24
    VALUE_25 = 25
    VALUE_26 = 26
    VALUE_27 = 27
    VALUE_28 = 28
    VALUE_29 = 29
    VALUE_30 = 30
    VALUE_31 = 31
    VALUE_32 = 32
    VALUE_33 = 33
    VALUE_34 = 34
    VALUE_35 = 35
    VALUE_36 = 36
    VALUE_37 = 37
    VALUE_38 = 38
    VALUE_39 = 39
    VALUE_40 = 40


class CodPtfType(Enum):
    VALUE_1 = 1
    VALUE_2 = 2
    VALUE_3 = 3
    VALUE_4 = 4
    VALUE_5 = 5
    VALUE_6 = 6
    VALUE_7 = 7
    VALUE_8 = 8
    VALUE_9 = 9
    VALUE_10 = 10
    VALUE_11 = 11
    VALUE_12 = 12
    VALUE_13 = 13
    VALUE_14 = 14
    VALUE_15 = 15
    VALUE_16 = 16
    VALUE_17 = 17
    VALUE_18 = 18
    VALUE_19 = 19
    VALUE_20 = 20
    VALUE_21 = 21
    VALUE_22 = 22
    VALUE_23 = 23
    VALUE_24 = 24
    VALUE_25 = 25
    VALUE_26 = 26
    VALUE_27 = 27
    VALUE_28 = 28
    VALUE_29 = 29
    VALUE_30 = 30
    VALUE_31 = 31
    VALUE_32 = 32
    VALUE_33 = 33
    VALUE_34 = 34
    VALUE_35 = 35
    VALUE_36 = 36
    VALUE_37 = 37
    VALUE_38 = 38


class CodScopOperatiuneType(Enum):
    VALUE_101 = 101
    VALUE_201 = 201
    VALUE_301 = 301
    VALUE_401 = 401
    VALUE_501 = 501
    VALUE_601 = 601
    VALUE_703 = 703
    VALUE_704 = 704
    VALUE_705 = 705
    VALUE_801 = 801
    VALUE_802 = 802
    VALUE_901 = 901
    VALUE_1001 = 1001
    VALUE_1101 = 1101
    VALUE_9901 = 9901
    VALUE_9999 = 9999


class CodTaraType(Enum):
    AD = "AD"
    AE = "AE"
    AF = "AF"
    AG = "AG"
    AI = "AI"
    AL = "AL"
    AM = "AM"
    AN = "AN"
    AO = "AO"
    AQ = "AQ"
    AR = "AR"
    AS = "AS"
    AT = "AT"
    AU = "AU"
    AW = "AW"
    AX = "AX"
    AZ = "AZ"
    BA = "BA"
    BB = "BB"
    BD = "BD"
    BE = "BE"
    BF = "BF"
    BG = "BG"
    BH = "BH"
    BI = "BI"
    BJ = "BJ"
    BL = "BL"
    BM = "BM"
    BN = "BN"
    BO = "BO"
    BQ = "BQ"
    BR = "BR"
    BS = "BS"
    BT = "BT"
    BV = "BV"
    BW = "BW"
    BY = "BY"
    BZ = "BZ"
    CA = "CA"
    CC = "CC"
    CD = "CD"
    CF = "CF"
    CG = "CG"
    CH = "CH"
    CI = "CI"
    CK = "CK"
    CL = "CL"
    CM = "CM"
    CN = "CN"
    CO = "CO"
    CR = "CR"
    CU = "CU"
    CV = "CV"
    CW = "CW"
    CX = "CX"
    CY = "CY"
    CZ = "CZ"
    DE = "DE"
    DJ = "DJ"
    DK = "DK"
    DM = "DM"
    DO = "DO"
    DZ = "DZ"
    EC = "EC"
    EE = "EE"
    EG = "EG"
    EH = "EH"
    EL = "EL"
    ER = "ER"
    ES = "ES"
    ET = "ET"
    FI = "FI"
    FJ = "FJ"
    FK = "FK"
    FM = "FM"
    FO = "FO"
    FR = "FR"
    GA = "GA"
    GB = "GB"
    GD = "GD"
    GE = "GE"
    GF = "GF"
    GG = "GG"
    GH = "GH"
    GI = "GI"
    GL = "GL"
    GM = "GM"
    GN = "GN"
    GP = "GP"
    GQ = "GQ"
    GS = "GS"
    GT = "GT"
    GU = "GU"
    GW = "GW"
    GY = "GY"
    HK = "HK"
    HM = "HM"
    HN = "HN"
    HR = "HR"
    HT = "HT"
    HU = "HU"
    ID = "ID"
    IE = "IE"
    IL = "IL"
    IM = "IM"
    IN = "IN"
    IO = "IO"
    IQ = "IQ"
    IR = "IR"
    IS = "IS"
    IT = "IT"
    JE = "JE"
    JM = "JM"
    JO = "JO"
    JP = "JP"
    KE = "KE"
    KG = "KG"
    KH = "KH"
    KI = "KI"
    KM = "KM"
    KN = "KN"
    KP = "KP"
    KR = "KR"
    KW = "KW"
    KY = "KY"
    KZ = "KZ"
    LA = "LA"
    LB = "LB"
    LC = "LC"
    LI = "LI"
    LK = "LK"
    LR = "LR"
    LS = "LS"
    LT = "LT"
    LU = "LU"
    LV = "LV"
    LY = "LY"
    MA = "MA"
    MC = "MC"
    MD = "MD"
    ME = "ME"
    MF = "MF"
    MG = "MG"
    MH = "MH"
    MK = "MK"
    ML = "ML"
    MM = "MM"
    MN = "MN"
    MO = "MO"
    MP = "MP"
    MQ = "MQ"
    MR = "MR"
    MS = "MS"
    MT = "MT"
    MU = "MU"
    MV = "MV"
    MW = "MW"
    MX = "MX"
    MY = "MY"
    MZ = "MZ"
    NA = "NA"
    NC = "NC"
    NE = "NE"
    NF = "NF"
    NG = "NG"
    NI = "NI"
    NL = "NL"
    NO = "NO"
    NP = "NP"
    NR = "NR"
    NU = "NU"
    NZ = "NZ"
    OM = "OM"
    PA = "PA"
    PE = "PE"
    PF = "PF"
    PG = "PG"
    PH = "PH"
    PK = "PK"
    PL = "PL"
    PM = "PM"
    PN = "PN"
    PR = "PR"
    PS = "PS"
    PT = "PT"
    PW = "PW"
    PY = "PY"
    QA = "QA"
    RE = "RE"
    RO = "RO"
    RS = "RS"
    RU = "RU"
    RW = "RW"
    SA = "SA"
    SB = "SB"
    SC = "SC"
    SD = "SD"
    SE = "SE"
    SG = "SG"
    SH = "SH"
    SI = "SI"
    SJ = "SJ"
    SK = "SK"
    SL = "SL"
    SM = "SM"
    SN = "SN"
    SO = "SO"
    SR = "SR"
    SS = "SS"
    ST = "ST"
    SV = "SV"
    SX = "SX"
    SY = "SY"
    SZ = "SZ"
    TC = "TC"
    TD = "TD"
    TF = "TF"
    TG = "TG"
    TH = "TH"
    TJ = "TJ"
    TK = "TK"
    TL = "TL"
    TM = "TM"
    TN = "TN"
    TO = "TO"
    TR = "TR"
    TT = "TT"
    TV = "TV"
    TW = "TW"
    TZ = "TZ"
    UA = "UA"
    UG = "UG"
    UM = "UM"
    US = "US"
    UY = "UY"
    UZ = "UZ"
    VA = "VA"
    VC = "VC"
    VE = "VE"
    VG = "VG"
    VI = "VI"
    VN = "VN"
    VU = "VU"
    WF = "WF"
    WS = "WS"
    XC = "XC"
    XI = "XI"
    XK = "XK"
    XL = "XL"
    YE = "YE"
    YT = "YT"
    ZA = "ZA"
    ZM = "ZM"
    ZW = "ZW"


class CodTipOperatiuneType(Enum):
    VALUE_10 = 10
    VALUE_12 = 12
    VALUE_14 = 14
    VALUE_20 = 20
    VALUE_22 = 22
    VALUE_24 = 24
    VALUE_30 = 30
    VALUE_40 = 40
    VALUE_50 = 50
    VALUE_60 = 60
    VALUE_70 = 70


class CorectieType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    uit: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "pattern": r"[0-9ACDEFHJKLMNPQRTUVWXY]{14}[0-9]{2}",
        }
    )


class DeclPostAvarieType(Enum):
    D = "D"


class ModifVehiculType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    uit: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "pattern": r"[0-9ACDEFHJKLMNPQRTUVWXY]{14}[0-9]{2}",
        }
    )
    nr_vehicul: str = field(
        metadata={
            "name": "nrVehicul",
            "type": "Attribute",
            "required": True,
            "pattern": r"[0-9A-Z]{2,20}",
        }
    )
    nr_remorca1: str | None = field(
        default=None,
        metadata={
            "name": "nrRemorca1",
            "type": "Attribute",
            "pattern": r"[0-9A-Z]{2,20}",
        },
    )
    nr_remorca2: str | None = field(
        default=None,
        metadata={
            "name": "nrRemorca2",
            "type": "Attribute",
            "pattern": r"[0-9A-Z]{2,20}",
        },
    )
    data_modificare: XmlDateTime = field(
        metadata={
            "name": "dataModificare",
            "type": "Attribute",
            "required": True,
        }
    )
    observatii: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 200,
        },
    )


class NotificareAnterioaraType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    uit: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "pattern": r"[0-9ACDEFHJKLMNPQRTUVWXY]{14}[0-9]{2}",
        }
    )
    observatii: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 200,
        },
    )
    ref_declarant: str | None = field(
        default=None,
        metadata={
            "name": "refDeclarant",
            "type": "Attribute",
            "min_length": 1,
            "max_length": 50,
        },
    )


class TipConfirmareType(Enum):
    VALUE_10 = 10
    VALUE_20 = 20
    VALUE_30 = 30


class TipDocumentType(Enum):
    VALUE_10 = 10
    VALUE_20 = 20
    VALUE_30 = 30
    VALUE_9999 = 9999


class BunuriTransportateType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    cod_scop_operatiune: CodScopOperatiuneType = field(
        metadata={
            "name": "codScopOperatiune",
            "type": "Attribute",
            "required": True,
        }
    )
    cod_tarifar: str | None = field(
        default=None,
        metadata={
            "name": "codTarifar",
            "type": "Attribute",
            "pattern": r"[0-9]{4}|[0-9]{6}|[0-9]{8}",
        },
    )
    denumire_marfa: str = field(
        metadata={
            "name": "denumireMarfa",
            "type": "Attribute",
            "required": True,
            "min_length": 1,
            "max_length": 200,
        }
    )
    cantitate: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "min_exclusive": "0",
            "pattern": r"[0-9]{0,12}(\.[0-9]{0,2})?",
        }
    )
    cod_unitate_masura: str = field(
        metadata={
            "name": "codUnitateMasura",
            "type": "Attribute",
            "required": True,
            "pattern": r"[0-9A-Z]{2,3}",
        }
    )
    greutate_neta: str | None = field(
        default=None,
        metadata={
            "name": "greutateNeta",
            "type": "Attribute",
            "min_exclusive": "0",
            "pattern": r"[0-9]{0,12}(\.[0-9]{0,2})?",
        },
    )
    greutate_bruta: str = field(
        metadata={
            "name": "greutateBruta",
            "type": "Attribute",
            "required": True,
            "min_exclusive": "0",
            "pattern": r"[0-9]{0,12}(\.[0-9]{0,2})?",
        }
    )
    valoare_lei_fara_tva: str | None = field(
        default=None,
        metadata={
            "name": "valoareLeiFaraTva",
            "type": "Attribute",
            "min_inclusive": "0",
            "pattern": r"[0-9]{0,12}(\.[0-9]{0,2})?",
        },
    )
    ref_declarant: str | None = field(
        default=None,
        metadata={
            "name": "refDeclarant",
            "type": "Attribute",
            "min_length": 1,
            "max_length": 50,
        },
    )


class ConfirmareType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    uit: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "pattern": r"[0-9ACDEFHJKLMNPQRTUVWXY]{14}[0-9]{2}",
        }
    )
    tip_confirmare: TipConfirmareType = field(
        metadata={
            "name": "tipConfirmare",
            "type": "Attribute",
            "required": True,
        }
    )
    observatii: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 200,
        },
    )


class DateTransportType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    nr_vehicul: str = field(
        metadata={
            "name": "nrVehicul",
            "type": "Attribute",
            "required": True,
            "pattern": r"[0-9A-Z]{2,20}",
        }
    )
    nr_remorca1: str | None = field(
        default=None,
        metadata={
            "name": "nrRemorca1",
            "type": "Attribute",
            "pattern": r"[0-9A-Z]{2,20}",
        },
    )
    nr_remorca2: str | None = field(
        default=None,
        metadata={
            "name": "nrRemorca2",
            "type": "Attribute",
            "pattern": r"[0-9A-Z]{2,20}",
        },
    )
    cod_tara_org_transport: CodTaraType = field(
        metadata={
            "name": "codTaraOrgTransport",
            "type": "Attribute",
            "required": True,
        }
    )
    cod_org_transport: str | None = field(
        default=None,
        metadata={
            "name": "codOrgTransport",
            "type": "Attribute",
            "min_length": 1,
            "max_length": 30,
        },
    )
    denumire_org_transport: str = field(
        metadata={
            "name": "denumireOrgTransport",
            "type": "Attribute",
            "required": True,
            "min_length": 1,
            "max_length": 200,
        }
    )
    data_transport: XmlDate = field(
        metadata={
            "name": "dataTransport",
            "type": "Attribute",
            "required": True,
        }
    )


class DocumenteTransportType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    tip_document: TipDocumentType = field(
        metadata={
            "name": "tipDocument",
            "type": "Attribute",
            "required": True,
        }
    )
    numar_document: str | None = field(
        default=None,
        metadata={
            "name": "numarDocument",
            "type": "Attribute",
            "min_length": 1,
            "max_length": 50,
        },
    )
    data_document: XmlDate = field(
        metadata={
            "name": "dataDocument",
            "type": "Attribute",
            "required": True,
        }
    )
    observatii: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 200,
        },
    )


class LocatieType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    cod_judet: CodJudetType = field(
        metadata={
            "name": "codJudet",
            "type": "Attribute",
            "required": True,
        }
    )
    denumire_localitate: str = field(
        metadata={
            "name": "denumireLocalitate",
            "type": "Attribute",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        }
    )
    denumire_strada: str = field(
        metadata={
            "name": "denumireStrada",
            "type": "Attribute",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        }
    )
    numar: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 20,
        },
    )
    bloc: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 30,
        },
    )
    scara: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 20,
        },
    )
    etaj: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 20,
        },
    )
    apartament: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 20,
        },
    )
    alte_info: str | None = field(
        default=None,
        metadata={
            "name": "alteInfo",
            "type": "Attribute",
            "min_length": 1,
            "max_length": 200,
        },
    )
    cod_postal: str | None = field(
        default=None,
        metadata={
            "name": "codPostal",
            "type": "Attribute",
            "min_length": 1,
            "max_length": 20,
        },
    )


class PartenerComercialType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    cod_tara: CodTaraType = field(
        metadata={
            "name": "codTara",
            "type": "Attribute",
            "required": True,
        }
    )
    cod: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_length": 1,
            "max_length": 30,
        },
    )
    denumire: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "min_length": 1,
            "max_length": 200,
        }
    )


class LocTraseuRutierType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    locatie: LocatieType | None = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
        },
    )
    cod_ptf: CodPtfType | None = field(
        default=None,
        metadata={
            "name": "codPtf",
            "type": "Attribute",
        },
    )
    cod_birou_vamal: CodBirouVamalType | None = field(
        default=None,
        metadata={
            "name": "codBirouVamal",
            "type": "Attribute",
        },
    )


class NotificareType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    corectie: CorectieType | None = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
        },
    )
    bunuri_transportate: list[BunuriTransportateType] = field(
        default_factory=list,
        metadata={
            "name": "bunuriTransportate",
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
            "min_occurs": 1,
        },
    )
    partener_comercial: PartenerComercialType = field(
        metadata={
            "name": "partenerComercial",
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
            "required": True,
        }
    )
    date_transport: DateTransportType = field(
        metadata={
            "name": "dateTransport",
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
            "required": True,
        }
    )
    loc_start_traseu_rutier: LocTraseuRutierType = field(
        metadata={
            "name": "locStartTraseuRutier",
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
            "required": True,
        }
    )
    loc_final_traseu_rutier: LocTraseuRutierType = field(
        metadata={
            "name": "locFinalTraseuRutier",
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
            "required": True,
        }
    )
    documente_transport: list[DocumenteTransportType] = field(
        default_factory=list,
        metadata={
            "name": "documenteTransport",
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
            "min_occurs": 1,
        },
    )
    notificare_anterioara: list[NotificareAnterioaraType] = field(
        default_factory=list,
        metadata={
            "name": "notificareAnterioara",
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
        },
    )
    cod_tip_operatiune: CodTipOperatiuneType = field(
        metadata={
            "name": "codTipOperatiune",
            "type": "Attribute",
            "required": True,
        }
    )


class ETransportType(BaseModel):
    class Meta:
        name = "eTransportType"

    model_config = ConfigDict(defer_build=True)
    any_element: object | None = field(
        default=None,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )
    notificare: NotificareType | None = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
        },
    )
    stergere: CorectieType | None = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
        },
    )
    confirmare: ConfirmareType | None = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
        },
    )
    modif_vehicul: ModifVehiculType | None = field(
        default=None,
        metadata={
            "name": "modifVehicul",
            "type": "Element",
            "namespace": "mfp:anaf:dgti:eTransport:declaratie:v2",
        },
    )
    cod_declarant: str = field(
        metadata={
            "name": "codDeclarant",
            "type": "Attribute",
            "required": True,
            "pattern": r"((\d{13})|(\d{2,10}))",
        }
    )
    ref_declarant: str | None = field(
        default=None,
        metadata={
            "name": "refDeclarant",
            "type": "Attribute",
            "min_length": 1,
            "max_length": 50,
        },
    )
    decl_post_avarie: DeclPostAvarieType | None = field(
        default=None,
        metadata={
            "name": "declPostAvarie",
            "type": "Attribute",
        },
    )


class ETransport(ETransportType):
    class Meta:
        name = "eTransport"
        namespace = "mfp:anaf:dgti:eTransport:declaratie:v2"

    model_config = ConfigDict(defer_build=True)
