import datetime
import decimal
import logging
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

from annotated_types import SLOTS, BaseMetadata, Ge, GroupedMetadata, Le, MaxLen, MinLen
from pydantic import AnyUrl, Base64Bytes, Field, GetCoreSchemaHandler, ValidationError
from pydantic._internal._fields import pydantic_general_metadata
from pydantic.types import UUID4
from pydantic_core import Url as PydanticUrl
from pydantic_core import core_schema

from .constraints import (
    ALLOW_EMPTY_STRING,
    FHIR_PRIMITIVES,
    FHIR_PRIMITIVES_MAPS,
    ID_MAX_LENGTH,
)

LOGGER = logging.getLogger(__name__)

__all__ = [
    "String",
    "Base64Binary",
    "Code",
    "Id",
    "Decimal",
    "Integer",
    "Integer64",
    "UnsignedInt",
    "PositiveInt",
    "PatternConstraint",
    "Uri",
    "Canonical",
    "Url",
    "Markdown",
    "Xhtml",
    "Date",
    "DateTime",
    "Instant",
    "Time",
    "BooleanType",
    "StringType",
    "Base64BinaryType",
    "CodeType",
    "IdType",
    "IntegerType",
    "Integer64Type",
    "DecimalType",
    "UnsignedIntType",
    "PositiveIntType",
    "CanonicalType",
    "UriType",
    "OidType",
    "UuidType",
    "UrlType",
    "MarkdownType",
    "XhtmlType",
    "DateType",
    "DateTimeType",
    "InstantType",
    "TimeType",
]


@dataclass(frozen=True, **SLOTS)
class String(GroupedMetadata):
    """A sequence of Unicode characters	xs:string JSON String
    Note that strings SHALL NOT exceed 1,048,576 (1024*1024) characters in size.
    Because UTF-8 characters can be expressed with more than one byte,
    the string size may be more than 1MB.
    Strings SHOULD not contain Unicode character points below 32, except for
    u0009 (horizontal tab), u000D (carriage return) and u000A (line feed).
    Leading and Trailing whitespace is allowed, but SHOULD be removed when using
    the XML format. Note: This means that a string that consists only of whitespace
    could be trimmed to nothing, which would be treated as an invalid element value.
    Therefore strings SHOULD always contain non-whitespace content
    This datatype can be bound to a ValueSet
    Regex: ^[\\s\\S]+$ (see notes below)

    ```py
    from pydantic import BaseModel
    from typing_extension import Annotated
    from fhir_core.types import String

    StringType = Annotated[str, String(allow_empty_string=False)]

    class StringModel(BaseModel):
        myString: StringType = None
    model = StringModel(myString='My string')
    print(model.myString)
    #> My string
    ```
    """

    allow_empty_string: bool = ALLOW_EMPTY_STRING
    __visit_name__ = "string"

    def __iter__(self) -> Iterator[BaseMetadata]:
        """
        Yield metadata for string validation.

        Returns:
            Iterator[BaseMetadata]: Metadata containing regex patterns.
        """
        regex = r"[ \r\n\t\S]+"
        if self.allow_empty_string:
            regex = f"({regex})|(^$)"
        yield pydantic_general_metadata(pattern=f"^{regex}$")
        if not self.allow_empty_string:
            yield MinLen(1)


@dataclass(frozen=True, **SLOTS)
class Base64Binary:
    """A stream of bytes, base64 encoded (RFC 4648)
    Just a symbolic class, no need to further check with regex as value is
    already decoded.
    """

    __visit_name__ = "base64Binary"
    regex = r"^(\s*([0-9a-zA-Z+=]){4}\s*)+$"

    def __hash__(self) -> int:
        """ """
        return hash(self.__class__)


