import pytest
from pydantic import Field, ValidationError

from onfhir.core.abstract import FHIRAbstract
from onfhir.core.types import StringType


class Resource(FHIRAbstract):
    """Mock Resource class for testing MRO checks."""

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
    fhir_comments: list[str] = Field(None, alias="fhir_comments")


def test_abstract_initialization():
    # Valid init
    res = MockResource(name="Test Resource", id="123")
    assert res.name == "Test Resource"
    assert res.id == "123"
    assert res.get_resource_type() == "MockResource"

    # Missing required field
    with pytest.raises(ValidationError):
        MockResource(id="123")


def test_model_dump_json_mode():
    res = MockResource(name="Test", id="123")

    # Python mode (dict)
    dump = res.model_dump(mode="python")
    assert isinstance(dump, dict)
    assert dump["resourceType"] == "MockResource"
    assert dump["name"] == "Test"

    # JSON mode (should include resourceType)
    json_dump = res.model_dump(mode="json")
    assert json_dump["resourceType"] == "MockResource"


def test_serialization_context_summary():
    # Summary only mode (should only include id and name, excluding comment)
    res = MockResource(name="Test", id="123", fhir_comments=["Secret comment"])

    # Normally includes everything
    assert "fhir_comments" in res.model_dump()

    # Summary only via context
    summary_dump = res.model_dump(context={"summary_only": True})
    assert "name" in summary_dump
    assert "id" in summary_dump
    assert "fhir_comments" not in summary_dump


def test_serialization_context_exclude_comments():
    # FHIR elements can have a 'fhir_comments' field. We can exclude it via context.
    res = MockResource(name="Test", fhir_comments=["This should be hidden"])

    dump = res.model_dump(context={"exclude_comments": True})
    assert "name" in dump
    assert "fhir_comments" not in dump


def test_model_dump_json_explicit_args():
    res = MockResource(name="Test")

    # Test our refactored explicit arguments
    json_str = res.model_dump_json(indent=2)
    assert '"name": "Test"' in json_str
    assert "  " in json_str  # Indentation check


def test_resource_base_check():
    assert MockResource.has_resource_base() is True

    class MockElement(FHIRAbstract):
        __resource_type__ = None  # Elements don't have resourceType

    assert MockElement.has_resource_base() is False


def test_get_model_class():
    res = MockResource(name="Test")
    # Should return the class itself
    assert res.get_model_class() == MockResource
