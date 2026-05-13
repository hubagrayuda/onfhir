from __future__ import annotations

from typing import ClassVar

from .element import FHIRElement


class DataType(FHIRElement):
    """Base model class for all FHIR data types."""

    __resource_type__: ClassVar[str] = "DataType"
