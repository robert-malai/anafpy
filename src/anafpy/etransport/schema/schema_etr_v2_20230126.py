from enum import Enum

from pydantic import BaseModel, ConfigDict
from xsdata.models.datatype import XmlDate, XmlDateTime
from xsdata_pydantic.fields import field

__NAMESPACE__ = "mfp:anaf:dgti:eTransport:declaratie:v2"


class CodBirouVamalType(Enum):
    BVI_ALBA_IULIA = 12801
    BVI_ARAD = 22801
    BVF_ARAD_AEROPORT = 22901
    BVF_ZONA_LIBERA_CURTICI = 22902
    BVI_PITESTI = 32801
    BVI_BACAU = 42801
    BVF_BACAU_AEROPORT = 42901
    BVI_ORADEA = 52801
    BVF_ORADEA_AEROPORT = 52901
    BVI_BISTRITA_NASAUD = 62801
    BVI_BOTOSANI = 72801
    BVF_STANCA_COSTESTI = 72901
    BVF_RADAUTI_PRUT = 72902
    BVI_BRASOV = 82801
    BVF_ZONA_LIBERA_BRAILA = 92901
    BVF_BRAILA = 92902
    BVI_BUZAU = 102801
    BVI_RESITA = 112801
    BVF_NAIDAS = 112901
    BVI_CLUJ_NAPOCA = 122801
    BVF_CLUJ_NAPOCA_AERO = 122901
    BVF_CONSTANTA_SUD_AGIGEA = 132901
    BVF_MIHAIL_KOGALNICEANU = 132902
    BVF_MANGALIA = 132903
    BVF_CONSTANTA_PORT = 132904
    BVI_SFANTU_GHEORGHE = 142801
    BVI_TARGOVISTE = 152801
    BVI_CRAIOVA = 162801
    BVF_CRAIOVA_AEROPORT = 162901
    BVF_BECHET = 162902
    BVF_CALAFAT = 162903
    BVF_ZONA_LIBERA_GALATI = 172901
    BVF_GIURGIULESTI = 172902
    BVF_OANCEA = 172903
    BVF_GALATI = 172904
    BVI_TARGU_JIU = 182801
    BVI_MIERCUREA_CIUC = 192801
    BVI_DEVA = 202801
    BVI_SLOBOZIA = 212801
    BVF_IASI_AERO = 222901
    BVF_SCULENI = 222902
    BVF_IASI = 222903
    BVI_ANTREPOZITE_ILFOV = 232801
    BVF_OTOPENI_CALATORI = 232901
    BVI_BAIA_MARE = 242801
    BVF_AERO_BAIA_MARE = 242901
    BVF_SIGHET = 242902
    BVF_ORSOVA = 252901
    BVF_PORTILE_DE_FIER_I = 252902
    BVF_PORTILE_DE_FIER_II = 252903
    BVF_DROBETA_TURNU_SEVERIN = 252904
    BVI_TARGU_MURES = 262801
    BVF_TARGU_MURES_AEROPORT = 262901
    BVI_PIATRA_NEAMT = 272801
    BVI_CORABIA = 282801
    BVI_OLT = 282802
    BVI_PLOIESTI = 292801
    BVI_SATU_MARE = 302801
    BVF_HALMEU = 302901
    BVF_AEROPORT_SATU_MARE = 302902
    BVI_ZALAU = 312801
    BVI_SIBIU = 322801
    BVF_SIBIU_AEROPORT = 322901
    BVI_SUCEAVA = 332801
    BVF_DORNESTI = 332901
    BVF_SIRET = 332902
    BVF_SUCEAVA_AERO = 332903
    BVF_VICOVU_DE_SUS = 332904
    BVI_ALEXANDRIA = 342801
    BVF_TURNU_MAGURELE = 342901
    BVF_ZIMNICEA = 342902
    BVI_TIMISOARA_BAZA = 352802
    BVF_JIMBOLIA = 352901
    BVF_MORAVITA = 352902
    BVF_TIMISOARA_AEROPORT = 352903
    BVF_SULINA = 362901
    BVF_AEROPORT_DELTA_DUNARII_TULCEA = 362902
    BVF_TULCEA = 362903
    BVF_ISACCEA = 362904
    BVI_VASLUI = 372801
    BVF_FALCIU = 372901
    BVF_ALBITA = 372902
    BVI_RAMNICU_VALCEA = 382801
    BVI_FOCSANI = 392801
    BVI_BUCURESTI_POSTA = 402801
    BVI_TARGURI_SI_EXPOZITII = 402802
    BVF_BANEASA = 402901
    BVI_CALARASI = 512801
    BVI_GIURGIU = 522801
    BVF_ZONA_LIBERA_GIURGIU = 522901


