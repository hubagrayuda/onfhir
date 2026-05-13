import pytest
from pydantic import BaseModel

from onfhir.types.primitives import (
    FHIRDecimal,
    FHIRInteger,
    FHIRPositiveInt,
    FHIRUnsignedInt,
)


class IntModel(BaseModel):
    value: FHIRInteger


def test_valid_integer():
    m = IntModel(value=123)
    assert m.value == 123


def test_integer_out_of_range():
    with pytest.raises(ValueError):
        IntModel(value=999999999999)


# ---- Unsigned ----


class UnsignedModel(BaseModel):
    value: FHIRUnsignedInt


def test_unsigned_valid():
    assert UnsignedModel(value=0)


def test_unsigned_negative():
    with pytest.raises(ValueError):
        UnsignedModel(value=-1)


# ---- Positive ----


class PositiveModel(BaseModel):
    value: FHIRPositiveInt


def test_positive_valid():
    assert PositiveModel(value=1)


def test_positive_zero():
    with pytest.raises(ValueError):
        PositiveModel(value=0)


# ---- Decimal ----


class DecimalModel(BaseModel):
    value: FHIRDecimal


def test_decimal():
    m = DecimalModel(value="12.34")  # type: ignore
    assert str(m.value) == "12.34"
