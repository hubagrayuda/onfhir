import sys  # noqa: F401

from pydantic import Field

from onfhir.core.abstract import FHIRAbstract
from onfhir.core.types import StringType


class Resource(FHIRAbstract):
    __resource_type__ = "Resource"


class MockResource(Resource):
    __resource_type__ = "MockResource"
    id: StringType = Field(
        None,
        json_schema_extra={"element_property": True, "summary_element_property": True},
    )
    name: StringType = Field(
        ...,
        json_schema_extra={"element_property": True, "summary_element_property": True},
    )
    fhir_comments: list[str] = Field(None, json_schema_extra={"element_property": True})


print("sequence:", MockResource.elements_sequence())
print("summary:", MockResource.summary_elements_sequence())
print("alias_mapping:", MockResource.get_alias_mapping())