@dataclass(frozen=True, **SLOTS)
class Code(GroupedMetadata):
    """Indicates that the value is taken from a set of controlled
    strings defined elsewhere (see Using codes for further discussion).
    Technically, a code is restricted to a string which has at least one
    character and no leading or trailing whitespace, and where there is
    no whitespace other than single spaces in the contents"""

    __visit_name__ = "code"

    def __iter__(self) -> Iterator[BaseMetadata]:
        """ """
        regex = r"^[^\s]+(\s[^\s]+)*$"
        yield pydantic_general_metadata(pattern=regex)

    def __hash__(self) -> int:
        return hash(self.__class__)


@dataclass(frozen=True, **SLOTS)
class Id(GroupedMetadata):
    """Any combination of upper- or lower-case ASCII letters
    ('A'..'Z', and 'a'..'z', numerals ('0'..'9'), '-' and '.',
    with a length limit of 64 characters.
    (This might be an integer, an un-prefixed OID, UUID or any other identifier
    pattern that meets these constraints.)

    But it is possible to change the default behaviour by patching
    constraint.ID_MAX_LENGTH value!

    There are a lots of discussion about ``Resource.Id`` length of value.
        1. https://bit.ly/360HksL
        2. https://bit.ly/3o1fZgl
    We see there is some agreement and disagreement, because of that we decide to make
    it more flexible. Now it is possible configure three types of constraints.
    """

    pattern = r"^[A-Za-z0-9\-.]+$"
    min_length = 1
    max_length = ID_MAX_LENGTH
    __visit_name__ = "id"

    def __iter__(self) -> Iterator[BaseMetadata]:
        """
        Yield metadata for ID validation.

        Returns:
            Iterator[BaseMetadata]: Metadata for length and pattern.
        """
        if self.min_length is not None:
            yield MinLen(self.min_length)
        if self.max_length is not None:
            yield MaxLen(self.max_length)
        if self.pattern is not None:
            yield pydantic_general_metadata(pattern=self.pattern)


