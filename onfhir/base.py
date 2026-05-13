from __future__ import annotations

from typing import ClassVar

from .core.abstract import FHIRAbstract


class Base(FHIRAbstract):
    """Base model class for all FHIR resources and types."""

    __resource_type__: ClassVar[str] = "Base"