class CodJudetType(Enum):
    ALBA = 1
    ARAD = 2
    ARGES = 3
    BACAU = 4
    BIHOR = 5
    BISTRITA_NASAUD = 6
    BOTOSANI = 7
    BRASOV = 8
    BRAILA = 9
    BUZAU = 10
    CARAS_SEVERIN = 11
    CALARASI = 51
    CLUJ = 12
    CONSTANTA = 13
    COVASNA = 14
    DAMBOVITA = 15
    DOLJ = 16
    GALATI = 17
    GIURGIU = 52
    GORJ = 18
    HARGHITA = 19
    HUNEDOARA = 20
    IALOMITA = 21
    IASI = 22
    ILFOV = 23
    MARAMURES = 24
    MEHEDINTI = 25
    MURES = 26
    NEAMT = 27
    OLT = 28
    PRAHOVA = 29
    SATU_MARE = 30
    SALAJ = 31
    SIBIU = 32
    SUCEAVA = 33
    TELEORMAN = 34
    TIMIS = 35
    TULCEA = 36
    VASLUI = 37
    VALCEA = 38
    VRANCEA = 39
    MUNICIPIUL_BUCURESTI = 40


class CodPtfType(Enum):
    PETEA = 1
    BORS = 2
    VARSAND = 3
    NADLAC = 4
    CALAFAT = 5
    BECHET = 6
    TURNU_MAGURELE = 7
    ZIMNICEA = 8
    GIURGIU = 9
    OSTROV = 10
    NEGRU_VODA = 11
    VAMA_VECHE = 12
    CALARASI = 13
    CORABIA = 14
    OLTENITA = 15
    CAREI = 16
    CENAD = 17
    EPISCOPIA_BIHOR = 18
    SALONTA = 19
    SACUIENI = 20
    TURNU = 21
    URZICENI = 22
    VALEA_LUI_MIHAI = 23
    VLADIMIRESCU = 24
    PORTILE_DE_FIER_1 = 25
    NAIDAS = 26
    STAMORA_MORAVITA = 27
    JIMBOLIA = 28
    HALMEU = 29
    STANCA_COSTESTI = 30
    SCULENI = 31
    ALBITA = 32
    OANCEA = 33
    GALATI_GIURGIULESTI = 34
    CONSTANTA_SUD_AGIGEA = 35
    SIRET = 36
    NADLAC_2_A1 = 37
    BORS_2_A3 = 38


class CodScopOperatiuneType(Enum):
    COMERCIALIZARE = 101
    PRODUCTIE = 201
    GRATUITATI = 301
    ECHIPAMENT_COMERCIAL = 401
    MIJLOACE_FIXE = 501
    CONSUM_PROPRIU = 601
    OPERATIUNI_DE_LIVRARE_CU_INSTALARE = 703
    TRANSFER_INTRE_GESTIUNI = 704
    BUNURI_PUSE_LA_DISPOZITIA_CLIENTULUI = 705
    LEASING_FINANCIAR_OPERATIONAL = 801
    BUNURI_IN_GARANTIE = 802
    OPERATIUNI_SCUTITE = 901
    INVESTITIE_IN_CURS = 1001
    DONATII_AJUTOARE = 1101
    ALTELE = 9901
    ACELASI_CU_OPERATIUNEA = 9999


