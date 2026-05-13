from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from .base import Base
from .core.types import CodeType, IdType, UriType


class Resource(Base):
    """Base model class for all FHIR resources."""

    __resource_type__: ClassVar[str] = "Resource"

    id: IdType | None = Field(
        default=None,
        alias="id",
        title="Logical id of this artifact",
        description=(
            "The logical id of the resource, as used in the URL for the resource. "
            "Once assigned, this value never changes."
        ),
        json_schema_extra={
            "element_property": True,
            "summary_element_property": True,
        },
    )

    implicitRules: UriType | None = Field(
        default=None,
        alias="implicitRules",
        title="A set of rules under which this content was created",
        description=(
            "A reference to a set of rules that were followed when the resource was"
            " constructed, and which must be understood when processing the "
            "content. Often, this is a reference to an implementation guide that "
            "defines the special rules along with other profiles etc."
        ),
        json_schema_extra={
            "element_property": True,
            "summary_element_property": True,
        },
    )
    implicitRules__ext: FHIRPrimitiveExtensionType | None = Field(
        default=None,
        alias="_implicitRules",
        title="Extension field for ``implicitRules``.",
    )

    language: CodeType | None = Field(
        default=None,
        alias="language",
        title="Language of the resource content",
        description="The base language in which the resource is written.",
        json_schema_extra={
            "element_property": True,
        },
    )
    language__ext: FHIRPrimitiveExtensionType | None = Field(
        default=None, alias="_language", title="Extension field for ``language``."
    )

    meta: MetaType | None = Field(
        default=None,
        alias="meta",
        title="Metadata about the resource",
        description=(
            "The metadata about the resource. This is content that is maintained by"
            " the infrastructure. Changes to the content might not always be "
            "associated with version changes to the resource."
        ),
        json_schema_extra={
            "element_property": True,
            "summary_element_property": True,
        },
    )
