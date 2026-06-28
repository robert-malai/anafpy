from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from xsdata_pydantic.fields import field

__NAMESPACE__ = (
    "urn:un:unece:uncefact:data:specification:CoreComponentTypeSchemaModule:2"
)


class AmountType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000001</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Amount.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A number of monetary units specified in a currency where the unit of the currency is explicit or implied.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Amount</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">decimal</ns1:PrimitiveType>
    "

    :ivar value:
    :ivar currency_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000001-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Amount
        Currency. Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The currency
        of the amount.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Amount
        Currency</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
        <ns1:UsageRule
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Reference
        UNECE Rec 9, using 3-letter alphabetic codes.</ns1:UsageRule>
    :ivar currency_code_list_version_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000001-SC3</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Amount
        Currency. Code List Version.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The VersionID
        of the UN/ECE Rec9 code list.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Amount
        Currency</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List
        Version</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: Decimal = field(
        metadata={
            "required": True,
        }
    )
    currency_id: str | None = field(
        default=None,
        metadata={
            "name": "currencyID",
            "type": "Attribute",
        },
    )
    currency_code_list_version_id: str | None = field(
        default=None,
        metadata={
            "name": "currencyCodeListVersionID",
            "type": "Attribute",
        },
    )


class BinaryObjectType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000002</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary Object.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A set of finite-length sequences of binary octets.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary Object</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">binary</ns1:PrimitiveType>
    "

    :ivar value:
    :ivar format: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000002-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary Object.
        Format. Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The format of
        the binary content.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary
        Object</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Format</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar mime_code: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000002-SC3</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary Object.
        Mime. Code</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The mime type
        of the binary object.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary
        Object</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Mime</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar encoding_code: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000002-SC4</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary Object.
        Encoding. Code</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Specifies the
        decoding algorithm of the binary object.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary
        Object</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Encoding</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar character_set_code: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000002-SC5</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary Object.
        Character Set. Code</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The character
        set of the binary object if the mime type is
        text.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary
        Object</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Character
        Set</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar uri: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000002-SC6</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary Object.
        Uniform Resource. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The Uniform
        Resource Identifier that identifies where the binary object is
        located.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary
        Object</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Uniform
        Resource Identifier</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar filename: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000002-SC7</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary Object.
        Filename.Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The filename
        of the binary object.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Binary
        Object</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Filename</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: bytes = field(
        metadata={
            "required": True,
            "format": "base64",
        }
    )
    format: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )
    mime_code: str | None = field(
        default=None,
        metadata={
            "name": "mimeCode",
            "type": "Attribute",
        },
    )
    encoding_code: str | None = field(
        default=None,
        metadata={
            "name": "encodingCode",
            "type": "Attribute",
        },
    )
    character_set_code: str | None = field(
        default=None,
        metadata={
            "name": "characterSetCode",
            "type": "Attribute",
        },
    )
    uri: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )
    filename: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )


class CodeType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A character string (letters, figures, or symbols) that for brevity and/or languange independence may be used to represent or replace a definitive value or text of an attribute together with relevant supplementary information.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    <ns1:UsageRule xmlns:ns1="urn:un:unece:uncefact:documentation:2">Should not be used if the character string identifies an instance of an object class or an object in the real world, in which case the Identifier. Type should be used.</ns1:UsageRule>
    "

    :ivar value:
    :ivar list_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The
        identification of a list of codes.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code
        List</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar list_agency_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC3</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List.
        Agency. Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">An agency that
        maintains one or more lists of codes.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code
        List</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Agency</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
        <ns1:UsageRule
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Defaults to
        the UN/EDIFACT data element 3055 code list.</ns1:UsageRule>
    :ivar list_agency_name: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC4</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List.
        Agency Name. Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The name of
        the agency that maintains the list of codes.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code
        List</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Agency
        Name</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar list_name: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC5</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List.
        Name. Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The name of a
        list of codes.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code
        List</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Name</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar list_version_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC6</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List.
        Version. Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The version of
        the list of codes.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code
        List</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Version</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar name: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC7</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code. Name.
        Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The textual
        equivalent of the code content component.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code</ns1:ObjectClass>
        <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Name</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar language_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC8</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Language.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The identifier
        of the language used in the code name.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Language</ns1:ObjectClass>
        <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar list_uri: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC9</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List.
        Uniform Resource. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The Uniform
        Resource Identifier that identifies where the code list is
        located.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code
        List</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Uniform
        Resource Identifier</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar list_scheme_uri: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000007-SC10</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List
        Scheme. Uniform Resource. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The Uniform
        Resource Identifier that identifies where the code list scheme
        is located.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List
        Scheme</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Uniform
        Resource Identifier</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )
    list_id: str | None = field(
        default=None,
        metadata={
            "name": "listID",
            "type": "Attribute",
        },
    )
    list_agency_id: str | None = field(
        default=None,
        metadata={
            "name": "listAgencyID",
            "type": "Attribute",
        },
    )
    list_agency_name: str | None = field(
        default=None,
        metadata={
            "name": "listAgencyName",
            "type": "Attribute",
        },
    )
    list_name: str | None = field(
        default=None,
        metadata={
            "name": "listName",
            "type": "Attribute",
        },
    )
    list_version_id: str | None = field(
        default=None,
        metadata={
            "name": "listVersionID",
            "type": "Attribute",
        },
    )
    name: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )
    language_id: str | None = field(
        default=None,
        metadata={
            "name": "languageID",
            "type": "Attribute",
        },
    )
    list_uri: str | None = field(
        default=None,
        metadata={
            "name": "listURI",
            "type": "Attribute",
        },
    )
    list_scheme_uri: str | None = field(
        default=None,
        metadata={
            "name": "listSchemeURI",
            "type": "Attribute",
        },
    )


