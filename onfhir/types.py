from __future__ import annotations

from typing import TYPE_CHECKING

from .core.base import (
    create_fhir_element_or_resource_type,
    create_fhir_type,
)

# The dependency hierarchy is circular due to Extension being referenced
# in FHIRPrimitiveExtension which itself is referenced in every resource.
# Extension is also referenced in several resources and refers to several resources.
# Pydantic fields can not use forward references as this causes the
# "class not fully defined" error at runtime: https://docs.pydantic.dev/2.12/errors/usage_errors/#class-not-fully-defined
# To properly allow type checkers to type check, use type aliases during
# type checking and the create_fhir_type workaround at runtime.
if TYPE_CHECKING:
    from . import (
        base,
        datatype,
        element,
        resource,
    )

    BaseType = base.Base
    DataTypeType = datatype.DataType
    ElementType = element.Element
    ResourceType = resource.Resource
else:
    FHIRPrimitiveExtensionType = create_fhir_type(
        "FHIRPrimitiveExtensionType",
        "fhir.resources.fhirprimitiveextension.FHIRPrimitiveExtension",
    )

    ElementType = create_fhir_element_or_resource_type(
        "ElementType", "fhir.resources.element.Element"
    )

    ResourceType = create_fhir_element_or_resource_type(
        "ResourceType", "fhir.resources.resource.Resource"
    )

    BaseType = create_fhir_type("BaseType", "fhir.resources.base.Base")

    DataTypeType = create_fhir_type("DataTypeType", "fhir.resources.datatype.DataType")