@dataclass(**SLOTS)
class Decimal:
    """Rational numbers that have a decimal representation.
    See below about the precision of the number"""

    pattern = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?$")
    __visit_name__ = "decimal"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type["Decimal"], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Return a Pydantic CoreSchema with Decimal validation.

        Args:
            source_type: The source type to be converted.
            handler: The handler to get the CoreSchema.

        Returns:
            A Pydantic CoreSchema with Decimal.

        """

        def _serialize(
            value: decimal.Decimal | float | str,
            info: core_schema.SerializationInfo,
        ) -> float:
            """Encodes a Decimal or float as float for JSON."""
            return float(value)

        def _validate(
            input_value: decimal.Decimal | float | str,
            validator: Callable[[decimal.Decimal | float | str], Any],
            _validation_info: core_schema.ValidationInfo,
        ) -> decimal.Decimal:
            """
            Validate a decimal value.

            Args:
                input_value: The value to be validated.
                validator: The inner validator.
                _validation_info: Validation metadata.

            Returns:
                decimal.Decimal: The validated decimal object.
            """
            if isinstance(input_value, (float, str)):
                input_value = decimal.Decimal(str(input_value))
            return validator(input_value)

        # Allow float/str in the schema input
        input_schema = core_schema.union_schema(
            [
                core_schema.decimal_schema(),
                core_schema.float_schema(),
                core_schema.str_schema(),
            ]
        )

        return core_schema.with_info_wrap_validator_function(
            _validate,
            input_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize,
                info_arg=True,
                when_used="always",
            ),
        )

    def __hash__(self) -> int:
        return hash(self.__class__)


@dataclass(frozen=True, **SLOTS)
class Integer(GroupedMetadata):
    """A signed integer in the range −2,147,483,648..2,147,483,647 (32-bit;
    for larger values, use decimal)"""

    pattern = re.compile(r"^[0]|[-+]?[1-9][0-9]*$")
    min_length: int = -2147483648
    max_length: int = 2147483647

    __visit_name__ = "integer"

    def __iter__(self) -> Iterator[BaseMetadata]:
        """
        Yield metadata for Integer validation.

        Returns:
            Iterator[BaseMetadata]: Metadata for range validation.
        """
        yield Le(self.max_length)
        yield Ge(self.min_length)


class Integer64(GroupedMetadata):
    """A signed integer in the range
    -9,223,372,036,854,775,808 to +9,223,372,036,854,775,807 (64-bit).
    This type is defined to allow for record/time counters that can get very large"""

    pattern = re.compile(r"^[0]|[-+]?[1-9][0-9]*$")

    min_length: int = -9223372036854775807
    max_length: int = 9223372036854775807
    __visit_name__ = "integer64"

    def __iter__(self) -> Iterator[BaseMetadata]:
        """
        Yield metadata for Integer64 validation.

        Returns:
            Iterator[BaseMetadata]: Metadata for range validation.
        """
        yield Le(self.max_length)
        yield Ge(self.min_length)


@dataclass(frozen=True, **SLOTS)
class UnsignedInt(Integer):
    """Any non-negative integer in the range 0..2,147,483,647"""

    regex: re.Pattern = re.compile(r"^[0]|([1-9][0-9]*)$")
    __visit_name__: str = "unsignedInt"
    min_length: int = 0


@dataclass(frozen=True, **SLOTS)
class PositiveInt(UnsignedInt):
    """Any positive integer in the range 1..2,147,483,647"""

    regex: re.Pattern = re.compile(r"^\+?[1-9][0-9]*$")
    __visit_name__: str = "positiveInt"
    min_length: int = 1


@dataclass(frozen=True, **SLOTS)
class PatternConstraint(GroupedMetadata):
    if TYPE_CHECKING:
        pattern: re.Pattern

    def __iter__(self) -> Iterator[BaseMetadata]:
        """
        Yield metadata for pattern validation.

        Returns:
            Iterator[BaseMetadata]: Metadata containing the regex pattern.
        """
        yield pydantic_general_metadata(pattern=self.pattern.pattern)


class Uri(PatternConstraint):
    """A Uniform Resource Identifier Reference (RFC 3986 ).
    Note: URIs are case sensitive.
    For UUID (urn:uuid:53fefa32-fcbb-4ff8-8a92-55ee120877b7)
    use all lowercase xs:anyURI A JSON string - a URI
    Regex: \\S* (This regex is very permissive, but URIs must be valid.
    Implementers are welcome to use more specific regex statements
    for a URI in specific contexts)
    URIs can be absolute or relative, and may have an optional fragment identifier
    This data type can be bound to a ValueSet"""

    __visit_name__ = "uri"
    pattern = re.compile(r"\S*")


class Oid(PatternConstraint):
    """An OID represented as a URI (RFC 3001 ); e.g. urn:oid:1.2.3.4.5"""

    __visit_name__ = "oid"
    pattern = re.compile(r"^urn:oid:[0-2](\.(0|[1-9][0-9]*))+$")


class Uuid:
    """A UUID (aka GUID) represented as a URI (RFC 4122 );
    e.g. urn:uuid:c757873d-ec9a-4326-a141-556f43239520"""

    __visit_name__ = "uuid"


class Canonical(Uri):
    """A URI that refers to a resource by its canonical URL.
    The canonical type differs from a uri in that it has special meaning in this
    specification, and in that it may have a version appended, separated by a
    vertical bar (|).
    Note that the type canonical is not used for the actual canonical URLs that are
    the target of these references, but for the URIs that refer to them, and may
    have the version suffix in them. Like other URIs, elements of type canonical
    may also have #fragment references"""

    __visit_name__ = "canonical"