class CodTaraType(Enum):
    ANDORRA = "AD"
    EMIRATELE_ARABE_UNITE = "AE"
    AFGANISTAN = "AF"
    ANTIGUA_SI_BARBUDA = "AG"
    ANGUILLA = "AI"
    ALBANIA = "AL"
    ARMENIA = "AM"
    NETHERLANDS_ANTILLES = "AN"
    ANGOLA = "AO"
    ANTARCTICA = "AQ"
    ARGENTINA = "AR"
    SAMOA_AMERICANA = "AS"
    AUSTRIA = "AT"
    AUSTRALIA = "AU"
    ARUBA = "AW"
    INSULELE_ALAND = "AX"
    AZERBAIDJAN = "AZ"
    BOSNIA_SI_HERTEGOVINA = "BA"
    BARBADOS = "BB"
    BANGLADESH = "BD"
    BELGIA = "BE"
    BURKINA_FASO = "BF"
    BULGARIA = "BG"
    BAHRAIN = "BH"
    BURUNDI = "BI"
    BENIN = "BJ"
    SAINT_BARTHELEMY = "BL"
    BERMUDA = "BM"
    BRUNEI = "BN"
    BOLIVIA = "BO"
    BONAIRE_SINT_EUSTATIUS_SI_SABA = "BQ"
    BRAZILIA = "BR"
    BAHAMAS = "BS"
    BHUTAN = "BT"
    INSULA_BOUVET = "BV"
    BOTSWANA = "BW"
    BELARUS = "BY"
    BELIZE = "BZ"
    CANADA = "CA"
    INSULELE_COCOS = "CC"
    REPUBLICA_DEMOCRATICA_CONGO = "CD"
    REPUBLICA_CENTRAFRICANA = "CF"
    CONGO = "CG"
    ELVETIA = "CH"
    COTE_D_IVOIRE = "CI"
    INSULELE_COOK = "CK"
    CHILE = "CL"
    CAMERUN = "CM"
    CHINA = "CN"
    COLUMBIA = "CO"
    COSTA_RICA = "CR"
    CUBA = "CU"
    CAPUL_VERDE = "CV"
    CURACAO = "CW"
    INSULA_CHRISTMAS = "CX"
    CIPRU = "CY"
    CEHIA = "CZ"
    GERMANIA = "DE"
    DJIBOUTI = "DJ"
    DANEMARCA = "DK"
    DOMINICA = "DM"
    REPUBLICA_DOMINICANA = "DO"
    ALGERIA = "DZ"
    ECUADOR = "EC"
    ESTONIA = "EE"
    EGIPT = "EG"
    SAHARA_OCCIDENTALA = "EH"
    GRECIA = "EL"
    ERITREEA = "ER"
    SPANIA = "ES"
    ETIOPIA = "ET"
    FINLANDA = "FI"
    FIJI = "FJ"
    INSULELE_FALKLAND = "FK"
    MICRONEZIA = "FM"
    INSULELE_FEROE = "FO"
    FRANTA = "FR"
    GABON = "GA"
    REGATUL_UNIT = "GB"
    GRENADA = "GD"
    GEORGIA = "GE"
    GUYANA_FRANCEZA = "GF"
    GUERNSEY = "GG"
    GHANA = "GH"
    GIBRALTAR = "GI"
    GROENLANDA = "GL"
    GAMBIA = "GM"
    GUINEEA = "GN"
    GUADELUPA = "GP"
    GUINEEA_ECUATORIALA = "GQ"
    GEORGIA_DE_SUD_SI_INSULELE_SANDWICH_DE_SUD = "GS"
    GUATEMALA = "GT"
    GUAM = "GU"
    GUINEEA_BISSAU = "GW"
    GUYANA = "GY"
    HONG_KONG = "HK"
    INSULA_HEARD_SI_INSULELE_MCDONALD = "HM"
    HONDURAS = "HN"
    CROATIA = "HR"
    HAITI = "HT"
    UNGARIA = "HU"
    INDONEZIA = "ID"
    IRLANDA = "IE"
    ISRAEL = "IL"
    INSULA_MAN = "IM"
    INDIA = "IN"
    TERITORIUL_BRITANIC_DIN_OCEANUL_INDIAN = "IO"
    IRAK = "IQ"
    IRAN = "IR"
    ISLANDA = "IS"
    ITALIA = "IT"
    JERSEY = "JE"
    JAMAICA = "JM"
    IORDANIA = "JO"
    JAPONIA = "JP"
    KENYA = "KE"
    KARGAZSTAN = "KG"
    CAMBODGIA = "KH"
    KIRIBATI = "KI"
    COMORE = "KM"
    SAINT_KITTS_SI_NEVIS = "KN"
    COREEA_DE_NORD = "KP"
    COREEA_DE_SUD = "KR"
    KUWEIT = "KW"
    INSULELE_CAYMAN = "KY"
    KAZAHSTAN = "KZ"
    LAOS = "LA"
    LIBAN = "LB"
    SAINT_LUCIA = "LC"
    LIECHTENSTEIN = "LI"
    SRI_LANKA = "LK"
    LIBERIA = "LR"
    LESOTHO = "LS"
    LITUANIA = "LT"
    LUXEMBURG = "LU"
    LETONIA = "LV"
    LIBIA = "LY"
    MAROC = "MA"
    MONACO = "MC"
    MOLDOVA = "MD"
    MUNTENEGRU = "ME"
    SAINT_MARTIN = "MF"
    MADAGASCAR = "MG"
    INSULELE_MARSHALL = "MH"
    MACEDONIA_DE_NORD = "MK"
    MALI = "ML"
    MYANMAR_BIRMANIA = "MM"
    MONGOLIA = "MN"
    MACAO = "MO"
    INSULELE_MARIANE_DE_NORD = "MP"
    MARTINICA = "MQ"
    MAURITANIA = "MR"
    MONTSERRAT = "MS"
    MALTA = "MT"
    MAURITIUS = "MU"
    MALDIVE = "MV"
    MALAWI = "MW"
    MEXIC = "MX"
    MALAYSIA = "MY"
    MOZAMBIC = "MZ"
    NAMIBIA = "NA"
    NOUA_CALEDONIE = "NC"
    NIGER = "NE"
    INSULA_NORFOLK = "NF"
    NIGERIA = "NG"
    NICARAGUA = "NI"
    TARILE_DE_JOS = "NL"
    NORVEGIA = "NO"
    NEPAL = "NP"
    NAURU = "NR"
    NIUE = "NU"
    NOUA_ZEELANDA = "NZ"
    OMAN = "OM"
    PANAMA = "PA"
    PERU = "PE"
    POLINEZIA_FRANCEZA = "PF"
    PAPUA_NOUA_GUINEE = "PG"
    FILIPINE = "PH"
    PAKISTAN = "PK"
    POLONIA = "PL"
    SAINT_PIERRE_SI_MIQUELON = "PM"
    INSULELE_PITCAIRN = "PN"
    PUERTO_RICO = "PR"
    PS = "PS"
    PORTUGALIA = "PT"
    PALAU = "PW"
    PARAGUAY = "PY"
    QATAR = "QA"
    REUNION = "RE"
    ROMANIA = "RO"
    SERBIA = "RS"
    RUSIA = "RU"
    RWANDA = "RW"
    ARABIA_SAUDITA = "SA"
    INSULELE_SOLOMON = "SB"
    SEYCHELLES = "SC"
    SUDAN = "SD"
    SUEDIA = "SE"
    SINGAPORE = "SG"
    SFANTA_ELENA_ASCENSION_SI_TRISTAN_DA_CUNHA = "SH"
    SLOVENIA = "SI"
    SVALBARD_SI_JAN_MAYEN = "SJ"
    SLOVACIA = "SK"
    SIERRA_LEONE = "SL"
    SAN_MARINO = "SM"
    SENEGAL = "SN"
    SOMALIA = "SO"
    SURINAME = "SR"
    SUDANUL_DE_SUD = "SS"
    SAO_TOME_SI_PRINCIPE = "ST"
    EL_SALVADOR = "SV"
    SINT_MAARTEN = "SX"
    SIRIA = "SY"
    ESWATINI = "SZ"
    INSULELE_TURKS_SI_CAICOS = "TC"
    CIAD = "TD"
    TERITORIILE_AUSTRALE_SI_ANTARCTICE_FRANCEZE = "TF"
    TOGO = "TG"
    THAILANDA = "TH"
    TADJIKISTAN = "TJ"
    TOKELAU = "TK"
    TIMORUL_DE_EST = "TL"
    TURKMENISTAN = "TM"
    TUNISIA = "TN"
    TONGA = "TO"
    TURCIA = "TR"
    TRINIDAD_SI_TOBAGO = "TT"
    TUVALU = "TV"
    TAIWAN = "TW"
    TANZANIA = "TZ"
    UCRAINA = "UA"
    UGANDA = "UG"
    INSULELE_MINORE_INDEPARTATE_ALE_STATELOR_UNITE = "UM"
    SUA = "US"
    URUGUAY = "UY"
    UZBEKISTAN = "UZ"
    VATICAN = "VA"
    SAINT_VINCENT_SI_GRENADINELE = "VC"
    VENEZUELA = "VE"
    INSULELE_VIRGINE_BRITANICE = "VG"
    INSULELE_VIRGINE_AMERICANE = "VI"
    VIETNAM = "VN"
    VANUATU = "VU"
    WALLIS_SI_FUTUNA = "WF"
    SAMOA = "WS"
    POSES_SPANIOLE_AFRICA_DE_NORD = "XC"
    IRLANDA_DE_NORD = "XI"
    KOSOVO = "XK"
    MELILA = "XL"
    YEMEN = "YE"
    MAYOTTE = "YT"
    AFRICA_DE_SUD = "ZA"
    ZAMBIA = "ZM"
    ZIMBABWE = "ZW"


