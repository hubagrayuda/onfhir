from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from ..valuesets import (
    AddressType,
    AddressUse,
    ContactPointSystem,
    ContactPointUse,
    IdentifierUse,
    NameUse,
    QuantityComparator,
)
from .primitives import (
    FHIRBase64Binary,
    FHIRBoolean,
    FHIRCode,
    FHIRDateTime,
    FHIRDecimal,
    FHIRInstant,
    FHIRPositiveInt,
    FHIRString,
    FHIRUnsignedInt,
    FHIRUri,
    FHIRUrl,
)

# -------------------
# Period Type
# -------------------
_PeriodType = Annotated[
    "FHIRPeriod | None",
    Field(None, description="Period of when the data is used."),
]


# -------------------
# Address
# -------------------
class FHIRAddress(BaseModel):
    """
    Data type for storing data values ​​in the form of addresses of a specific location.
    """

    use: Annotated[
        FHIRCode[AddressUse] | None,
        Field(None, description="Usage of the address"),
    ] = None
    type: Annotated[
        FHIRCode[AddressType] | None,
        Field(None, description="Type of the address"),
    ] = None
    text: Annotated[FHIRString | None, Field(None, description="Complete address")] = (
        None
    )
    line: Annotated[
        list[FHIRString] | None, Field([], description="Street name, home number, etc")
    ] = []
    city: Annotated[FHIRString | None, Field(None, description="City/Regency Name")] = (
        None
    )
    district: Annotated[FHIRString | None, Field(None, description="District Name")] = (
        None
    )
    state: Annotated[FHIRString | None, Field(None, description="State Name")] = None
    postalCode: Annotated[FHIRString | None, Field(None, description="Postal Code")] = (
        None
    )
    country: Annotated[
        FHIRString | None,
        Field(
            None,
            description=(
                "Country name or code, can use standard ISO code "
                "either from ISO 3166-2 or ISO 3166-3"
            ),
        ),
    ] = None
    period: _PeriodType = None


# -------------------
# Attachment
# -------------------
class FHIRAttachment(BaseModel):
    """
    Contains and references attachments or additional data in other formats.
    It's typically used to display images or reports in PDF format.
    It can also be used for any data with a MIME type.
    """

    contentType: Annotated[
        FHIRCode | None,
        Field(None, description="Attachement/Additional data type with Mime Type."),
    ] = None
    language: Annotated[
        FHIRCode | None,
        Field(None, description="Language used in the data."),
    ] = None
    data: Annotated[
        FHIRBase64Binary | None, Field(None, description="Inline data, base64'ed.")
    ] = None
    url: Annotated[
        FHIRUrl | None,
        Field(None, description="Data URI, place where the data can be found."),
    ] = None
    size: Annotated[
        FHIRUnsignedInt | None, Field(None, description="Bytes inside the data.")
    ]
    hash: Annotated[
        FHIRBase64Binary | None,
        Field(None, description="Data hash (sha-1 and base64'ed)."),
    ] = None
    title: Annotated[
        FHIRString | None,
        Field(None, description="Label to be shown as title of the data."),
    ] = None
    creation: Annotated[
        FHIRDateTime | None,
        Field(None, description="When the first time the data is created."),
    ] = None


# -------------------
# CodeableConcept
# -------------------
class FHIRCodeableConcept(BaseModel):
    """
    This data type represents a value that is typically assigned
    by one or more terminology references or other ontologies.
    """

    coding: Annotated[
        list["FHIRCoding"] | None,
        Field([], description="Coding system defined in the referenced system"),
    ] = []
    text: Annotated[
        str | None, Field(None, description="Description of the concept in question")
    ] = None


# -------------------
# Coding
# -------------------
class FHIRCoding(BaseModel):
    """
    A data type that represents a concept definition using certain symbols,
    which were previously defined in a certain system (CodeSystem).
    """

    system: Annotated[
        FHIRUri | None, Field(None, description="URI of the referenced system")
    ] = None
    version: Annotated[
        FHIRString | None, Field(None, description="Version of the referenced system")
    ] = None
    code: Annotated[
        FHIRCode | None,
        Field(None, description="Symbol defined in the referenced system"),
    ] = None
    display: Annotated[
        FHIRString | None,
        Field(None, description="Description of the referenced system"),
    ] = None
    userSelected: Annotated[
        FHIRBoolean | None,
        Field(
            None, description="Indicator whether this coding system is user-selected"
        ),
    ] = None


