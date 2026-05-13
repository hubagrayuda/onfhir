"""
This module defines core constants, type mappings, and configuration flags
used throughout the onfhir library to enforce FHIR-specific constraints
and manage type conversions.
"""

import re
from collections import OrderedDict
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any  # noqa: F401
from uuid import UUID

# Regex used to extract FHIR versions from class names or module paths
FHIR_VERSIONS = re.compile(r"\.(DSTU2|STU3|R4|R4B|R5|R6)")

# --- Hardcoded FHIR constraints ---
ID_MAX_LENGTH = 64
ALLOW_EMPTY_STRING = False

# --- Dependency detection for optional formats ---
try:
    import lxml  # noqa: F401

    HAS_XML_SUPPORT = True
except ImportError:
    HAS_XML_SUPPORT = False

try:
    import yaml  # noqa: F401

    HAS_YAML_SUPPORT = True
except ImportError:
    HAS_YAML_SUPPORT = False


# --- Type Mappings ---

# Maps FHIR resource/type names to their respective module paths
FHIR_TYPES_MAPS: dict[str, str] = {}

# Maps native Python types to their FHIR primitive equivalents
FHIR_PRIMITIVES_MAPS: dict[Any, str] = {
    str: "string",
    int: "integer",
    bool: "boolean",
    bytes: "base64Binary",
    bytearray: "base64Binary",
    float: "decimal",
    datetime: "dateTime",
    date: "date",
    time: "time",
    Decimal: "decimal",
    UUID: "uuid",
}

# Immutable set of supported Python types for quick lookup
PYTHON_PRIMITIVES = frozenset(FHIR_PRIMITIVES_MAPS.keys())

# Comprehensive list of all primitive types defined in the FHIR specification
FHIR_PRIMITIVES = frozenset(
    [
        "boolean",
        "string",
        "base64Binary",
        "code",
        "id",
        "decimal",
        "integer",
        "integer64",
        "unsignedInt",
        "positiveInt",
        "uri",
        "oid",
        "uuid",
        "canonical",
        "url",
        "markdown",
        "xhtml",
        "date",
        "dateTime",
        "instant",
        "time",
    ]
)

# Coding used in the 'meta.tag' field when a resource is returned in summary mode
SUMMARY_MODE_CODING = OrderedDict(
    [
        ("system", "http://terminology.hl7.org/CodeSystem/v3-ObservationValue"),
        ("code", "SUBSETTED"),
        ("display", "Resource encoded in summary mode"),
    ]
)