class CodTipOperatiuneType(Enum):
    ACHIZITIE_INTRACOMUNITARA = 10  # AIC - Achiziţie intracomunitară
    OPERATIUNI_IN_SISTEM_LOHN_UE_INTRARE = (
        12  # LHI - Operațiuni în sistem lohn (UE) - intrare
    )
    STOCURI_LA_DISPOZITIA_CLIENTULUI_CALL_OFF_STOCK_INTRARE = (
        14  # SCI - Stocuri la dispoziția clientului (Call-off stock) - intrare
    )
    LIVRARE_INTRACOMUNITARA = 20  # LIC - Livrare intracomunitară
    OPERATIUNI_IN_SISTEM_LOHN_UE_IESIRE = (
        22  # LHE - Operațiuni în sistem lohn (UE) - ieșire
    )
    STOCURI_LA_DISPOZITIA_CLIENTULUI_CALL_OFF_STOCK_IESIRE = (
        24  # SCE - Stocuri la dispoziția clientului (Call-off stock) - ieșire
    )
    TRANSPORT_PE_TERITORIUL_NATIONAL = 30  # TTN - Transport pe teritoriul naţional
    IMPORT = 40  # IMP - Import
    EXPORT = 50  # EXP - Export
    TRANZACTIE_INTRACOMUNITARA_INTRARE_PENTRU_DEPOZITARE_FORMARE_NOU_TRANSPORT = 60  # DIN - Tranzacţie intracomunitară - Intrare pentru depozitare/formare nou transport
    TRANZACTIE_INTRACOMUNITARA_IESIRE_DUPA_DEPOZITARE_FORMARE_NOU_TRANSPORT = 70  # DIE - Tranzacţie intracomunitară - Ieşire după depozitare/formare nou transport


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
    CONFIRMAT = 10
    CONFIRMAT_PARTIAL = 20
    INFIRMAT = 30


class TipDocumentType(Enum):
    CMR = 10
    FACTURA = 20
    AVIZ_DE_INSOTIRE_A_MARFII = 30
    ALTELE = 9999


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
