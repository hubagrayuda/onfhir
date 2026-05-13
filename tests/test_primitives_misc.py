import pytest
from pydantic import BaseModel

from onfhir.types.primitives import (
    FHIRBase64Binary,
    FHIRBoolean,
    FHIRDate,
    FHIRDateTime,
    FHIRTime,
    FHIRUuid,
)

# ---- Base64 ----


class Base64Model(BaseModel):
    value: FHIRBase64Binary


def test_valid_base64():
    assert Base64Model(value="aGVsbG8=")  # type: ignore # "hello"


def test_invalid_base64():
    with pytest.raises(ValueError):
        Base64Model(value="not-base64")  # type: ignore


# ---- UUID ----


class UUIDModel(BaseModel):
    value: FHIRUuid


def test_valid_uuid():
    assert UUIDModel(
        value="urn:uuid:53fefa32-fcbb-4ff8-8a92-55ee120877b7"  # type: ignore
    )


def test_invalid_uuid():
    with pytest.raises(ValueError):
        UUIDModel(value="urn:uuid:INVALID")  # type: ignore


# ---- Boolean ----


class BoolModel(BaseModel):
    value: FHIRBoolean


def test_boolean():
    assert BoolModel(value=True)


# ---- Date / Time ----


class DateModel(BaseModel):
    value: FHIRDate


def test_date():
    assert DateModel(value="2023-01-01")


class DateTimeModel(BaseModel):
    value: FHIRDateTime


def test_datetime():
    assert DateTimeModel(value="2023-01-01T10:00:00")  # type: ignore


class TimeModel(BaseModel):
    value: FHIRTime


def test_time():
    assert TimeModel(value="10:00:00")  # type: ignore