# -------------------
# ContactPoint
# -------------------
class FHIRContactPoint(BaseModel):
    """
    A data type that contains the values ​​of all contacts of a person or organization,
    such as contact info in the form of telephone numbers, emails, etc.
    """

    system: Annotated[
        FHIRCode[ContactPointSystem] | None,
        Field(
            None, description="Code from referenced system (phone, email, sms, etc.)"
        ),
    ] = None
    value: Annotated[
        FHIRString | None,
        Field(None, description="Detailed information of the contact"),
    ] = None
    use: Annotated[
        FHIRCode[ContactPointUse] | None,
        Field(None, description="Usage defined in the referenced system"),
    ] = None
    rank: Annotated[
        FHIRPositiveInt | None,
        Field(None, description="The rank used in this data type (1 = highest value)."),
    ] = None
    period: _PeriodType = None


# -------------------
# HumanName
# -------------------
class FHIRHumanName(BaseModel):
    """The data type contains the human name in text form."""

    use: Annotated[
        FHIRCode[NameUse] | None,
        Field(
            None,
            description=(
                "Code for use of names that are used as references "
                "(usual, official, temp, nickname, anonymous, old, maiden)."
            ),
        ),
    ] = None
    text: Annotated[
        FHIRString | None,
        Field(None, description="Contains text that represents the full name."),
    ] = None
    family: Annotated[
        FHIRString | None,
        Field(None, description="Contains text that represents the family name."),
    ] = None
    given: Annotated[
        list[FHIRString] | None,
        Field(
            [],
            description=(
                "Contains text that represents a nickname "
                "(not always a first name, can also be a middle name or last name)."
            ),
        ),
    ] = []
    prefix: Annotated[
        list[FHIRString] | None,
        Field(
            [],
            description=(
                "Prefix of a name, an additional word at the beginning before writing "
                "the name, for example a title or title (Prof. dr., Mr., Mrs., etc.)."
            ),
        ),
    ] = []
    suffix: Annotated[
        list[FHIRString] | None,
        Field(
            [],
            description=(
                "Suffix of a name, an additional word at the end after writing "
                "the name, for example a degree (ST, MBA, etc.)."
            ),
        ),
    ] = []
    period: _PeriodType = None


# -------------------
# Identifier
# -------------------
class FHIRIdentifier(BaseModel):
    """
    The Identifier data type is typically used to connect content on a resource
    to external content available on other frameworks or protocols.
    """

    use: Annotated[
        FHIRCode[IdentifierUse] | None,
        Field(
            None,
            description=(
                "Code of the use of the identifier that is used as a reference "
                "(usual, official, temp, secondary, old)."
            ),
        ),
    ] = None
    type: Annotated[
        FHIRCodeableConcept | None,
        Field(None, description="Description of the data type."),
    ] = None
    system: Annotated[
        FHIRUri | None,
        Field(None, description="Namespace for value of the identifier."),
    ] = None
    value: Annotated[
        FHIRString | None, Field(None, description="Contains unique value.")
    ] = None
    period: _PeriodType = None
    assigner: Annotated[
        "FHIRReference | None",
        Field(None, description="Name of the organization that issued the ID."),
    ] = None


# -------------------
# Period
# -------------------
class FHIRPeriod(BaseModel):
    """
    A data type for storing values ​​over a period/time range,
    defined by the start and end of a specific date or time.
    """

    start: Annotated[
        FHIRDateTime | None, Field(None, description="Start of the period")
    ] = None
    end: Annotated[
        FHIRDateTime | None, Field(None, description="End of the period")
    ] = None


# -------------------
# Quantity
# -------------------
class FHIRQuantity(BaseModel):
    """Data type for storing measurement data values ​​from an entity."""

    value: Annotated[
        FHIRDecimal | None,
        Field(None, description="The value in decimal or can also be an integer."),
    ] = None
    comparator: Annotated[
        FHIRCode[QuantityComparator] | None,
        Field(
            None,
            description=(
                "Comparative information for the value, the value for this property "
                "MUST be present if the value is an estimate (can be >, ≥, <, or ≤)."
            ),
        ),
    ] = None
    unit: Annotated[
        FHIRString | None, Field(None, description="The type of measurement unit used.")
    ] = None
    system: Annotated[
        FHIRUri | None,
        Field(
            None,
            description=(
                "The system reference for the unit code, the value for this property "
                "MUST be present if the unit property has a value or is filled."
            ),
        ),
    ] = None
    code: Annotated[
        FHIRCode | None, Field(None, description="Code of the used unit.")
    ] = None

    @model_validator(mode="after")
    def validate_unit_and_system(self):
        if self.unit is not None and self.system is None:
            raise ValueError("'system' must be provided if 'unit' is not None")
        return self


