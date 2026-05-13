from pydantic import Field

from onfhir.core.abstract import FHIRAbstract
from onfhir.core.types import StringType


class Resource(FHIRAbstract):
    __resource_type__ = "Resource"


class MockResource(Resource):
    __resource_type__ = "MockResource"
    id: StringType = Field(None, json_schema_extra={"element_property": True})
    name: StringType = Field(..., json_schema_extra={"element_property": True})


print(f"Model fields: {list(MockResource.model_fields.keys())}")
print(f"Elements sequence: {MockResource.elements_sequence()}")
print(f"Alias mapping: {MockResource.get_alias_mapping()}")

res = MockResource(name="Test", id="123")
print(f"Dump: {res.model_dump()}")
