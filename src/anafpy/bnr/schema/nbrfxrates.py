from pydantic import BaseModel, ConfigDict
from xsdata.models.datatype import XmlDate
from xsdata_pydantic.fields import field

__NAMESPACE__ = "https://www.bnr.ro/xsd"


class LtCube(BaseModel):
    class Meta:
        name = "LT_Cube"

    model_config = ConfigDict(defer_build=True)
    rate: list["LtCube.Rate"] = field(
        default_factory=list,
        metadata={
            "name": "Rate",
            "type": "Element",
            "namespace": "https://www.bnr.ro/xsd",
            "min_occurs": 1,
        },
    )
    date: XmlDate = field(
        metadata={
            "type": "Attribute",
            "required": True,
        }
    )

    class Rate(BaseModel):
        model_config = ConfigDict(defer_build=True)
        value: str = field(
            default="",
            metadata={
                "required": True,
                "min_exclusive": "0",
                "pattern": r"\d+.\d{4}",
            },
        )
        currency: str = field(
            metadata={
                "type": "Attribute",
                "required": True,
                "pattern": r"[A-Z]{3}",
            }
        )
        multiplier: int | None = field(
            default=None,
            metadata={
                "type": "Attribute",
                "min_inclusive": 1,
            },
        )


class LtHeader(BaseModel):
    class Meta:
        name = "LT_Header"

    model_config = ConfigDict(defer_build=True)
    publisher: str = field(
        metadata={
            "name": "Publisher",
            "type": "Element",
            "namespace": "https://www.bnr.ro/xsd",
            "required": True,
            "min_length": 1,
            "pattern": r"[\S]{1}.{0,99}",
        }
    )
    publishing_date: XmlDate = field(
        metadata={
            "name": "PublishingDate",
            "type": "Element",
            "namespace": "https://www.bnr.ro/xsd",
            "required": True,
        }
    )
    message_type: str = field(
        metadata={
            "name": "MessageType",
            "type": "Element",
            "namespace": "https://www.bnr.ro/xsd",
            "required": True,
            "pattern": r"[A-Z]{2}",
        }
    )


class DataSet(BaseModel):
    """
    nbrfxrates.xsd.
    """

    class Meta:
        namespace = "https://www.bnr.ro/xsd"

    model_config = ConfigDict(defer_build=True)
    header: LtHeader = field(
        metadata={
            "name": "Header",
            "type": "Element",
            "required": True,
        }
    )
    body: "DataSet.Body" = field(
        metadata={
            "name": "Body",
            "type": "Element",
            "required": True,
        }
    )

    class Body(BaseModel):
        model_config = ConfigDict(defer_build=True)
        subject: str = field(
            metadata={
                "name": "Subject",
                "type": "Element",
                "required": True,
                "min_length": 1,
                "pattern": r"[\S]{1}.{0,99}",
            }
        )
        description: str | None = field(
            default=None,
            metadata={
                "name": "Description",
                "type": "Element",
                "min_length": 1,
                "pattern": r"[\S]{1}.{0,499}",
            },
        )
        orig_currency: str = field(
            metadata={
                "name": "OrigCurrency",
                "type": "Element",
                "required": True,
                "pattern": r"[A-Z]{3}",
            }
        )
        cube: list[LtCube] = field(
            default_factory=list,
            metadata={
                "name": "Cube",
                "type": "Element",
                "min_occurs": 1,
            },
        )
