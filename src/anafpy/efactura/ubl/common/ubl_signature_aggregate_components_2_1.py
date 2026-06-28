from pydantic import BaseModel, ConfigDict
from xsdata_pydantic.fields import field

from .ubl_common_basic_components_2_1 import Id
from .ubl_signature_basic_components_2_1 import ReferencedSignatureId
from .ubl_xmldsig_core_schema_2_1 import Signature

__NAMESPACE__ = (
    "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2"
)


class SignatureInformationType(BaseModel):
    """<ns1:Component xmlns:ns1="urn:un:unece:uncefact:documentation:2">
    <ns1:ComponentType>ABIE</ns1:ComponentType> <ns1:DictionaryEntryName>Signature
    Information.

    Details</ns1:DictionaryEntryName> <ns1:Definition>This class
    captures a single signature and optionally associates to a signature
    in the document with the corresponding identifier.</ns1:Definition>
    <ns1:ObjectClass>Signature Information</ns1:ObjectClass>
    </ns1:Component>
    "

    :ivar id: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Signature Information.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition>This
        specifies the identifier of the signature distinguishing it from
        other signatures.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Signature Information</ns1:ObjectClass>
        <ns1:PropertyTerm>Identifier</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Identifier</ns1:RepresentationTerm>
        <ns1:DataType>Identifier. Type</ns1:DataType> </ns1:Component>
    :ivar referenced_signature_id: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Signature Information. Referenced
        Signature Identifier. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition>This associates this signature with the
        identifier of a signature business object in the
        document.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Signature Information</ns1:ObjectClass>
        <ns1:PropertyTerm>Referenced Signature
        Identifier</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Identifier</ns1:RepresentationTerm>
        <ns1:DataType>Identifier. Type</ns1:DataType> </ns1:Component>
    :ivar signature: This is a single digital signature as defined by
        the W3C specification.
    """

    model_config = ConfigDict(defer_build=True)
    id: Id | None = field(
        default=None,
        metadata={
            "name": "ID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    referenced_signature_id: ReferencedSignatureId | None = field(
        default=None,
        metadata={
            "name": "ReferencedSignatureID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2",
        },
    )
    signature: Signature | None = field(
        default=None,
        metadata={
            "name": "Signature",
            "type": "Element",
            "namespace": "http://www.w3.org/2000/09/xmldsig#",
        },
    )


class SignatureInformation(SignatureInformationType):
    class Meta:
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2"

    model_config = ConfigDict(defer_build=True)