@dataclass(frozen=True, **SLOTS)
class Url:
    """A Uniform Resource Locator (RFC 1738 ).
    Note URLs are accessed directly using the specified protocol.
    Common URL protocols are http{s}:, ftp:, mailto: and mllp:,
    though many others are defined"""

    path_pattern = re.compile(
        r"^/(?P<resourceType>[A-Z][A-Za-z0-9]*)(/[A-Za-z0-9\-.#_]+)*$"
    )
    __visit_name__ = "url"

    @classmethod
    def _validate_url(  # type: ignore
        cls,
        input_value: PydanticUrl | str,
        validator: Callable[[Any], Any],
    ) -> PydanticUrl | str:
        """
        Validate a URL string or object, allowing for FHIR relative references.

        Args:
            input_value: The value to validate.
            validator: The inner Pydantic URL validator.

        Returns:
            PydanticUrl | str: The validated URL or relative reference.
        """
        if isinstance(input_value, PydanticUrl):
            return input_value

        if input_value in FHIR_PRIMITIVES:
            return input_value

        try:
            return validator(input_value)
        except ValidationError:
            # Handle FHIR relative paths
            if not isinstance(input_value, str):
                raise
            if not input_value.startswith("/"):
                regex_match = cls.path_pattern.match("/" + input_value)
            else:
                regex_match = cls.path_pattern.match(input_value)

            if regex_match is not None:
                resource_type = regex_match.groupdict().get("resourceType", "")
                if re.match(r"^[A-Za-z0-9\-.#]+$", resource_type):
                    return input_value
            raise

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Return a Pydantic CoreSchema with the url validation.
        """
        inner_schema = core_schema.url_schema()

        def _validate(
            input_value: Any,
            validator: Callable[[Any], Any],
            _validation_info: core_schema.ValidationInfo,
        ) -> Any:
            """
            Internal validation hook for URL types.
            """
            if isinstance(input_value, PydanticUrl):
                return str(input_value)
            res = cls._validate_url(input_value, validator)
            return (
                input_value
                if isinstance(input_value, str)
                else str(res)
                if isinstance(res, PydanticUrl)
                else res
            )

        return core_schema.with_info_wrap_validator_function(
            _validate,
            inner_schema,
        )


class Markdown(PatternConstraint):
    """
    A FHIR string (see above) that may contain Markdown syntax for optional
    processing by a Markdown presentation engine, in the GFM extension of
    CommonMark format
    """

    __visit_name__ = "markdown"
    pattern = re.compile(r"\s*(\S|\s)*")


class Xhtml:  # type:ignore
    __visit_name__ = "xhtml"


FHIR_DATE_PARTS = re.compile(r"(?P<year>\d{4})(-(?P<month>\d{2}))?(-(?P<day>\d{2}))?$")


@dataclass(frozen=True, **SLOTS)
class Date:
    """A date, or partial date (e.g. just year or year + month)
    as used in human communication. The format is YYYY, YYYY-MM, or YYYY-MM-DD,
    e.g. 2018, 1973-06, or 1905-08-23.
    There SHALL be no time zone. Dates SHALL be valid dates"""

    pattern = re.compile(
        r"([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|"
        r"[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2]"
        r"[0-9]|3[0-1]))?)?"
    )
    __visit_name__ = "date"

    @classmethod
    def produce_inner_schema(cls):
        """ """
        return core_schema.date_schema()

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Pydantic CoreSchema with the FHIR Date, DateTime, Time and
        Instant validation.

        Args:
            source_type: The source type to be converted.
            handler: The handler to get the CoreSchema.

        Returns:
            A Pydantic CoreSchema with the FHIR resource validation.

        """

        # inner_schema = cls.produce_inner_schema(source_type, handler)
        def _serialize(
            value: datetime.date | datetime.datetime | datetime.time | str,
            info: core_schema.SerializationInfo,
        ) -> datetime.date | datetime.datetime | datetime.time | str:
            if isinstance(value, str):
                return value
            if info.mode == "json":
                return value.isoformat()
            return value

        return core_schema.with_info_wrap_validator_function(
            cls._validate,
            cls.produce_inner_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize,
                info_arg=True,
                when_used="always",
            ),
        )

    @classmethod
    def _validate(
        cls,
        input_value: PydanticUrl | str,
        validator: Callable[[PydanticUrl | str], Any],
        _validation_info: core_schema.ValidationInfo,
    ) -> datetime.date | str:
        """
        Validate a date from the provided date or str value.

        Args:
            input_value: The date value to be validated.
        Returns:
            Date or str.
        """
        if not isinstance(input_value, str):
            # default handler
            return validator(input_value)

        if not cls.pattern.fullmatch(input_value):
            raise ValueError(
                f"{cls.__name__} value string does not match regex pattern."
            )

        date_match = FHIR_DATE_PARTS.match(input_value)
        if date_match and not date_match.groupdict().get("day"):
            # It's not a full date (e.g., YYYY or YYYY-MM)
            if (
                date_match.groupdict().get("month")
                and int(date_match.groupdict()["month"]) > 12
            ):
                raise ValueError(f"Invalid month in {cls.__name__}")
            return input_value

        return validator(input_value)