# -------------------
# SimpleQuantity
# -------------------
class FHIRSimpleQuantity(FHIRQuantity):
    """
    A data type for storing simple data values ​​resulting from measurements of an entity
    that refers to a Quantity resource.
    """

    @model_validator(mode="after")
    def ensure_empty_comparator(self):
        if self.comparator is not None:
            raise ValueError("'comparator' must be None for Simple Quantity")
        return self


# -------------------
# Range
# -------------------
class FHIRRange(BaseModel):
    """
    A data type for specifying a range of values ​​in order
    determined by the lowest and highest limits.
    """

    low: Annotated[
        FHIRSimpleQuantity | None,
        Field(None, description="Contains a range of values ​​with a lower limit."),
    ] = None
    high: Annotated[
        FHIRSimpleQuantity | None,
        Field(None, description="Contains a range of values ​​with a higher limit."),
    ] = None


# -------------------
# Ratio
# -------------------
class FHIRRatio(BaseModel):
    """
    A data type used as a connector between two quantity values
    ​​expressed as a numerator and denominator.
    """

    numerator: Annotated[
        FHIRQuantity | None, Field(None, description="Contains numerator value.")
    ] = None
    denominator: Annotated[
        FHIRQuantity | None, Field(None, description="Contains denominator value.")
    ] = None


# -------------------
# RatioRange
# -------------------
class FHIRRatioRange(BaseModel):
    """
    A data type that contains the ratio range of two Quantity values
    ​​expressed as a low numerator, high numerator, and denominator.
    """

    lowNumerator: Annotated[
        FHIRSimpleQuantity | None,
        Field(None, description="Contains lower numerator value."),
    ] = None
    highNumerator: Annotated[
        FHIRSimpleQuantity | None,
        Field(None, description="Contains higher numerator value."),
    ] = None
    denominator: Annotated[
        FHIRSimpleQuantity | None,
        Field(None, description="Contains denominator value."),
    ] = None


# -------------------
# Reference
# -------------------
class FHIRReference(BaseModel):
    """
    A data type for storing data that indicates a reference to another resource.
    References are always defined and represented by a single path,
    from the source resource to the target resource.
    """

    reference: Annotated[
        FHIRString | None, Field(None, description="Contains literal reference.")
    ] = None
    type: Annotated[
        FHIRUri | None, Field(None, description="Type of the reference.")
    ] = None
    identifier: Annotated[
        "FHIRIdentifier | None", Field(None, description="Contains logical reference.")
    ] = None
    display: Annotated[
        FHIRString | None, Field(None, description="Description regarding reference.")
    ] = None

    @model_validator(mode="after")
    def validate_either_reference_identifier_or_display(self):
        if self.reference is None and self.identifier is None and self.display is None:
            raise ValueError("'reference', 'identifier', or 'display' must be given.")
        return self


# -------------------
# Signature
# -------------------
class FHIRSignature(BaseModel):
    """
    The type of data that contains a signature or proof that it has been
    approved/recognized, either in electronic form (cryptography),
    or in the form of an image of the signature of the person concerned.
    """

    type: Annotated[
        list[FHIRCoding] | None,
        Field(
            [],
            description="Contains an indication of the reason for signing an object.",
        ),
    ] = []
    when: Annotated[
        list[FHIRInstant] | None, Field([], description="When signature is created")
    ] = []
    who: Annotated[
        list[FHIRReference] | None, Field([], description="Who signed the object")
    ] = []
    onBehalfOf: Annotated[
        FHIRReference | None,
        Field(
            None,
            description="Who carries out/represents/represents the relevant signature.",
        ),
    ] = None
    targetFormat: Annotated[
        FHIRCode | None,
        Field(None, description="The technical format of the signed resource."),
    ] = None
    sigFormat: Annotated[
        FHIRCode | None,
        Field(None, description="The technical format of the signature.."),
    ] = None
    data: Annotated[
        FHIRBase64Binary | None,
        Field(None, description="Contains the original content of the signature."),
    ] = None


# -------------------
# Timing
# -------------------
class _FHIRTimingRepeat(BaseModel): ...


class FHIRTiming(BaseModel):
    """
    This data type represents a time schedule
    that specifies events that may occur multiple times.
    """
