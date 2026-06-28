from pydantic import BaseModel, ConfigDict
from xsdata_pydantic.fields import field

from .ubl_signature_aggregate_components_2_1 import SignatureInformation

__NAMESPACE__ = (
    "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2"
)


class UbldocumentSignaturesType(BaseModel):
    """<ns1:Component xmlns:ns1="urn:un:unece:uncefact:documentation:2">
    <ns1:ComponentType>ABIE</ns1:ComponentType> <ns1:DictionaryEntryName>UBL
    Document Signatures.

    Details</ns1:DictionaryEntryName> <ns1:Definition>This class
    collects all signature information for a document.</ns1:Definition>
    <ns1:ObjectClass>UBL Document Signatures</ns1:ObjectClass>
    </ns1:Component>
    "

    :ivar signature_information: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>UBL Document Signatures. Signature
        Information</ns1:DictionaryEntryName> <ns1:Definition>Each of
        these is scaffolding for a single digital
        signature.</ns1:Definition>
        <ns1:Cardinality>1..n</ns1:Cardinality> <ns1:ObjectClass>UBL
        Document Signatures</ns1:ObjectClass>
        <ns1:PropertyTerm>Signature Information</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Signature
        Information</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Signature
        Information</ns1:RepresentationTerm> </ns1:Component>
    """

    class Meta:
        name = "UBLDocumentSignaturesType"

    model_config = ConfigDict(defer_build=True)
    signature_information: list[SignatureInformation] = field(
        default_factory=list,
        metadata={
            "name": "SignatureInformation",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2",
            "min_occurs": 1,
        },
    )


class UbldocumentSignatures(UbldocumentSignaturesType):
    class Meta:
        name = "UBLDocumentSignatures"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2"
        )

    model_config = ConfigDict(defer_build=True)
