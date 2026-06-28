from pydantic import BaseModel, ConfigDict
from xsdata_pydantic.fields import field

from .ubl_common_basic_components_2_1 import (
    Id,
    Name,
)
from .ubl_extension_content_data_type_2_1 import ExtensionContentType
from .ubl_unqualified_data_types_2_1 import (
    CodeType,
    IdentifierType,
    TextType,
)

__NAMESPACE__ = (
    "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
)


class ExtensionAgencyIdtype(IdentifierType):
    class Meta:
        name = "ExtensionAgencyIDType"

    model_config = ConfigDict(defer_build=True)


class ExtensionAgencyNameType(TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExtensionAgencyUritype(IdentifierType):
    class Meta:
        name = "ExtensionAgencyURIType"

    model_config = ConfigDict(defer_build=True)


class ExtensionContent(ExtensionContentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExtensionReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExtensionReasonType(TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExtensionUritype(IdentifierType):
    class Meta:
        name = "ExtensionURIType"

    model_config = ConfigDict(defer_build=True)


class ExtensionVersionIdtype(IdentifierType):
    class Meta:
        name = "ExtensionVersionIDType"

    model_config = ConfigDict(defer_build=True)


class ExtensionAgencyId(ExtensionAgencyIdtype):
    class Meta:
        name = "ExtensionAgencyID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExtensionAgencyName(ExtensionAgencyNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExtensionAgencyUri(ExtensionAgencyUritype):
    class Meta:
        name = "ExtensionAgencyURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExtensionReason(ExtensionReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExtensionReasonCode(ExtensionReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExtensionUri(ExtensionUritype):
    class Meta:
        name = "ExtensionURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExtensionVersionId(ExtensionVersionIdtype):
    class Meta:
        name = "ExtensionVersionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class UblextensionType(BaseModel):
    """
    A single extension for private use.
    "

    :ivar id: An identifier for the Extension assigned by the creator of
        the extension.
    :ivar name: A name for the Extension assigned by the creator of the
        extension.
    :ivar extension_agency_id: An agency that maintains one or more
        Extensions.
    :ivar extension_agency_name: The name of the agency that maintains
        the Extension.
    :ivar extension_version_id: The version of the Extension.
    :ivar extension_agency_uri: A URI for the Agency that maintains the
        Extension.
    :ivar extension_uri: A URI for the Extension.
    :ivar extension_reason_code: A code for reason the Extension is
        being included.
    :ivar extension_reason: A description of the reason for the
        Extension.
    :ivar extension_content: The definition of the extension content.
    """

    class Meta:
        name = "UBLExtensionType"

    model_config = ConfigDict(defer_build=True)
    id: Id | None = field(
        default=None,
        metadata={
            "name": "ID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    name: Name | None = field(
        default=None,
        metadata={
            "name": "Name",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    extension_agency_id: ExtensionAgencyId | None = field(
        default=None,
        metadata={
            "name": "ExtensionAgencyID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_agency_name: ExtensionAgencyName | None = field(
        default=None,
        metadata={
            "name": "ExtensionAgencyName",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_version_id: ExtensionVersionId | None = field(
        default=None,
        metadata={
            "name": "ExtensionVersionID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_agency_uri: ExtensionAgencyUri | None = field(
        default=None,
        metadata={
            "name": "ExtensionAgencyURI",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_uri: ExtensionUri | None = field(
        default=None,
        metadata={
            "name": "ExtensionURI",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_reason_code: ExtensionReasonCode | None = field(
        default=None,
        metadata={
            "name": "ExtensionReasonCode",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_reason: ExtensionReason | None = field(
        default=None,
        metadata={
            "name": "ExtensionReason",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_content: ExtensionContent = field(
        metadata={
            "name": "ExtensionContent",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "required": True,
        }
    )


class Ublextension(UblextensionType):
    """
    A single extension for private use.
    """

    class Meta:
        name = "UBLExtension"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class UblextensionsType(BaseModel):
    """
    A container for all extensions present in the document.
    "

    :ivar ublextension: A single extension for private use.
    """

    class Meta:
        name = "UBLExtensionsType"

    model_config = ConfigDict(defer_build=True)
    ublextension: list[Ublextension] = field(
        default_factory=list,
        metadata={
            "name": "UBLExtension",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "min_occurs": 1,
        },
    )


class Ublextensions(UblextensionsType):
    """
    A container for all extensions present in the document.
    """

    class Meta:
        name = "UBLExtensions"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        )

    model_config = ConfigDict(defer_build=True)
