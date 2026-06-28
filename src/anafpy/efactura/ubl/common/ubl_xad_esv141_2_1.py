from pydantic import BaseModel, ConfigDict
from xsdata_pydantic.fields import field

from .ubl_xad_esv132_2_1 import (
    CertificateValues,
    RevocationValues,
    XadEstimeStampType,
)

__NAMESPACE__ = "http://uri.etsi.org/01903/v1.4.1#"


class ArchiveTimeStampV2(XadEstimeStampType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.4.1#"

    model_config = ConfigDict(defer_build=True)


class ValidationDataType(BaseModel):
    model_config = ConfigDict(defer_build=True)
    certificate_values: CertificateValues | None = field(
        default=None,
        metadata={
            "name": "CertificateValues",
            "type": "Element",
            "namespace": "http://uri.etsi.org/01903/v1.3.2#",
        },
    )
    revocation_values: RevocationValues | None = field(
        default=None,
        metadata={
            "name": "RevocationValues",
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
    ur: str | None = field(
        default=None,
        metadata={
            "name": "UR",
            "type": "Attribute",
        },
    )


class TimeStampValidationData(ValidationDataType):
    class Meta:
        namespace = "http://uri.etsi.org/01903/v1.4.1#"

    model_config = ConfigDict(defer_build=True)