class DateTime(Date):
    """A date, date-time or partial date (e.g. just year or year + month) as used
    in human communication. The format is YYYY, YYYY-MM, YYYY-MM-DD or
    YYYY-MM-DDThh:mm:ss+zz:zz, e.g. 2018, 1973-06, 1905-08-23,
    2015-02-07T13:28:17-05:00 or 2017-01-01T00:00:00.000Z.
    If hours and minutes are specified, a time zone SHALL be populated.
    Seconds must be provided due to schema type constraints but may be
    zero-filled and may be ignored at receiver discretion.
    Dates SHALL be valid dates. The time "24:00" is not allowed.
    Leap Seconds are allowed - see below"""

    pattern = re.compile(
        r"([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|"
        r"[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|"
        r"3[0-1])(T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|"
        r"60)(\.[0-9]+)?(Z|([+\-])((0[0-9]|"
        r"1[0-3]):[0-5][0-9]|14:00)))?)?)?"
    )
    __visit_name__ = "dateTime"

    @classmethod
    def produce_inner_schema(cls):
        """ """
        return core_schema.datetime_schema()

    @classmethod
    def _validate(
        cls,
        input_value: PydanticUrl | str,
        validator: Callable[[PydanticUrl | str], Any],
        _validation_info: core_schema.ValidationInfo,
    ) -> datetime.date | datetime.datetime | str:
        """
        Validate a datetime from the provided datetime, date or str value.

        Args:
            input_value: The datetime, date or str value to be validated.
        Returns:
            Datetime, date or str.
        """
        validated_data = super()._validate(input_value, validator, _validation_info)

        if isinstance(validated_data, str):
            # A partial date
            return validated_data

        if type(input_value) is datetime.date:
            # The date has been successfully validated. As the validated_value will
            # be a datetime with a time component of 00:00:00, just return the
            # input date.
            return input_value

        if isinstance(input_value, str) and isinstance(
            validated_data, datetime.datetime
        ):
            if "T" in input_value and validated_data.tzinfo is None:
                # a datetime with time MUST have a timezone
                raise ValueError(
                    "DateTime must be timezone aware if it has a time component."
                )
            if "T" not in input_value and validated_data.time():
                # a datetime without time MUST NOT have a time component
                # so extract the date part only
                validated_data = validated_data.date()

        if isinstance(input_value, datetime.datetime):
            if input_value.tzinfo is None:
                # datetime values have time, even if 00:00, so MUST have a timezone
                raise ValueError("DateTime must be timezone aware.")

        return validated_data


