from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict
from xsdata.models.datatype import XmlDateTime
from xsdata_pydantic.fields import field

from .ubl_xmldsig_core_schema_2_1 import (
    CanonicalizationMethod,
    DigestMethod,
    DigestValue,
    Signature,
    Transforms,
    X509IssuerSerialType,
)

__NAMESPACE__ = "http://uri.etsi.org/01903/v1.3.2#"


class AnyType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    any_attributes: dict[str, str] = field(
        default_factory=dict,
        metadata={
            "type": "Attributes",
            "namespace": "##any",
        },
    )
    content: list[object] = field(
        default_factory=list,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
            "mixed": True,
        },
    )


class CrlidentifierType(BaseModel):
    class Meta:
        name = "CRLIdentifierType"

    model_config = ConfigDict(defer_build=True)
    issuer: str = field(
        metadata={
            "name": "Issuer",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    issue_time: XmlDateTime = field(
        metadata={
            "name": "IssueTime",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    number: int | None = field(
        default=None,
        metadata={
            "name": "Number",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    uri: str | None = field(
        default=None,
        metadata={
            "name": "URI",
            "type": "Attribute",
        },
    )


class DocumentationReferencesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    documentation_reference: list[str] = field(
        default_factory=list,
        metadata={
            "name": "DocumentationReference",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class EncapsulatedPkidataType(BaseModel):
    class Meta:
        name = "EncapsulatedPKIDataType"

    model_config = ConfigDict(defer_build=True)
    value: bytes = field(
        metadata={
            "required": True,
            "format": "base64",
        }
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )
    encoding: str | None = field(
        default=None,
        metadata={
            "name": "Encoding",
            "type": "Attribute",
        },
    )


class IncludeType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    uri: str = field(
        metadata={
            "name": "URI",
            "type": "Attribute",
            "required": True,
        }
    )
    referenced_data: bool | None = field(
        default=None,
        metadata={
            "name": "referencedData",
            "type": "Attribute",
        },
    )


class IntegerListType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    int_value: list[int] = field(
        default_factory=list,
        metadata={
            "name": "int",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class QualifierType(Enum):
    OIDAS_URI = "OIDAsURI"
    OIDAS_URN = "OIDAsURN"


class QualifyingPropertiesReferenceType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    uri: str = field(
        metadata={
            "name": "URI",
            "type": "Attribute",
            "required": True,
        }
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class ResponderIdtype(BaseModel):
    class Meta:
        name = "ResponderIDType"

    model_config = ConfigDict(defer_build=True)
    by_name: str | None = field(
        default=None,
        metadata={
            "name": "ByName",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    by_key: bytes | None = field(
        default=None,
        metadata={
            "name": "ByKey",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "format": "base64",
        },
    )


class Spuri(BaseModel):
    class Meta:
        name = "SPURI"
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)
    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )


class SignatureProductionPlaceType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    city: str | None = field(
        default=None,
        metadata={
            "name": "City",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    state_or_province: str | None = field(
        default=None,
        metadata={
            "name": "StateOrProvince",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    postal_code: str | None = field(
        default=None,
        metadata={
            "name": "PostalCode",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    country_name: str | None = field(
        default=None,
        metadata={
            "name": "CountryName",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class SigningTime(BaseModel):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)
    value: XmlDateTime = field(
        metadata={
            "required": True,
        }
    )


class AnyType(AnyType):
    class Meta:
        name = "Any"
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class CrlvaluesType(BaseModel):
    class Meta:
        name = "CRLValuesType"

    model_config = ConfigDict(defer_build=True)
    encapsulated_crlvalue: list[EncapsulatedPkidataType] = field(
        default_factory=list,
        metadata={
            "name": "EncapsulatedCRLValue",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class CertificateValuesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    encapsulated_x509_certificate: list[EncapsulatedPkidataType] = field(
        default_factory=list,
        metadata={
            "name": "EncapsulatedX509Certificate",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    other_certificate: list[AnyType] = field(
        default_factory=list,
        metadata={
            "name": "OtherCertificate",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class CertifiedRolesListType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    certified_role: list[EncapsulatedPkidataType] = field(
        default_factory=list,
        metadata={
            "name": "CertifiedRole",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class ClaimedRolesListType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    claimed_role: list[AnyType] = field(
        default_factory=list,
        metadata={
            "name": "ClaimedRole",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class CommitmentTypeQualifiersListType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    commitment_type_qualifier: list[AnyType] = field(
        default_factory=list,
        metadata={
            "name": "CommitmentTypeQualifier",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class CounterSignatureType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    signature: Signature = field(
        metadata={
            "name": "Signature",
            "type": "Element",
            "namespace": "http://www.w3.org/2000/09/xmldsig#",
            "required": True,
        }
    )


class DigestAlgAndValueType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    digest_method: DigestMethod = field(
        metadata={
            "name": "DigestMethod",
            "type": "Element",
            "namespace": "http://www.w3.org/2000/09/xmldsig#",
            "required": True,
        }
    )
    digest_value: DigestValue = field(
        metadata={
            "name": "DigestValue",
            "type": "Element",
            "namespace": "http://www.w3.org/2000/09/xmldsig#",
            "required": True,
        }
    )


class EncapsulatedPkidata(EncapsulatedPkidataType):
    class Meta:
        name = "EncapsulatedPKIData"
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class IdentifierType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )
    qualifier: QualifierType | None = field(
        default=None,
        metadata={
            "name": "Qualifier",
            "type": "Attribute",
        },
    )


class Include(IncludeType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class NoticeReferenceType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    organization: str = field(
        metadata={
            "name": "Organization",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    notice_numbers: IntegerListType = field(
        metadata={
            "name": "NoticeNumbers",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )


class OcspidentifierType(BaseModel):
    class Meta:
        name = "OCSPIdentifierType"

    model_config = ConfigDict(defer_build=True)
    responder_id: ResponderIdtype = field(
        metadata={
            "name": "ResponderID",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    produced_at: XmlDateTime = field(
        metadata={
            "name": "ProducedAt",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    uri: str | None = field(
        default=None,
        metadata={
            "name": "URI",
            "type": "Attribute",
        },
    )


class OcspvaluesType(BaseModel):
    class Meta:
        name = "OCSPValuesType"

    model_config = ConfigDict(defer_build=True)
    encapsulated_ocspvalue: list[EncapsulatedPkidataType] = field(
        default_factory=list,
        metadata={
            "name": "EncapsulatedOCSPValue",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class OtherCertStatusRefsType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    other_ref: list[AnyType] = field(
        default_factory=list,
        metadata={
            "name": "OtherRef",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class OtherCertStatusValuesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    other_value: list[AnyType] = field(
        default_factory=list,
        metadata={
            "name": "OtherValue",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class QualifyingPropertiesReference(QualifyingPropertiesReferenceType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class ReferenceInfoType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    digest_method: DigestMethod = field(
        metadata={
            "name": "DigestMethod",
            "type": "Element",
            "namespace": "http://www.w3.org/2000/09/xmldsig#",
            "required": True,
        }
    )
    digest_value: DigestValue = field(
        metadata={
            "name": "DigestValue",
            "type": "Element",
            "namespace": "http://www.w3.org/2000/09/xmldsig#",
            "required": True,
        }
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )
    uri: str | None = field(
        default=None,
        metadata={
            "name": "URI",
            "type": "Attribute",
        },
    )


class SigPolicyQualifiersListType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    sig_policy_qualifier: list[AnyType] = field(
        default_factory=list,
        metadata={
            "name": "SigPolicyQualifier",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class SignatureProductionPlace(SignatureProductionPlaceType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class UnsignedDataObjectPropertiesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    unsigned_data_object_property: list[AnyType] = field(
        default_factory=list,
        metadata={
            "name": "UnsignedDataObjectProperty",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class AttrAuthoritiesCertValues(CertificateValuesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class CrlrefType(BaseModel):
    class Meta:
        name = "CRLRefType"

    model_config = ConfigDict(defer_build=True)
    digest_alg_and_value: DigestAlgAndValueType = field(
        metadata={
            "name": "DigestAlgAndValue",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    crlidentifier: CrlidentifierType | None = field(
        default=None,
        metadata={
            "name": "CRLIdentifier",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class CertIdtype(BaseModel):
    class Meta:
        name = "CertIDType"

    model_config = ConfigDict(defer_build=True)
    cert_digest: DigestAlgAndValueType = field(
        metadata={
            "name": "CertDigest",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    issuer_serial: X509IssuerSerialType = field(
        metadata={
            "name": "IssuerSerial",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    uri: str | None = field(
        default=None,
        metadata={
            "name": "URI",
            "type": "Attribute",
        },
    )


class CertificateValues(CertificateValuesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class CounterSignature(CounterSignatureType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class OcsprefType(BaseModel):
    class Meta:
        name = "OCSPRefType"

    model_config = ConfigDict(defer_build=True)
    ocspidentifier: OcspidentifierType = field(
        metadata={
            "name": "OCSPIdentifier",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    digest_alg_and_value: DigestAlgAndValueType | None = field(
        default=None,
        metadata={
            "name": "DigestAlgAndValue",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class ObjectIdentifierType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    identifier: IdentifierType = field(
        metadata={
            "name": "Identifier",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    description: str | None = field(
        default=None,
        metadata={
            "name": "Description",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    documentation_references: DocumentationReferencesType | None = field(
        default=None,
        metadata={
            "name": "DocumentationReferences",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class ReferenceInfo(ReferenceInfoType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class RevocationValuesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    crlvalues: CrlvaluesType | None = field(
        default=None,
        metadata={
            "name": "CRLValues",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    ocspvalues: OcspvaluesType | None = field(
        default=None,
        metadata={
            "name": "OCSPValues",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    other_values: OtherCertStatusValuesType | None = field(
        default=None,
        metadata={
            "name": "OtherValues",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class SpuserNoticeType(BaseModel):
    class Meta:
        name = "SPUserNoticeType"

    model_config = ConfigDict(defer_build=True)
    notice_ref: NoticeReferenceType | None = field(
        default=None,
        metadata={
            "name": "NoticeRef",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    explicit_text: str | None = field(
        default=None,
        metadata={
            "name": "ExplicitText",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class SignerRoleType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    claimed_roles: ClaimedRolesListType | None = field(
        default=None,
        metadata={
            "name": "ClaimedRoles",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    certified_roles: CertifiedRolesListType | None = field(
        default=None,
        metadata={
            "name": "CertifiedRoles",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class UnsignedDataObjectProperties(UnsignedDataObjectPropertiesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class AttributeRevocationValues(RevocationValuesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class CrlrefsType(BaseModel):
    class Meta:
        name = "CRLRefsType"

    model_config = ConfigDict(defer_build=True)
    crlref: list[CrlrefType] = field(
        default_factory=list,
        metadata={
            "name": "CRLRef",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class CertIdlistType(BaseModel):
    class Meta:
        name = "CertIDListType"

    model_config = ConfigDict(defer_build=True)
    cert: list[CertIdtype] = field(
        default_factory=list,
        metadata={
            "name": "Cert",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class CommitmentTypeIndicationType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    commitment_type_id: ObjectIdentifierType = field(
        metadata={
            "name": "CommitmentTypeId",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    object_reference: list[str] = field(
        default_factory=list,
        metadata={
            "name": "ObjectReference",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    all_signed_data_objects: object | None = field(
        default=None,
        metadata={
            "name": "AllSignedDataObjects",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    commitment_type_qualifiers: CommitmentTypeQualifiersListType | None = field(
        default=None,
        metadata={
            "name": "CommitmentTypeQualifiers",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class DataObjectFormatType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    description: str | None = field(
        default=None,
        metadata={
            "name": "Description",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    object_identifier: ObjectIdentifierType | None = field(
        default=None,
        metadata={
            "name": "ObjectIdentifier",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    mime_type: str | None = field(
        default=None,
        metadata={
            "name": "MimeType",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    encoding: str | None = field(
        default=None,
        metadata={
            "name": "Encoding",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    object_reference: str = field(
        metadata={
            "name": "ObjectReference",
            "type": "Attribute",
            "required": True,
        }
    )


class GenericTimeStampType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    include: list[Include] = field(
        default_factory=list,
        metadata={
            "name": "Include",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    reference_info: list[ReferenceInfo] = field(
        default_factory=list,
        metadata={
            "name": "ReferenceInfo",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    canonicalization_method: CanonicalizationMethod | None = field(
        default=None,
        metadata={
            "name": "CanonicalizationMethod",
            "type": "Element",
            "namespace": "http://www.w3.org/2000/09/xmldsig#",
        },
    )
    encapsulated_time_stamp: list[EncapsulatedPkidataType] = field(
        default_factory=list,
        metadata={
            "name": "EncapsulatedTimeStamp",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    xmltime_stamp: list[AnyType] = field(
        default_factory=list,
        metadata={
            "name": "XMLTimeStamp",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class OcsprefsType(BaseModel):
    class Meta:
        name = "OCSPRefsType"

    model_config = ConfigDict(defer_build=True)
    ocspref: list[OcsprefType] = field(
        default_factory=list,
        metadata={
            "name": "OCSPRef",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class ObjectIdentifier(ObjectIdentifierType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class RevocationValues(RevocationValuesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class SpuserNotice(SpuserNoticeType):
    class Meta:
        name = "SPUserNotice"
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class SignaturePolicyIdType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    sig_policy_id: ObjectIdentifierType = field(
        metadata={
            "name": "SigPolicyId",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    transforms: Transforms | None = field(
        default=None,
        metadata={
            "name": "Transforms",
            "type": "Element",
            "namespace": "http://www.w3.org/2000/09/xmldsig#",
        },
    )
    sig_policy_hash: DigestAlgAndValueType = field(
        metadata={
            "name": "SigPolicyHash",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    sig_policy_qualifiers: SigPolicyQualifiersListType | None = field(
        default=None,
        metadata={
            "name": "SigPolicyQualifiers",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class SignerRole(SignerRoleType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class CommitmentTypeIndication(CommitmentTypeIndicationType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class CompleteCertificateRefsType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    cert_refs: CertIdlistType = field(
        metadata={
            "name": "CertRefs",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "required": True,
        }
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class CompleteRevocationRefsType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    crlrefs: CrlrefsType | None = field(
        default=None,
        metadata={
            "name": "CRLRefs",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    ocsprefs: OcsprefsType | None = field(
        default=None,
        metadata={
            "name": "OCSPRefs",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    other_refs: OtherCertStatusRefsType | None = field(
        default=None,
        metadata={
            "name": "OtherRefs",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class DataObjectFormat(DataObjectFormatType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class OtherTimeStampType(GenericTimeStampType):
    model_config = ConfigDict(defer_build=True)
    include: Any = field(
        exclude=True,
        default=None,
        metadata={
            "type": "Ignore",
        },
    )
    reference_info: list[ReferenceInfo] = field(
        default_factory=list,
        metadata={
            "name": "ReferenceInfo",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
            "min_occurs": 1,
        },
    )


class SignaturePolicyIdentifierType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    signature_policy_id: SignaturePolicyIdType | None = field(
        default=None,
        metadata={
            "name": "SignaturePolicyId",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    signature_policy_implied: object | None = field(
        default=None,
        metadata={
            "name": "SignaturePolicyImplied",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )


class SigningCertificate(CertIdlistType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class XadEstimeStampType(GenericTimeStampType):
    class Meta:
        name = "XAdESTimeStampType"

    model_config = ConfigDict(defer_build=True)
    reference_info: Any = field(
        exclude=True,
        default=None,
        metadata={
            "type": "Ignore",
        },
    )


class AllDataObjectsTimeStamp(XadEstimeStampType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class ArchiveTimeStamp(XadEstimeStampType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class AttributeCertificateRefs(CompleteCertificateRefsType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class AttributeRevocationRefs(CompleteRevocationRefsType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class CompleteCertificateRefs(CompleteCertificateRefsType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class CompleteRevocationRefs(CompleteRevocationRefsType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class IndividualDataObjectsTimeStamp(XadEstimeStampType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class OtherTimeStamp(OtherTimeStampType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class RefsOnlyTimeStamp(XadEstimeStampType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class SigAndRefsTimeStamp(XadEstimeStampType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class SignaturePolicyIdentifier(SignaturePolicyIdentifierType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class SignatureTimeStamp(XadEstimeStampType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class SignedDataObjectPropertiesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    data_object_format: list[DataObjectFormatType] = field(
        default_factory=list,
        metadata={
            "name": "DataObjectFormat",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    commitment_type_indication: list[CommitmentTypeIndicationType] = field(
        default_factory=list,
        metadata={
            "name": "CommitmentTypeIndication",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    all_data_objects_time_stamp: list[XadEstimeStampType] = field(
        default_factory=list,
        metadata={
            "name": "AllDataObjectsTimeStamp",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    individual_data_objects_time_stamp: list[XadEstimeStampType] = field(
        default_factory=list,
        metadata={
            "name": "IndividualDataObjectsTimeStamp",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class SignedSignaturePropertiesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    signing_time: XmlDateTime | None = field(
        default=None,
        metadata={
            "name": "SigningTime",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    signing_certificate: CertIdlistType | None = field(
        default=None,
        metadata={
            "name": "SigningCertificate",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    signature_policy_identifier: SignaturePolicyIdentifierType | None = field(
        default=None,
        metadata={
            "name": "SignaturePolicyIdentifier",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    signature_production_place: SignatureProductionPlaceType | None = field(
        default=None,
        metadata={
            "name": "SignatureProductionPlace",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    signer_role: SignerRoleType | None = field(
        default=None,
        metadata={
            "name": "SignerRole",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class UnsignedSignaturePropertiesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    counter_signature: list[CounterSignatureType] = field(
        default_factory=list,
        metadata={
            "name": "CounterSignature",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    signature_time_stamp: list[XadEstimeStampType] = field(
        default_factory=list,
        metadata={
            "name": "SignatureTimeStamp",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    complete_certificate_refs: list[CompleteCertificateRefsType] = field(
        default_factory=list,
        metadata={
            "name": "CompleteCertificateRefs",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    complete_revocation_refs: list[CompleteRevocationRefsType] = field(
        default_factory=list,
        metadata={
            "name": "CompleteRevocationRefs",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    attribute_certificate_refs: list[CompleteCertificateRefsType] = field(
        default_factory=list,
        metadata={
            "name": "AttributeCertificateRefs",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    attribute_revocation_refs: list[CompleteRevocationRefsType] = field(
        default_factory=list,
        metadata={
            "name": "AttributeRevocationRefs",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    sig_and_refs_time_stamp: list[XadEstimeStampType] = field(
        default_factory=list,
        metadata={
            "name": "SigAndRefsTimeStamp",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    refs_only_time_stamp: list[XadEstimeStampType] = field(
        default_factory=list,
        metadata={
            "name": "RefsOnlyTimeStamp",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    certificate_values: list[CertificateValuesType] = field(
        default_factory=list,
        metadata={
            "name": "CertificateValues",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    revocation_values: list[RevocationValuesType] = field(
        default_factory=list,
        metadata={
            "name": "RevocationValues",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    attr_authorities_cert_values: list[CertificateValuesType] = field(
        default_factory=list,
        metadata={
            "name": "AttrAuthoritiesCertValues",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    attribute_revocation_values: list[RevocationValuesType] = field(
        default_factory=list,
        metadata={
            "name": "AttributeRevocationValues",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    archive_time_stamp: list[XadEstimeStampType] = field(
        default_factory=list,
        metadata={
            "name": "ArchiveTimeStamp",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    other_element: list[object] = field(
        default_factory=list,
        metadata={
            "type": "Wildcard",
            "namespace": "##other",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class XadEstimeStamp(XadEstimeStampType):
    class Meta:
        name = "XAdESTimeStamp"
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class SignedDataObjectProperties(SignedDataObjectPropertiesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class SignedPropertiesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    signed_signature_properties: SignedSignaturePropertiesType | None = field(
        default=None,
        metadata={
            "name": "SignedSignatureProperties",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    signed_data_object_properties: SignedDataObjectPropertiesType | None = field(
        default=None,
        metadata={
            "name": "SignedDataObjectProperties",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class SignedSignatureProperties(SignedSignaturePropertiesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class UnsignedPropertiesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    unsigned_signature_properties: UnsignedSignaturePropertiesType | None = field(
        default=None,
        metadata={
            "name": "UnsignedSignatureProperties",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    unsigned_data_object_properties: UnsignedDataObjectPropertiesType | None = field(
        default=None,
        metadata={
            "name": "UnsignedDataObjectProperties",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class UnsignedSignatureProperties(UnsignedSignaturePropertiesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class QualifyingPropertiesType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    signed_properties: SignedPropertiesType | None = field(
        default=None,
        metadata={
            "name": "SignedProperties",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    unsigned_properties: UnsignedPropertiesType | None = field(
        default=None,
        metadata={
            "name": "UnsignedProperties",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    target: str = field(
        metadata={
            "name": "Target",
            "type": "Attribute",
            "required": True,
        }
    )
    id: str | None = field(
        default=None,
        metadata={
            "name": "Id",
            "type": "Attribute",
        },
    )


class SignedProperties(SignedPropertiesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class UnsignedProperties(UnsignedPropertiesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)


class QualifyingProperties(QualifyingPropertiesType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.3.2#"

    model_config = ConfigDict(defer_build=True)
