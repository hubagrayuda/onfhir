import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Any, get_args

from pydantic import Field, GetCoreSchemaHandler
from pydantic_core import core_schema

# -------------------
# Boolean
# -------------------
FHIRBoolean = bool


# -------------------
# Integer (32-bit)
# -------------------
FHIRInteger = Annotated[int, Field(..., ge=-2_147_483_648, le=2_147_483_647)]


# -------------------
# String
# -------------------
def validate_fhir_string(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Must be string")

    if len(value) == 0:
        raise ValueError("String cannot be empty")

    if len(value) > 1_048_576:
        raise ValueError("String too long")

    if value != value.strip():
        raise ValueError("No leading/trailing spaces allowed")

    for ch in value:
        code = ord(ch)
        if code < 32 and ch not in ("\t", "\n", "\r"):
            raise ValueError("Invalid control character")

    return value


class FHIRString(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, *_):
        return core_schema.no_info_plain_validator_function(validate_fhir_string)


# -------------------
# Decimal
# -------------------
FHIRDecimal = Decimal


# -------------------
# URI / URL / Canonical
# -------------------
URI_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:.*$")


class FHIRUri(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, *_):
        from pydantic_core import core_schema

        def validate(value: str) -> str:
            if not URI_REGEX.match(value):
                raise ValueError("Invalid URI")
            return value

        return core_schema.no_info_plain_validator_function(validate)


FHIRUrl = FHIRUri
FHIRCanonical = FHIRUri


# -------------------
# Base64 Binary
# -------------------
class FHIRBase64Binary(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, *_):
        import base64

        from pydantic_core import core_schema

        def validate(value: str) -> str:
            try:
                base64.b64decode(value, validate=True)
            except Exception as e:
                raise ValueError("Invalid Base64") from e
            return value

        return core_schema.no_info_plain_validator_function(validate)


# -------------------
# Instant
# -------------------
FHIRInstant = datetime


# -------------------
# Date / DateTime / Time
# -------------------
FHIRDate = date
FHIRDateTime = datetime
FHIRTime = time


# -------------------
# Code
# -------------------
class FHIRCode[T: str](FHIRString):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ):
        args = get_args(source_type)
        if args:
            # Chain: Generic argument validation -> FHIR String validation
            return core_schema.chain_schema(
                [
                    handler(args[0]),
                    core_schema.no_info_plain_validator_function(validate_fhir_string),
                ]
            )

        # Default FHIR String validation
        return core_schema.no_info_plain_validator_function(validate_fhir_string)


# -------------------
# OID
# -------------------
class FHIROid(FHIRUri):
    pass


# -------------------
# ID
# -------------------
ID_REGEX = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")


class FHIRId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, *_):
        from pydantic_core import core_schema

        def validate(value: str) -> str:
            if not ID_REGEX.match(value):
                raise ValueError("Invalid id")
            return value

        return core_schema.no_info_plain_validator_function(validate)


# -------------------
# Markdown
# -------------------
FHIRMarkdown = FHIRString


# -------------------
# Unsigned Int
# -------------------
FHIRUnsignedInt = Annotated[int, Field(..., ge=0, le=2_147_483_647)]


# -------------------
# Positive Int
# -------------------
FHIRPositiveInt = Annotated[int, Field(..., ge=1, le=2_147_483_647)]


# -------------------
# UUID
# -------------------
UUID_REGEX = re.compile(
    r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class FHIRUuid(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, *_):
        from pydantic_core import core_schema

        def validate(value: str) -> str:
            if not UUID_REGEX.match(value):
                raise ValueError("Invalid UUID (must be lowercase urn:uuid)")
            return value

        return core_schema.no_info_plain_validator_function(validate)