class Instant(DateTime):
    """An instant in time in the format YYYY-MM-DDThh:mm:ss.sss+zz:zz
    (e.g. 2015-02-07T13:28:17.239+02:00 or 2017-01-01T00:00:00Z).
    The time SHALL specify at least to the second and SHALL include a time zone.
    Note: This is intended for when precisely observed times are required
    (typically system logs etc.), and not human-reported times - for those,
    use date or dateTime (which can be as precise as instant,
    but is not required to be). instant is a more constrained dateTime

    Note: This type is for system times, not human times (see date and dateTime below).
    """

    pattern = re.compile(
        r"([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|"
        r"[1-9]000)-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|"
        r"3[0-1])T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]"
        r"|60)(\.[0-9]+)?(Z|([+\-])((0[0-9]|"
        r"1[0-3]):[0-5][0-9]|14:00))"
    )
    __visit_name__ = "instant"

    @classmethod
    def _validate(
        cls,
        input_value: PydanticUrl | str,
        validator: Callable[[PydanticUrl | str], Any],
        _validation_info: core_schema.ValidationInfo,
    ) -> datetime.datetime:
        """
        Validate an instant from the provided timestamp or str value.

        Args:
            input_value: The instant value to be validated.
        Returns:
            Datetime
        """
        if isinstance(input_value, str):
            if not cls.pattern.fullmatch(input_value):
                raise ValueError("Instant value string does not match spec regex.")

        validated_value = validator(input_value)

        if not isinstance(validated_value, datetime.datetime):
            raise ValueError("Instant value does not parse to datetime.")

        if validated_value.tzinfo is None:
            # a datetime with time MUST have a timezone
            raise ValueError("Instant must be timezone aware.")

        return validated_value


