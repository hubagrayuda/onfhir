from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from .base import Base
from .types import StringType


class Element(Base):
    """Base model class for all elements in a resource."""

    __resource_type__: ClassVar[str] = "Element"

    id: StringType | None = Field(
        None,
        alias="id",
        title="Unique id for inter-element referencing",
        description=(
            "Unique id for the element within a resource (for internal references)."
            " This may be any string value that does not contain spaces."
        ),
        json_schema_extra={"element_property": True},
    )

    extension: list[ExtensionType] | None = Field(
        None,
        alias="extension",
        title="Additional content defined by implementations",
        description=(
            "May be used to represent additional information that is not part of "
            "the basic definition of the element. To make the use of extensions "
            "safe and managable, there is a strict set of governance applied to the"
            " definition and use of extensions. Though any implementer can define "
            "an extension, there is a set of requirements that SHALL be met as part"
            " of the definition of the extension."
        ),
        json_schema_extra={"element_property": True},
    )
