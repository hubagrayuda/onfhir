from __future__ import annotations

import decimal
import inspect
import logging
from collections import OrderedDict
from collections.abc import Callable, Generator
from functools import lru_cache
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self, cast
from warnings import warn

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PydanticDeprecatedSince20,
    SerializationInfo,
    ValidationError,
    model_serializer,
    model_validator,
)
from pydantic.fields import FieldInfo
from pydantic_core import InitErrorDetails, PydanticCustomError
from typing_extensions import deprecated

from .constraints import HAS_XML_SUPPORT, HAS_YAML_SUPPORT
from .utils import get_base64_encoder, is_primitive_type

if HAS_XML_SUPPORT:
    from .xml_utils import xml_dumps, xml_loads

if HAS_YAML_SUPPORT:
    from .yaml_utils import yaml_dumps, yaml_loads

if TYPE_CHECKING:
    from pydantic.main import TupleGenerator

FHIR_COMMENTS_FIELD_NAME = "fhir_comments"
ROOT_KEY = "root"
LOGGER = logging.getLogger(__name__)

FHIRErrorCodes = Literal[
    "fhir-validation-missing-resource-type",
    "fhir-validation-wrong-resource-type",
    "model_field_validation.missing",
]


class FHIRAbstract(BaseModel):
    """Abstract base model class for all FHIR elements.

    Disclaimer: Any field that ends with ``__ext`` is **NOT** part of
    Resource StructureDefinition, instead used to enable Extensibility feature
    for FHIR Primitive Data Types.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
    )

    __resource_type__: ClassVar[str] = "__resource_type__"

    fhir_comments: str | list[str] | None = Field(
        default=None,
        alias="fhir_comments",
        json_schema_extra={"element_property": False},
    )

    def __init__(self, /, **data: Any) -> None:
        """
        Initialize the FHIR model.

        Args:
            data: The model data to initialize.

        Raises:
            ValueError: If __resource_type__ is not defined in the subclass.
            ValidationError: If the resource_type in data does not match the model.
        """
        if self.__resource_type__ is Ellipsis:
            raise ValueError("__resource_type__ must be defined in subclasses")

        resource_type = data.pop("resource_type", None)
        if "resourceType" in data and "resourceType" not in self.__class__.model_fields:
            resource_type = data.pop("resourceType", None)

        if resource_type is not None and resource_type != self.__resource_type__:
            expected_resource_type = self.__resource_type__
            error_type: PydanticCustomError = PydanticCustomError(
                "fhir-validation-wrong-resource-type",
                "``{module_name}.{class_name}`` expects resource type "
                "``{expected_resource_type}``, but got ``{resource_type}``. "
                "Make sure resource type name is correct and right "
                "ModelClass has been chosen.",
                {
                    "module_name": self.__class__.__module__,
                    "class_name": self.__class__.__name__,
                    "expected_resource_type": expected_resource_type,
                    "resource_type": resource_type,
                },
            )
            error_: InitErrorDetails = {
                "type": error_type,
                "loc": ("resource_type",),
                "input": resource_type,
            }
            raise ValidationError.from_exception_data(self.__class__.__name__, [error_])

        BaseModel.__init__(self, **data)

    @classmethod
    def element_properties(
        cls: type[FHIRAbstract],
    ) -> Generator[FieldInfo, None, None]:
        """
        Yield Pydantic FieldInfo objects for fields marked as FHIR elements.

        Yields:
            FieldInfo: The field metadata.
        """
        for field_info in cls.model_fields.values():
            if field_info.json_schema_extra.get("element_property", False):
                yield field_info

    @classmethod
    def elements_sequence(cls) -> list[str]:
        """
        Return the sequence of FHIR element names.
        If not overridden, returns all fields marked as element properties.
        """
        return [
            f.alias or n
            for n, f in cls.model_fields.items()
            if (
                isinstance(f.json_schema_extra, dict)
                and f.json_schema_extra.get("element_property")
            )
        ]

    @classmethod
    def summary_element_properties(
        cls: type[FHIRAbstract],
    ) -> Generator[FieldInfo, None, None]:
        """
        Yield FieldInfo objects for fields marked as FHIR summary elements.

        Yields:
            FieldInfo: The field metadata.
        """
        for field_info in cls.model_fields.values():
            if field_info.json_schema_extra.get(
                "element_property", False
            ) and field_info.json_schema_extra.get("summary_element_property", False):
                yield field_info

    @classmethod
    def summary_elements_sequence(cls) -> list[str]:
        """
        Return the sequence of FHIR summary element names.
        """
        return [
            f.alias or n
            for n, f in cls.model_fields.items()
            if (
                isinstance(f.json_schema_extra, dict)
                and f.json_schema_extra.get("summary_element_property")
            )
        ]

    @classmethod
    @lru_cache(maxsize=1024, typed=True)
    def has_resource_base(cls) -> bool:
        """
        Check if the model inherits from a FHIR 'Resource' class.
        """
        for mro_class in inspect.getmro(cls):
            if mro_class.__name__ == "Resource" or (
                getattr(mro_class, "__resource_type__", None)
                not in (None, "__resource_type__", Ellipsis)
            ):
                return True
        return False

    @classmethod
    @lru_cache(maxsize=None, typed=True)
    def get_resource_type(cls: type[FHIRAbstract]) -> str:
        """
        Return the FHIR resource type name.

        Returns:
            str: The resource type.
        """
        return cls.__resource_type__

    def get_model_class(self) -> type[FHIRAbstract]:
        """
        Return the class of the model instance.

        Returns:
            type[FHIRAbstract]: The model class.
        """
        return self.__class__

    @classmethod
    @lru_cache(maxsize=None, typed=True)
    def get_alias_mapping(cls: type[FHIRAbstract]) -> dict[str, str]:
        """
        Create a mapping between FHIR aliases and internal Python field names.

        Returns:
            dict[str, str]: Map of alias -> field_name.
        """
        aliases = cls.elements_sequence()
        return {
            field_info.alias or field_name: field_name
            for field_name, field_info in cls.model_fields.items()
            if (field_info.alias or field_name) in aliases
        }

    @classmethod
    def get_json_encoder(cls) -> Callable[[Any], Any]:
        """
        Return the Pydantic JSON serializer function.

        Returns:
            Callable: The serialization function.
        """
        return cls.__pydantic_serializer__.to_json

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        include: Any = None,
        exclude: Any = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        serialize_as_any: bool = False,
        # FHIR custom
        exclude_comments: bool = False,
        summary_only: bool = False,
    ) -> str:
        """
        Generate a JSON representation of the model.

        Args:
            indent: Indentation for the JSON output.
            include: Fields to include in the output.
            exclude: Fields to exclude from the output.
            context: Additional context for serialization.
            by_alias: Whether to use field aliases as keys.
            exclude_unset: Whether to exclude fields that were not set.
            exclude_defaults: Whether to exclude fields with default values.
            exclude_none: Whether to exclude fields with None values.
            round_trip: Whether to serialize for round-tripping.
            warnings: Whether to output serialization warnings.
            serialize_as_any: Whether to serialize as 'Any' type.
            exclude_comments: Whether to exclude FHIR comments.
            summary_only: Whether to include only summary elements.

        Returns:
            str: The JSON string representation.
        """
        if context is None:
            context = {}
        context.setdefault("exclude_comments", exclude_comments)
        context.setdefault("summary_only", summary_only)

        return BaseModel.model_dump_json(
            self,
            indent=indent,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    def model_dump_yaml(
        self,
        *,
        indent: int | None = None,
        include: Any = None,
        exclude: Any = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        serialize_as_any: bool = False,
        # FHIR custom
        exclude_comments: bool = False,
        summary_only: bool = False,
    ) -> str:
        """
        Generate a YAML representation of the model.

        Args:
            indent: Indentation for the YAML output.
            include: Fields to include.
            exclude: Fields to exclude.
            context: Serialization context.
            by_alias: Use aliases as keys.
            exclude_unset: Exclude fields not set.
            exclude_defaults: Exclude fields with default values.
            exclude_none: Exclude None values.
            round_trip: Serialize for round-tripping.
            warnings: Output serialization warnings.
            serialize_as_any: Serialize as 'Any' type.
            exclude_comments: Exclude FHIR comments.
            summary_only: Include only summary elements.

        Returns:
            str: The YAML string representation.
        """
        if not HAS_YAML_SUPPORT:
            raise ModuleNotFoundError(
                "You need to install the 'PyYAML' package to use this method."
            )

        model_dict = self.model_dump(
            mode="python",
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
            exclude_comments=exclude_comments,
            summary_only=summary_only,
        )

        return yaml_dumps(
            model_dict, indent=indent, return_bytes=False, sort_keys=False
        )

    def model_dump_xml(
        self,
        *,
        pretty_print: bool = False,
        xml_declaration: bool = True,
        # FHIR custom
        exclude_comments: bool = False,
        summary_only: bool = False,
    ) -> str:
        """
        Generate an XML representation of the model.

        Args:
            pretty_print: Whether to format the XML.
            xml_declaration: Whether to include the XML header.
            exclude_comments: Whether to exclude FHIR comments.
            summary_only: Whether to include only summary elements.

        Returns:
            str: The XML string representation.
        """
        if not HAS_XML_SUPPORT:
            raise ModuleNotFoundError(
                "You need to install the 'lxml' package to use this method."
            )

        return xml_dumps(
            self,
            pretty_print=pretty_print,
            xml_declaration=xml_declaration,
            with_comments=not exclude_comments,
            summary_only=summary_only,
        )

    def model_dump(
        self,
        *,
        mode: Literal["json", "python"] | str = "python",
        include: Any = None,
        exclude: Any = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        serialize_as_any: bool = False,
        # FHIR custom
        exclude_comments: bool = False,
        summary_only: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a dictionary representation of the model.

        Args:
            mode: The serialization mode.
            include: Fields to include.
            exclude: Fields to exclude.
            context: Serialization context.
            by_alias: Use aliases as keys.
            exclude_unset: Exclude fields not set.
            exclude_defaults: Exclude fields with default values.
            exclude_none: Exclude None values.
            round_trip: Serialize for round-tripping.
            warnings: Output serialization warnings.
            serialize_as_any: Serialize as 'Any' type.
            exclude_comments: Exclude FHIR comments.
            summary_only: Include only summary elements.

        Returns:
            dict[str, Any]: The dictionary representation.
        """
        if context is None:
            context = {}
        context.setdefault("exclude_comments", exclude_comments)
        context.setdefault("summary_only", summary_only)

        return BaseModel.model_dump(
            self,
            mode=mode,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    @deprecated(
        "The `dict` method is deprecated; use `model_dump` instead.", category=None
    )
    def dict(
        self,
        *,
        mode: Literal["json", "python"] | str = "python",
        include: Any = None,
        exclude: Any = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        serialize_as_any: bool = False,
        # FHIR custom
        exclude_comments: bool = False,
        summary_only: bool = False,
    ) -> dict[str, Any]:
        """
        Deprecated 'dict' method. Use 'model_dump' instead.
        """
        warn(
            "The `dict` method is deprecated; use `model_dump` instead.",
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return self.model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
            exclude_comments=exclude_comments,
            summary_only=summary_only,
        )

    @deprecated(
        "The `json` method is deprecated; use `model_dump_json` instead.", category=None
    )
    def json(
        self,
        *,
        indent: int | None = None,
        include: Any = None,
        exclude: Any = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        serialize_as_any: bool = False,
        # FHIR custom
        exclude_comments: bool = False,
        summary_only: bool = False,
    ) -> str:
        """
        Deprecated 'json' method. Use 'model_dump_json' instead.
        """
        warn(
            "The `json` method is deprecated; use `model_dump_json` instead.",
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return self.model_dump_json(
            indent=indent,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
            exclude_comments=exclude_comments,
            summary_only=summary_only,
        )

    @classmethod
    def model_validate_yaml(
        cls,
        yaml_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: Any | None = None,
    ) -> Self:
        """
        Validate the given YAML data against the Pydantic model.

        Args:
            yaml_data: The YAML data to validate.
            strict: Whether to enforce types strictly.
            context: Extra variables to pass to the validator.

        Returns:
            Self: The validated Pydantic model instance.

        Raises:
            ModuleNotFoundError: If 'PyYAML' is not installed.
            ValueError: If 'yaml_data' is not a valid YAML string.
        """
        if not HAS_YAML_SUPPORT:
            raise ModuleNotFoundError(
                "You need to install the 'PyYAML' package to use this method."
            )
        data = yaml_loads(yaml_data)
        return cls.model_validate(data, strict=strict, context=context)

    @classmethod
    def model_validate_xml(
        cls,
        xml_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: Any | None = None,
        xml_parser: Any | None = None,
    ) -> Self:
        """
        Validate the given XML data against the Pydantic model.

        Args:
            xml_data: The XML data to validate.
            strict: Whether to enforce types strictly.
            context: Extra variables to pass to the validator.
            xml_parser: Custom XML parser to use.

        Returns:
            Self: The validated Pydantic model instance.

        Raises:
            ModuleNotFoundError: If 'lxml' is not installed.
            ValueError: If 'xml_data' is not valid XML.
        """
        if not HAS_XML_SUPPORT:
            raise ModuleNotFoundError(
                "You need to install the 'lxml' package to use this method."
            )
        if TYPE_CHECKING and xml_parser is not None:
            from lxml.etree import XMLParser

            xml_parser = cast(XMLParser, xml_parser)

        model_instance = xml_loads(cls, xml_data, xml_parser=xml_parser)
        if TYPE_CHECKING:
            model_instance = cast(Self, model_instance)
        return model_instance

    # Serializers
    @model_serializer(mode="wrap", when_used="always", return_type=OrderedDict)
    def fhir_model_serializer(
        self,
        serialize: Callable[[Any], Any],
        info: SerializationInfo,
    ) -> OrderedDict:
        """
        Pydantic model serializer that ensures correct element sequencing.

        Args:
            serialize: The standard serialization function.
            info: Serialization metadata.

        Returns:
            OrderedDict: The serialized model data in sequence.
        """
        return OrderedDict(self._fhir_iter(serialize, info))

    # Private methods
    def _fhir_iter(
        self,
        serialize: Callable[[Any], Any],
        info: SerializationInfo,
    ) -> TupleGenerator:
        """
        Internal iterator for FHIR serialization.

        Args:
            serialize: The serialization function.
            info: Serialization metadata.

        Yields:
            tuple: (field_name, field_value)
        """
        if self.__class__.has_resource_base():
            yield "resourceType", self.__resource_type__

        context = info.context or {}
        summary_only = context.get("summary_only", False)
        exclude_comments = context.get("exclude_comments", False)

        alias_mapping = self.__class__.get_alias_mapping()
        summary_sequence = self.__class__.summary_elements_sequence()

        for prop_name in self.__class__.elements_sequence():
            if summary_only and prop_name not in summary_sequence:
                continue

            field_key = alias_mapping[prop_name]
            field_info = self.__class__.model_fields[field_key]
            is_primitive = is_primitive_type(field_info)
            dict_key = (field_info.alias or field_key) if info.by_alias else field_key
            value = getattr(self, field_key, None)

            if not is_primitive and value is not None:
                value = self._serialize_non_primitive_value(value, serialize, info)
            else:
                value = self._serialize_primitive_value(value, field_info)

            if value is not None or (info.exclude_none is False and value is None):
                yield dict_key, value

            # Handle primitive extensions/comments
            if is_primitive and not summary_only:
                extension_key = f"{field_key}__ext"
                extension_value = self.__dict__.get(extension_key, None)
                if extension_value is not None:
                    extension_value = self._serialize_non_primitive_value(
                        extension_value, serialize, info
                    )

                if extension_value is not None and len(extension_value) > 0:
                    extension_dict_key = (
                        self.__class__.model_fields[extension_key].alias
                        if info.by_alias
                        else extension_key
                    )
                    yield extension_dict_key, extension_value

        if not summary_only:
            comments = self.__dict__.get(FHIR_COMMENTS_FIELD_NAME, None)
            if comments is not None and not exclude_comments:
                yield FHIR_COMMENTS_FIELD_NAME, comments

    def _serialize_non_primitive_value(
        self,
        value: Any,
        serialize: Callable[[Any], Any],
        info: SerializationInfo,
    ) -> Any:
        """
        Serialize a non-primitive value (list, FHIR model, or other objects).

        Args:
            value: The value to serialize.
            serialize: The serialization function.
            info: Serialization metadata.

        Returns:
            Any: The serialized value.
        """
        if isinstance(value, list):
            if not value:
                return value
            return [
                self._serialize_non_primitive_value(item, serialize, info)
                for item in value
            ]

        if value is None:
            return value

        if isinstance(value, FHIRAbstract):
            return value.model_dump(
                mode=info.mode,
                by_alias=info.by_alias,
                exclude_none=info.exclude_none,
                exclude_comments=info.context.get("exclude_comments", False),
                summary_only=info.context.get("summary_only", False),
            )

        return serialize(value)

    def _serialize_primitive_value(
        self,
        value: Any,
        field_info: FieldInfo,
    ) -> Any:
        """
        Serialize a primitive value, handling Base64 and Decimal specifically.

        Args:
            value: The value to serialize.
            field_info: The field metadata.

        Returns:
            Any: The serialized primitive value.
        """
        if isinstance(value, list):
            if not value:
                return value
            return [self._serialize_primitive_value(item, field_info) for item in value]

        if value is None:
            return value

        if isinstance(value, (bytes, bytearray)):
            encoder_class = get_base64_encoder(field_info)
            if encoder_class:
                return encoder_class.encode(value)

        if isinstance(value, decimal.Decimal):
            exponent = value.as_tuple().exponent
            if (
                value.is_finite()
                and value == value.to_integral_value()
                and isinstance(exponent, int)
                and exponent >= 0
            ):
                return int(value)
            return float(value)

        return value

    @model_validator(mode="after")
    def validate_after_model_construction(self) -> Self:
        """
        Perform complex validation after model construction.

        Returns:
            Self: The validated model instance.
        """
        self._validate_required_primitive_elements()
        self._validate_one_of_many()
        return self

    def _validate_one_of_many(self) -> None:
        """
        Validate that only one of a set of mutually exclusive fields is present.
        (FHIR [x] choice elements).
        """
        one_of_many_fields = self.get_one_of_many_fields()
        if not one_of_many_fields:
            return

        for prefix, fields in one_of_many_fields.items():
            first_field = self.__class__.model_fields[fields[0]]
            assert first_field.json_schema_extra["one_of_many"] == prefix

            required = (
                first_field.json_schema_extra.get("one_of_many_required", False) is True
            )
            found_field = None

            for field_name in fields:
                if getattr(self, field_name, None) is not None:
                    if found_field:
                        raise ValueError(
                            f"Multiple values found for choice element '{prefix}': "
                            f"'{found_field}' and '{field_name}'."
                        )
                    found_field = field_name

            if required and not found_field:
                raise ValueError(
                    f"One of the following fields is required for '{prefix}': {fields}"
                )

    def _validate_required_primitive_elements(self) -> None:
        """
        Validate required primitive elements, allowing for extensions if missing.
        """
        required_fields = self.get_required_fields()
        if not required_fields:
            return

        missing_marker = object()
        errors: list[InitErrorDetails] = []
        alias_mapping = self.get_alias_mapping()

        for name, extension_name in required_fields:
            field_key = alias_mapping[name]
            field_info = self.__class__.model_fields[field_key]
            value = getattr(self, field_key, missing_marker)

            if value not in (missing_marker, None):
                continue

            extension_value = getattr(self, extension_name, missing_marker)
            missing_extension = True

            if extension_value not in (missing_marker, None):
                if isinstance(extension_value, dict):
                    missing_extension = not extension_value.get("extension")
                elif (
                    getattr(extension_value, "__resource_type__", None)
                    == "FHIRPrimitiveExtension"
                ):
                    if (
                        hasattr(extension_value, "extension")
                        and extension_value.extension
                    ):
                        missing_extension = False
                else:
                    if (
                        hasattr(extension_value, "extension")
                        and extension_value.extension
                    ):
                        missing_extension = False

            if missing_extension:
                error_type = PydanticCustomError(
                    "model_field_validation.missing",
                    "Value for the field '{field_name}' is required.",
                    {"field_name": field_info.alias},
                )
                errors.append(
                    {
                        "type": error_type,
                        "loc": (field_info.alias,),
                        "input": value if value is not missing_marker else None,
                    }
                )

        if errors:
            raise ValidationError.from_exception_data(self.__class__.__name__, errors)

    def get_required_fields(self) -> list[tuple[str, str]]:
        """This method should be overridden in each subclass.
        [("type", "type__ext")]"""
        return []

    def get_one_of_many_fields(self) -> dict[str, list[str]]:
        """This method should be override in subclasses to specify one set of fields

        return {
            "allowed": ["allowedMoney", "allowedString", "allowedUnsignedInt"],
            "used": ["usedMoney", "usedUnsignedInt"],
        }
        """
        return {}
