import pytest
from pydantic import BaseModel

from onfhir.types.primitives import FHIRCanonical, FHIROid, FHIRUri, FHIRUrl


class UriModel(BaseModel):
    value: FHIRUri


def test_valid_uri():
    m = UriModel(value="http://example.com")  # type: ignore
    assert m.value


def test_invalid_uri():
    with pytest.raises(ValueError):
        UriModel(value="not-a-uri")  # type: ignore


# ---- URL ----


class UrlModel(BaseModel):
    value: FHIRUrl


def test_url():
    assert UrlModel(value="https://example.com")  # type: ignore


# ---- Canonical ----


class CanonicalModel(BaseModel):
    value: FHIRCanonical


def test_canonical():
    assert CanonicalModel(value="http://example.com/StructureDefinition/test")  # type: ignore


# ---- OID ----


class OidModel(BaseModel):
    value: FHIROid


def test_oid():
    assert OidModel(value="urn:oid:1.2.3.4")  # type: ignore