@dataclass(frozen=True, **SLOTS)
class Time:
    """A time during the day, in the format hh:mm:ss.
    There is no date specified. Seconds must be provided due
    to schema type constraints but may be zero-filled and may
    be ignored at receiver discretion.
    The time "24:00" SHALL NOT be used. A time zone SHALL NOT be present.
    Times can be converted to a Duration since midnight."""

    pattern = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]+)?")
    __visit_name__ = "time"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Return a Pydantic CoreSchema with the Time validation.

        Args:
            source_type: The source type to be converted.
            handler: The handler to get the CoreSchema.

        Returns:
            A Pydantic CoreSchema with the time validation.

        """

        # inner_schema = cls.produce_inner_schema(source_type, handler)

        def _validate(
            input_value: PydanticUrl | str,
            _validator: Callable[[PydanticUrl | str], Any],
            _validation_info: core_schema.ValidationInfo,
        ) -> PydanticUrl | str:
            """
            Validate a Time value.

            Args:
                input_value: The value to validate.
                _validator: The inner validator (unused).
                _validation_info: Validation metadata.

            Returns:
                PydanticUrl | str: The validated time string.
            """
            if not isinstance(input_value, str):
                raise ValueError(f"Invalid {cls.__name__} format.")

            if not cls.pattern.fullmatch(input_value):
                raise ValueError(f"{cls.__name__} value string does not match regex.")

            return input_value

        return core_schema.with_info_wrap_validator_function(
            _validate,
            core_schema.time_schema(),
        )

    @classmethod
    def _validate_time(cls, input_value, validator):
        """ """
        if isinstance(input_value, str):
            if not cls.pattern.fullmatch(input_value):
                raise ValueError("Time value string does not match spec regex.")

        return validator(input_value)


# **************************************
# ****  FHIR Primitive Types ***********
# **************************************
# boolean
BooleanType = bool
FHIR_PRIMITIVES_MAPS[BooleanType] = "boolean"

# string
StringType = Annotated[str, String()]
FHIR_PRIMITIVES_MAPS[StringType] = "string"
FHIR_PRIMITIVES_MAPS[String] = "string"

# base64Binary
Base64BinaryType = Annotated[Base64Bytes, Base64Binary()]
FHIR_PRIMITIVES_MAPS[Base64BinaryType] = "base64Binary"
FHIR_PRIMITIVES_MAPS[Base64Binary] = "base64Binary"

# code
CodeType = Annotated[str, Code()]
FHIR_PRIMITIVES_MAPS[CodeType] = "code"
FHIR_PRIMITIVES_MAPS[Code] = "code"

# id
IdType = Annotated[str, Id(), Field(max_length=ID_MAX_LENGTH)]
FHIR_PRIMITIVES_MAPS[IdType] = "id"
FHIR_PRIMITIVES_MAPS[Id] = "id"

# decimal
DecimalType = Annotated[decimal.Decimal, Decimal()]
FHIR_PRIMITIVES_MAPS[DecimalType] = "decimal"
FHIR_PRIMITIVES_MAPS[Decimal] = "decimal"

# integer
IntegerType = Annotated[int, Integer(), Field(ge=-2147483648, le=2147483647)]
FHIR_PRIMITIVES_MAPS[IntegerType] = "integer"
FHIR_PRIMITIVES_MAPS[Integer] = "integer"

# integer64
Integer64Type = Annotated[int, Integer64()]
FHIR_PRIMITIVES_MAPS[Integer64Type] = "integer64"
FHIR_PRIMITIVES_MAPS[Integer64] = "integer64"

# unsignedInt
UnsignedIntType = Annotated[int, UnsignedInt()]
FHIR_PRIMITIVES_MAPS[UnsignedIntType] = "unsignedInt"
FHIR_PRIMITIVES_MAPS[UnsignedInt] = "unsignedInt"

# positiveInt
PositiveIntType = Annotated[int, PositiveInt()]
FHIR_PRIMITIVES_MAPS[PositiveIntType] = "positiveInt"
FHIR_PRIMITIVES_MAPS[PositiveInt] = "positiveInt"

# uri
UriType = Annotated[str, Uri()]
FHIR_PRIMITIVES_MAPS[UriType] = "uri"
FHIR_PRIMITIVES_MAPS[Uri] = "uri"

# canonical
CanonicalType = Annotated[str, Canonical()]
FHIR_PRIMITIVES_MAPS[CanonicalType] = "canonical"
FHIR_PRIMITIVES_MAPS[Canonical] = "canonical"

# oid
OidType = Annotated[str, Oid()]
FHIR_PRIMITIVES_MAPS[OidType] = "oid"
FHIR_PRIMITIVES_MAPS[Oid] = "oid"

# uuid
UuidType = UUID4
FHIR_PRIMITIVES_MAPS[UuidType] = "uuid"

# url
UrlType = Annotated[AnyUrl | str, Url()]
FHIR_PRIMITIVES_MAPS[UrlType] = "url"
FHIR_PRIMITIVES_MAPS[Url] = "url"

# markdown
MarkdownType = Annotated[str, Markdown()]
FHIR_PRIMITIVES_MAPS[MarkdownType] = "markdown"
FHIR_PRIMITIVES_MAPS[Markdown] = "markdown"

# xhtml
XhtmlType = Annotated[str, Xhtml()]
FHIR_PRIMITIVES_MAPS[XhtmlType] = "xhtml"
FHIR_PRIMITIVES_MAPS[Xhtml] = "xhtml"

# date
DateType = Annotated[datetime.date, Date()]
FHIR_PRIMITIVES_MAPS[DateType] = "date"
FHIR_PRIMITIVES_MAPS[Date] = "date"

# dateTime
DateTimeType = Annotated[datetime.datetime, DateTime()]
FHIR_PRIMITIVES_MAPS[DateTimeType] = "dateTime"
FHIR_PRIMITIVES_MAPS[DateTime] = "dateTime"

# instant
InstantType = Annotated[datetime.datetime, Instant()]
FHIR_PRIMITIVES_MAPS[InstantType] = "instant"
FHIR_PRIMITIVES_MAPS[Instant] = "instant"

# time
TimeType = Annotated[datetime.time, Time()]
FHIR_PRIMITIVES_MAPS[TimeType] = "time"
FHIR_PRIMITIVES_MAPS[Time] = "time"
