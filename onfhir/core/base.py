import logging
from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast, get_args, get_origin

from pydantic import GetCoreSchemaHandler, ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError, core_schema

from .abstract import FHIRAbstract
from .constraints import FHIR_TYPES_MAPS, FHIR_VERSIONS
from .utils import import_string

LOGGER = logging.getLogger(__name__)

__all__ = [
    "FHIRBase",
    "create_fhir_type",
    "create_fhir_element_or_resource_type",
]


class FHIRBase:
    """The base type aka validator for FHIR resource model.

    ```py
    from fhir.resources.core.fhirabstractmodel import FHIRAbstract
    from fhir.resources.core.types import create_fhirabstractmodel
    from pydantic import Field

    class Patient(FHIRAbstract):
        __resource_type__ = "Patient"
        name: str = Field(..., title="Patient name")

    PatientType = create_fhir_type('PatientType', 'fhir.resources.patient.Patient')

    class CarePlan(FHIRAbstract):
        __resource_type__ = "CarePlan"
        subject: PatientType = Field(..., title="Patient")

    care_plan = CarePlan(subject={'name': 'Petter paddle'})
    print(care_plan)
    #>  subject=Patient(name='Petter paddle')
    ```
    """

    if TYPE_CHECKING:
        _model_class: str
        _version_prefix: str
    else:
        __slots__ = ("_model_class", "_version_prefix")

    @classmethod
    @lru_cache(typed=True)
    def get_model_class(cls) -> type[FHIRAbstract]:
        """
        Import and return the target FHIR model class.

        Returns:
            type[FHIRAbstract]: The FHIR model class.
        """
        return import_string(cls._model_class)

    @classmethod
    @lru_cache(typed=True)
    def produce_inner_schema(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema | None:
        """
        Produce the inner Pydantic core schema for the FHIR resource.

        Args:
            source_type: The type being validated.
            handler: The core schema handler.

        Returns:
            core_schema.CoreSchema | None: The generated schema or None.
        """
        if isinstance(source_type, cls):
            # Generate schema from the specific target class instead of FHIRAbstract
            return handler.generate_schema(cls.get_model_class())

        if get_origin(source_type) is not None:
            for arg_type in get_args(source_type):
                inner_schema = cls.produce_inner_schema(arg_type, handler)
                if inner_schema:
                    return inner_schema
        return None

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type["FHIRBase"], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Return a Pydantic CoreSchema with the FHIR resource validation.

        Args:
            source_type: The source type to be converted.
            handler: The handler to get the CoreSchema.

        Returns:
            A Pydantic CoreSchema with the FHIR resource validation.

        """
        inner_schema = cls.produce_inner_schema(source_type, handler)  # type: ignore
        if inner_schema is None:
            # show warning log
            inner_schema = core_schema.any_schema()

        def serialize(
            value: Any, info: core_schema.SerializationInfo
        ) -> dict[str, Any]:
            """Serialize the FHIR model instance."""
            if TYPE_CHECKING:
                value = cast(FHIRAbstract, value)
            # Use the requested mode (json or python)
            return value.model_dump(mode=info.mode)

        def _validate(
            input_value: bytes | dict | str | FHIRAbstract,
            validator: Callable[[FHIRAbstract], Any],
            _validation_info: core_schema.ValidationInfo,
        ) -> FHIRAbstract:
            """
            Validate a FHIR resource from various input formats.

            Args:
                input_value: The value to validate (string, bytes, dict, or instance).
                validator: The inner Pydantic validator.
                _validation_info: Metadata about the validation process.

            Returns:
                FHIRAbstract: The validated model instance.
            """
            model_class = source_type.get_model_class()
            if TYPE_CHECKING:
                model_class = cast(type[FHIRAbstract], model_class)
            return validator(cls.fhir_model_validator(input_value, model_class))

        return core_schema.with_info_wrap_validator_function(
            _validate,
            inner_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize,
                info_arg=True,
                when_used="always",
            ),
        )

    @classmethod
    def fhir_model_validator(
        cls,
        value: bytes | dict | str | FHIRAbstract,
        model_class: type[FHIRAbstract],
    ) -> FHIRAbstract:
        """
        Validate and convert the input value into a FHIR model instance.

        Args:
            value: The input value (JSON string, bytes, dict, or model instance).
            model_class: The expected FHIR model class.

        Returns:
            FHIRAbstract: The validated model instance.

        Raises:
            ValidationError: If validation fails.
        """
        if value is None:
            LOGGER.debug("None value provided for %s", model_class)
            return value

        if isinstance(value, (str, bytes)):
            value = model_class.model_validate_json(value)
        elif isinstance(value, dict):
            value = model_class.model_validate(value)

        errors: list[InitErrorDetails] = []

        if not isinstance(value, model_class):
            error_type = PydanticCustomError(
                "model_validation_format",
                "Value expected to be an instance of {model_class}, but got {type}",
                {"model_class": model_class.__name__, "type": type(value).__name__},
            )
            errors.append(
                {
                    "type": error_type,
                    "loc": ("root",),
                    "input": value,
                }
            )

        if not errors:
            # Check resourceType consistency
            if model_class.get_resource_type() != value.get_resource_type():
                error_type = PydanticCustomError(
                    "model_validation_format",
                    'Expected resourceType "{expected}", but got "{actual}"',
                    {
                        "expected": model_class.get_resource_type(),
                        "actual": value.get_resource_type(),
                    },
                )
                errors.append(
                    {
                        "type": error_type,
                        "loc": ("root",),
                        "input": value,
                    }
                )

        if errors:
            raise ValidationError.from_exception_data(cls.__name__, errors)

        return value

    def __hash__(self) -> int:
        return hash(self._model_class)


class FHIRElementOrResourceBase(FHIRBase):
    """Special type of validator for FHIR Resource & Element model.
    There are many cases that value type is declared as ResourceType
    but expect any of FHIR resource that derived from Base Resource.
    Fx. domainresource.DomainResource.contained: typing.List[fhirtypes.ResourceType]
    """

    @classmethod
    def fhir_model_validator(
        cls,
        value: bytes | dict | str | FHIRAbstract,
        model_class: type[FHIRAbstract],
    ) -> FHIRAbstract:
        """
        Validate and resolve the specific FHIR model for polymorphic types.

        Args:
            value: The input value.
            model_class: The base FHIR model class (e.g., Resource or Element).

        Returns:
            FHIRAbstract: The resolved and validated model instance.
        """
        actual_model_class = model_class
        if isinstance(value, FHIRAbstract):
            actual_model_class = value.__class__
        elif isinstance(value, (str, bytes, dict)):
            # Determine the actual class from the resourceType
            data = value
            if isinstance(value, (str, bytes)):
                import json

                try:
                    data = json.loads(value)
                except Exception:
                    data = {}

            if isinstance(data, dict) and "resourceType" in data:
                type_key = f"{cls._version_prefix}{data['resourceType']}Type"
                if type_key in FHIR_TYPES_MAPS:
                    actual_model_class = import_string(FHIR_TYPES_MAPS[type_key])

        errors: list[InitErrorDetails] = []

        is_resource = (
            model_class.__name__ == "Resource"
            or model_class.__name__ == "FHIRAbstract"
            or issubclass(model_class, FHIRAbstract)
        )
        is_element = model_class.__name__ == "Element"

        if is_resource:
            if not actual_model_class.has_resource_base():
                error_type = PydanticCustomError(
                    "model_validation_format",
                    "Resource {model} must derive from 'Resource'.",
                    {"model": actual_model_class.__name__},
                )
                errors.append(
                    {
                        "type": error_type,
                        "loc": ("root",),
                        "input": actual_model_class,
                    }
                )

        elif is_element:
            if actual_model_class.has_resource_base():
                error_type = PydanticCustomError(
                    "model_validation_format",
                    "Resource {model} must derive from 'Element'.",
                    {"model": actual_model_class.__name__},
                )
                errors.append(
                    {
                        "type": error_type,
                        "loc": ("root",),
                        "input": actual_model_class,
                    }
                )
        else:
            error_type = PydanticCustomError(
                "model_validation_format",
                "Validator only allowed for 'Element' or 'Resource'.",
                {},
            )
            errors.append(
                {
                    "type": error_type,
                    "loc": ("root",),
                    "input": model_class,
                }
            )

        if errors:
            raise ValidationError.from_exception_data(cls.__name__, errors)

        return FHIRBase.fhir_model_validator(value, actual_model_class)


# factory function
def _create_fhir_type(
    class_name: str, model_class: str, base_class: type[FHIRBase]
) -> type[FHIRBase]:
    """
    Internal factory function to create a FHIR model type.

    Args:
        class_name: The name of the new validator class.
        model_class: The full import path of the FHIR model.
        base_class: The base validator class.

    Returns:
        type[FHIRBase]: The new validator class.
    """
    version_match = FHIR_VERSIONS.search(model_class)
    version_prefix = f"{version_match.group(1)}." if version_match else ""

    new_class = type(
        class_name,
        (base_class,),
        {"_model_class": model_class, "_version_prefix": version_prefix},
    )

    if TYPE_CHECKING:
        new_class = cast(type[FHIRBase], new_class)

    class_key = f"{version_prefix}{class_name}"
    if class_key not in FHIR_TYPES_MAPS:
        FHIR_TYPES_MAPS[class_key] = model_class

    return new_class


@lru_cache(maxsize=1024)
def create_fhir_type(class_name: str, model_class: str) -> type[FHIRBase]:
    """
    Create a FHIR model validator type.

    Args:
        class_name: The name of the new validator class.
        model_class: The full import path of the FHIR model.

    Returns:
        type[FHIRBase]: The new validator class.
    """
    return _create_fhir_type(class_name, model_class, FHIRBase)


@lru_cache(maxsize=1024)
def create_fhir_element_or_resource_type(
    class_name: str, model_class: str
) -> type[FHIRElementOrResourceBase]:
    """
    Create a FHIR Element or Resource validator type.

    Args:
        class_name: The name of the new validator class.
        model_class: The full import path of the FHIR model.

    Returns:
        type[FHIRElementOrResourceBase]: The new validator class.
    """
    return _create_fhir_type(class_name, model_class, FHIRElementOrResourceBase)
