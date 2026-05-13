import pytest
from pydantic import BaseModel

from onfhir.types.primitives import FHIRId, FHIRMarkdown, FHIRString


class Model(BaseModel):
    value: FHIRString


def test_valid_string():
    m = Model(value="hello")  # type: ignore
    assert m.value == "hello"


def test_empty_string():
    with pytest.raises(ValueError):
        Model(value="")  # type: ignore


def test_leading_space():
    with pytest.raises(ValueError):
        Model(value=" hello")  # type: ignore


def test_trailing_space():
    with pytest.raises(ValueError):
        Model(value="hello ")  # type: ignore


def test_invalid_control_char():
    with pytest.raises(ValueError):
        Model(value="hello\x01")  # type: ignore


# ---- ID ----


class IdModel(BaseModel):
    value: FHIRId


def test_valid_id():
    m = IdModel(value="abc-123.DEF")  # type: ignore
    assert m.value == "abc-123.DEF"


def test_invalid_id():
    with pytest.raises(ValueError):
        IdModel(value="invalid id!!!")  # type: ignore


# ---- Markdown ----


class MarkdownModel(BaseModel):
    value: FHIRMarkdown


def test_markdown():
    m = MarkdownModel(value="**bold**")  # type: ignore
    assert m.value == "**bold**"
