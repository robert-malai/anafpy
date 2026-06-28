from pydantic import ConfigDict

from .ubl_unqualified_data_types_2_1 import IdentifierType

__NAMESPACE__ = (
    "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2"
)


class ReferencedSignatureIdtype(IdentifierType):
    class Meta:
        name = "ReferencedSignatureIDType"

    model_config = ConfigDict(defer_build=True)


class ReferencedSignatureId(ReferencedSignatureIdtype):
    class Meta:
        name = "ReferencedSignatureID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)
