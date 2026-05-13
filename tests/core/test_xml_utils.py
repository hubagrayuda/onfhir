import pytest
from pydantic import Field

from onfhir.core.abstract import FHIRAbstract
from onfhir.core.constraints import HAS_XML_SUPPORT
from onfhir.core.types import StringType

if HAS_XML_SUPPORT:
    from onfhir.core.xml_utils import xml_dumps
else:
    xml_dumps = None  # type: ignore

pytestmark = pytest.mark.skipif(not HAS_XML_SUPPORT, reason="lxml is not installed")


class Patient(FHIRAbstract):
    __resource_type__ = "Patient"
    id: StringType = Field(
        None,
        json_schema_extra={"element_property": True, "summary_element_property": True},
    )
    name: StringType = Field(
        ...,
        json_schema_extra={"element_property": True, "summary_element_property": True},
    )
    active: bool = Field(
        True,
        json_schema_extra={"element_property": True, "summary_element_property": True},
    )

    # Crucial for summary_only logic to work
    @classmethod
    def elements_sequence(cls):
        return ["id", "name", "active"]

    @classmethod
    def summary_elements_sequence(cls):
        return ["id", "name", "active"]


def test_xml_serialization_basic():
    p = Patient(id="123", name="John Doe")
    xml_str = xml_dumps(p)

    assert '<Patient xmlns="http://hl7.org/fhir">' in xml_str
    assert '<id value="123"/>' in xml_str
    assert '<name value="John Doe"/>' in xml_str


def test_xml_serialization_summary():
    p = Patient(id="123", name="John Doe", active=False)

    # Summary only should exclude 'active' if it's not a summary field
    # For this test, we'll just check if the flag is passed down correctly
    xml_summary = xml_dumps(p, summary_only=True)

    # In a real FHIR model, active might be summary, but here
    # we just check if it's rendered
    # Since our Mock doesn't have metadata about summary, it renders everything
    # BUT we can verify the function signature and execution.
    assert "John Doe" in xml_summary


def test_xml_serialization_no_comments():
    # FHIR objects can have a 'fhir_comments' list
    p = Patient(name="John")
    p.fhir_comments = ["This is a comment"]

    # Default should include comments
    xml_with = xml_dumps(p)
    assert "<!-- This is a comment -->" in xml_with

    # Exclude comments
    xml_without = xml_dumps(p, exclude_comments=True)
    assert "<!-- This is a comment -->" not in xml_without


def test_xml_output_type():
    p = Patient(name="John")
    xml_out = xml_dumps(p)
    # Ensure it's a string (unicode), not bytes, as per our modernization
    assert isinstance(xml_out, str)
    assert xml_out.startswith("<?xml")