class DateTimeType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000008</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Date
    Time.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A particular point in the progression of time together with the relevant supplementary information.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Date Time</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    <ns1:UsageRule xmlns:ns1="urn:un:unece:uncefact:documentation:2">Can be used for a date and/or time.</ns1:UsageRule>
    "

    :ivar value:
    :ivar format: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000008-SC1</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Date Time.
        Format. Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The format of
        the date time content</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Date
        Time</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Format</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )
    format: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )


class IdentifierType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000011</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A character string to identify and distinguish uniquely, one instance of an object in an identification scheme from all other objects in the same scheme together with relevant supplementary information.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    "

    :ivar value:
    :ivar scheme_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000011-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme. Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The
        identification of the identification scheme.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar scheme_name: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000011-SC3</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme. Name. Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The name of
        the identification scheme.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Name</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar scheme_agency_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000011-SC4</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme Agency. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The
        identification of the agency that maintains the identification
        scheme.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme Agency</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
        <ns1:UsageRule
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Defaults to
        the UN/EDIFACT data element 3055 code list.</ns1:UsageRule>
    :ivar scheme_agency_name: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000011-SC5</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme Agency. Name. Text</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The name of
        the agency that maintains the identification
        scheme.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme Agency</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Agency
        Name</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar scheme_version_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000011-SC6</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme. Version. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The version of
        the identification scheme.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Version</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar scheme_data_uri: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000011-SC7</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme Data. Uniform Resource.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The Uniform
        Resource Identifier that identifies where the identification
        scheme data is located.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme Data</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Uniform
        Resource Identifier</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar scheme_uri: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000011-SC8</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme. Uniform Resource. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The Uniform
        Resource Identifier that identifies where the identification
        scheme is located.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification
        Scheme</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Uniform
        Resource Identifier</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )
    scheme_id: str | None = field(
        default=None,
        metadata={
            "name": "schemeID",
            "type": "Attribute",
        },
    )
    scheme_name: str | None = field(
        default=None,
        metadata={
            "name": "schemeName",
            "type": "Attribute",
        },
    )
    scheme_agency_id: str | None = field(
        default=None,
        metadata={
            "name": "schemeAgencyID",
            "type": "Attribute",
        },
    )
    scheme_agency_name: str | None = field(
        default=None,
        metadata={
            "name": "schemeAgencyName",
            "type": "Attribute",
        },
    )
    scheme_version_id: str | None = field(
        default=None,
        metadata={
            "name": "schemeVersionID",
            "type": "Attribute",
        },
    )
    scheme_data_uri: str | None = field(
        default=None,
        metadata={
            "name": "schemeDataURI",
            "type": "Attribute",
        },
    )
    scheme_uri: str | None = field(
        default=None,
        metadata={
            "name": "schemeURI",
            "type": "Attribute",
        },
    )


class IndicatorType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000012</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Indicator.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A list of two mutually exclusive Boolean values that express the only possible states of a Property.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Indicator</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    "

    :ivar value:
    :ivar format: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000012-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Indicator.
        Format. Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Whether the
        indicator is numeric, textual or binary.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Indicator</ns1:ObjectClass>
        <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Format</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )
    format: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )


class MeasureType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000013</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Measure.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A numeric value determined by measuring an object along with the specified unit of measure.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Measure</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">decimal</ns1:PrimitiveType>
    "

    :ivar value:
    :ivar unit_code: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000013-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Measure Unit.
        Code</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The type of
        unit of measure.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Measure
        Unit</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
        <ns1:UsageRule
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Reference
        UNECE Rec. 20 and X12 355</ns1:UsageRule>
    :ivar unit_code_list_version_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000013-SC3</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Measure Unit.
        Code List Version. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The version of
        the measure unit code list.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Measure
        Unit</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List
        Version</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: Decimal = field(
        metadata={
            "required": True,
        }
    )
    unit_code: str | None = field(
        default=None,
        metadata={
            "name": "unitCode",
            "type": "Attribute",
        },
    )
    unit_code_list_version_id: str | None = field(
        default=None,
        metadata={
            "name": "unitCodeListVersionID",
            "type": "Attribute",
        },
    )


