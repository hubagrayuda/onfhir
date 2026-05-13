import pytest
from pydantic import BaseModel, Field, ValidationError

from onfhir.core.abstract import FHIRAbstract
from onfhir.core.base import create_fhir_element_or_resource_type, create_fhir_type
from onfhir.core.types import StringType


# 1. Setup mock models
class Patient(FHIRAbstract):
    __resource_type__ = "Patient"
    name: StringType = Field(None, json_schema_extra={"element_property": True})


class Observation(FHIRAbstract):
    __resource_type__ = "Observation"
    status: StringType = Field(None, json_schema_extra={"element_property": True})


# Register these in FHIR_TYPES_MAPS for the polymorphic validator to find them
# In a real app, this happens via create_fhir_type
from onfhir.core.constraints import FHIR_TYPES_MAPS  # noqa: E402

FHIR_TYPES_MAPS["PatientType"] = "tests.core.test_base.Patient"
FHIR_TYPES_MAPS["ObservationType"] = "tests.core.test_base.Observation"

# Create validator types
PatientValidator = create_fhir_type("PatientType", "tests.core.test_base.Patient")
ResourceValidator = create_fhir_element_or_resource_type(
    "ResourceType", "onfhir.core.abstract.FHIRAbstract"
)


class Container(BaseModel):
    patient: PatientValidator = None
    any_resource: ResourceValidator = None


def test_patient_validator():
    # Dict input
    c = Container(patient={"name": "John"})
    assert isinstance(c.patient, Patient)
    assert c.patient.name == "John"

    # Instance input
    p = Patient(name="Doe")
    c2 = Container(patient=p)
    assert c2.patient.name == "Doe"

    # JSON string input
    c3 = Container(patient='{"name": "Smith"}')
    assert c3.patient.name == "Smith"


def test_resource_polymorphic_validator():
    # Valid Patient in generic resource slot
    c = Container(any_resource={"resourceType": "Patient", "name": "John"})
    assert isinstance(c.any_resource, Patient)
    assert c.any_resource.name == "John"

    # Valid Observation in generic resource slot
    c2 = Container(any_resource={"resourceType": "Observation", "status": "final"})
    assert isinstance(c2.any_resource, Observation)
    assert c2.any_resource.status == "final"

    # Invalid resourceType
    with pytest.raises(ValidationError):
        Container(any_resource={"resourceType": "Unknown", "foo": "bar"})


def test_validator_mismatch_error():
    # Trying to put an Observation where a Patient is expected
    with pytest.raises(ValidationError) as exc:
        Container(patient={"resourceType": "Observation", "status": "final"})

    # Check our custom error message
    assert "expects resource type ``Patient``, but got ``Observation``" in str(
        exc.value
    )


def test_invalid_input_type():
    # Pass a list instead of a dict/str
    with pytest.raises(ValidationError) as exc:
        Container(patient=[1, 2, 3])
    assert "Value expected to be an instance of Patient, but got list" in str(exc.value)


def test_factory_caching():
    # Factory should return the same class for the same input
    V1 = create_fhir_type("PatientType", "tests.core.test_base.Patient")
    V2 = create_fhir_type("PatientType", "tests.core.test_base.Patient")
    assert V1 is V2
