import datetime
import decimal
from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from onfhir.core.types import (
    Base64BinaryType,
    DateTimeType,
    DateType,
    DecimalType,
    IdType,
    InstantType,
    IntegerType,
    PositiveIntType,
    String,
    StringType,
    TimeType,
    UnsignedIntType,
    UrlType,
)


class StringModel(BaseModel):
    val: StringType = None


class IdModel(BaseModel):
    val: IdType = None


class DecimalModel(BaseModel):
    val: DecimalType = None


class IntegerModel(BaseModel):
    val: IntegerType = None


class DateModel(BaseModel):
    val: DateType = None


class DateTimeModel(BaseModel):
    val: DateTimeType = None


class UrlModel(BaseModel):
    val: UrlType = None


def test_string_type():
    # Valid strings
    assert StringModel(val="Hello World").val == "Hello World"
    assert StringModel(val="  Leading and trailing  ").val == "  Leading and trailing  "

    # Empty string (default not allowed)
    with pytest.raises(ValidationError):
        StringModel(val="")

    # Allowed empty string constraint
    class LooseStringModel(BaseModel):
        val: Annotated[str, String(allow_empty_string=True)]

    assert LooseStringModel(val="text").val == "text"
    assert LooseStringModel(val="").val == ""


def test_id_type():
    # Valid IDs
    assert IdModel(val="a-z.0-9").val == "a-z.0-9"
    assert IdModel(val="12345").val == "12345"

    # Invalid characters
    with pytest.raises(ValidationError):
        IdModel(val="invalid_id!")

    # Length limit (default 64)
    IdModel(val="a" * 64)
    with pytest.raises(ValidationError):
        IdModel(val="a" * 65)


def test_decimal_type():
    # Valid decimals
    assert DecimalModel(val="1.23").val == decimal.Decimal("1.23")
    assert DecimalModel(val=1.23).val == decimal.Decimal("1.23")
    assert DecimalModel(val=decimal.Decimal("1.23")).val == decimal.Decimal("1.23")

    # Precision and scale
    d = DecimalModel(val="1.00000000000000000001").val
    assert d == decimal.Decimal("1.00000000000000000001")

    # Serialization to JSON (should be float as per our refactor)
    model = DecimalModel(val="1.23")
    dump = model.model_dump(mode="json")
    assert isinstance(dump["val"], float)
    assert dump["val"] == 1.23


def test_integer_types():
    # Standard Integer (32-bit range)
    assert IntegerModel(val=2147483647).val == 2147483647
    assert IntegerModel(val=-2147483648).val == -2147483648
    with pytest.raises(ValidationError):
        IntegerModel(val=2147483648)

    # UnsignedInt
    class UnsignedModel(BaseModel):
        val: UnsignedIntType

    assert UnsignedModel(val=0).val == 0
    with pytest.raises(ValidationError):
        UnsignedModel(val=-1)

    # PositiveInt
    class PositiveModel(BaseModel):
        val: PositiveIntType

    assert PositiveModel(val=1).val == 1
    with pytest.raises(ValidationError):
        PositiveModel(val=0)


def test_url_types():
    # Valid URLs
    assert UrlModel(val="http://example.com").val == "http://example.com"
    assert (
        UrlModel(val="https://example.com/fhir/Patient/123").val
        == "https://example.com/fhir/Patient/123"
    )

    # Relative paths (FHIR references)
    assert UrlModel(val="Patient/123").val == "Patient/123"
    assert UrlModel(val="/Patient/123").val == "/Patient/123"
    assert (
        UrlModel(val="Observation/abc.123/_history/1").val
        == "Observation/abc.123/_history/1"
    )

    # Invalid formats
    with pytest.raises(ValidationError):
        UrlModel(val="not a url")


def test_date_types():
    # Full date
    assert DateModel(val="2023-10-25").val == datetime.date(2023, 10, 25)

    # Partial dates (should return as strings)
    assert DateModel(val="2023").val == "2023"
    assert DateModel(val="2023-10").val == "2023-10"

    # Invalid dates
    with pytest.raises(ValidationError):
        DateModel(val="2023-13-01")  # Invalid month
    with pytest.raises(ValidationError):
        DateModel(val="2023-10-32")  # Invalid day
    with pytest.raises(ValidationError):
        DateModel(val="invalid")


def test_datetime_types():
    # Full datetime with timezone
    dt_str = "2023-10-25T14:30:00+02:00"
    val = DateTimeModel(val=dt_str).val
    assert isinstance(val, datetime.datetime)
    assert val.year == 2023
    assert val.tzinfo is not None

    # Datetime without timezone (should fail if it has time component)
    with pytest.raises(ValidationError):
        DateTimeModel(val="2023-10-25T14:30:00")

    # Partial date-times
    assert DateTimeModel(val="2023").val == "2023"
    assert DateTimeModel(val="2023-10").val == "2023-10"

    # Date only as input
    d = datetime.date(2023, 10, 25)
    assert DateTimeModel(val=d).val == d


def test_instant_type():
    class InstantModel(BaseModel):
        val: InstantType

    # Instant must have time and timezone
    inst_str = "2023-10-25T14:30:00.123Z"
    val = InstantModel(val=inst_str).val
    assert isinstance(val, datetime.datetime)

    # Instant cannot be partial date
    with pytest.raises(ValidationError):
        InstantModel(val="2023-10")


def test_time_type():
    class TimeModel(BaseModel):
        val: TimeType

    # Valid time
    assert TimeModel(val="14:30:00").val == "14:30:00"
    assert TimeModel(val="14:30:00.123456").val == "14:30:00.123456"

    # Invalid time
    with pytest.raises(ValidationError):
        TimeModel(val="25:00:00")
    with pytest.raises(ValidationError):
        TimeModel(val="14:30")  # Seconds are required in FHIR


def test_base64binary_type():
    class B64Model(BaseModel):
        val: Base64BinaryType

    # Valid base64
    data = b"Hello World"
    import base64

    b64_str = base64.b64encode(data).decode()
    model = B64Model(val=b64_str)
    assert model.val == data

    # Serialization
    assert model.model_dump(mode="json")["val"] == b64_str