class NumericType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000014</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Numeric.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">Numeric information that is assigned or is determined by calculation, counting, or sequencing. It does not require a unit of quantity or unit of measure.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Numeric</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    "

    :ivar value:
    :ivar format: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000014-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Numeric.
        Format. Text</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Whether the
        number is an integer, decimal, real number or
        percentage.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Numeric</ns1:ObjectClass>
        <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Format</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: Decimal = field(
        metadata={
            "required": True,
        }
    )
    format: str | None = field(
        default=None,
        metadata={
            "type": "Attribute",
        },
    )


class QuantityType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000018</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A counted number of non-monetary units possibly including fractions.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">decimal</ns1:PrimitiveType>
    "

    :ivar value:
    :ivar unit_code: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000018-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity.
        Unit. Code</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The unit of
        the quantity</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity</ns1:ObjectClass>
        <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Unit
        Code</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar unit_code_list_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000018-SC3</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity Unit.
        Code List. Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The quantity
        unit code list.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity
        Unit</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code
        List</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar unit_code_list_agency_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000018-SC4</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity Unit.
        Code List Agency. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The
        identification of the agency that maintains the quantity unit
        code list</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity
        Unit</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List
        Agency</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
        <ns1:UsageRule
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Defaults to
        the UN/EDIFACT data element 3055 code list.</ns1:UsageRule>
    :ivar unit_code_list_agency_name: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000018-SC5</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity Unit.
        Code List Agency Name. Text</ns1:DictionaryEntryName>
        <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The name of
        the agency which maintains the quantity unit code
        list.</ns1:Definition> <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Quantity
        Unit</ns1:ObjectClass> <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Code List
        Agency Name</ns1:PropertyTermName> <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: Decimal = field(
        metadata={
            "required": True,
        }
    )
    unit_code: str | None = field(
        default=None,
        metadata={
            "name": "unitCode",
            "type": "Attribute",
        },
    )
    unit_code_list_id: str | None = field(
        default=None,
        metadata={
            "name": "unitCodeListID",
            "type": "Attribute",
        },
    )
    unit_code_list_agency_id: str | None = field(
        default=None,
        metadata={
            "name": "unitCodeListAgencyID",
            "type": "Attribute",
        },
    )
    unit_code_list_agency_name: str | None = field(
        default=None,
        metadata={
            "name": "unitCodeListAgencyName",
            "type": "Attribute",
        },
    )


class TextType(BaseModel):
    """<ns1:UniqueID
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000019</ns1:UniqueID>
    <ns1:CategoryCode
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">CCT</ns1:CategoryCode>
    <ns1:DictionaryEntryName
    xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text.

    Type</ns1:DictionaryEntryName>
    <ns1:VersionID xmlns:ns1="urn:un:unece:uncefact:documentation:2">1.0</ns1:VersionID>
    <ns1:Definition xmlns:ns1="urn:un:unece:uncefact:documentation:2">A character string (i.e. a finite set of characters) generally in the form of words of a language.</ns1:Definition>
    <ns1:RepresentationTermName xmlns:ns1="urn:un:unece:uncefact:documentation:2">Text</ns1:RepresentationTermName>
    <ns1:PrimitiveType xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    "

    :ivar value:
    :ivar language_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000019-SC2</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Language.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The identifier
        of the language used in the content component.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Language</ns1:ObjectClass>
        <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identification</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    :ivar language_locale_id: <ns1:UniqueID
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">UNDT000019-SC3</ns1:UniqueID>
        <ns1:CategoryCode
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">SC</ns1:CategoryCode>
        <ns1:DictionaryEntryName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2"> Language.
        Locale. Identifier</ns1:DictionaryEntryName> <ns1:Definition
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">The
        identification of the locale of the language.</ns1:Definition>
        <ns1:ObjectClass
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Language</ns1:ObjectClass>
        <ns1:PropertyTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Locale</ns1:PropertyTermName>
        <ns1:RepresentationTermName
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">Identifier</ns1:RepresentationTermName>
        <ns1:PrimitiveType
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">string</ns1:PrimitiveType>
    """

    model_config = ConfigDict(defer_build=True)
    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )
    language_id: str | None = field(
        default=None,
        metadata={
            "name": "languageID",
            "type": "Attribute",
        },
    )
    language_locale_id: str | None = field(
        default=None,
        metadata={
            "name": "languageLocaleID",
            "type": "Attribute",
        },
    )
