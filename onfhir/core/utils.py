"""
This module provides utility functions for introspecting Pydantic fields
and identifying their corresponding FHIR types, versions, and encoding requirements.
"""

import importlib
from functools import lru_cache
from typing import Any, get_args, get_origin

from pydantic.fields import FieldInfo
from pydantic.types import Base64Encoder, EncodedBytes

from .constraints import (
    FHIR_PRIMITIVES_MAPS,
    FHIR_TYPES_MAPS,
    FHIR_VERSIONS,
    PYTHON_PRIMITIVES,
)

__all__ = [
    "is_primitive_type",
    "get_fhir_type_name",
    "is_list_type",
    "get_base64_encoder",
]


def import_string(dotted_path: str) -> Any:
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path.

    Args:
        dotted_path: A string representing the full path to a class or function
            (e.g., 'onfhir.R4.models.Patient').

    Returns:
        Any: The imported class or attribute.

    Raises:
        ImportError: If the module path is invalid or the attribute is not found.

    Example:
        >>> cls = import_string('datetime.datetime')
        >>> cls.now()
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as e:
        raise ImportError(f"{dotted_path} doesn't look like a module path") from e

    module = importlib.import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as e:
        raise ImportError(
            f"Module '{module_path}' does not define a '{class_name}' attribute"
        ) from e


@lru_cache(maxsize=1024)
def _is_primitive_type(annotation: Any) -> bool:
    """
    Recursively check if a type annotation represents a FHIR primitive type.

    Args:
        annotation: The type annotation to check (e.g., str, Optional[int]).

    Returns:
        bool: True if the annotation represents a primitive FHIR type.
    """
    origin = get_origin(annotation)

    # Base case: directly in the primitive map
    if origin is None:
        return annotation in FHIR_PRIMITIVES_MAPS

    # A list is a collection, not a primitive, even if its elements are.
    if origin is list:
        return False

    # Handle Union/Optional: return True if any part (except None) is a primitive
    args = get_args(annotation)
    return any(_is_primitive_type(arg) for arg in args if arg is not type(None))


def is_primitive_type(field: FieldInfo) -> bool:
    """
    Determine if a Pydantic field is annotated as a FHIR primitive type.

    Args:
        field: The Pydantic FieldInfo object to inspect.

    Returns:
        bool: True if the field is a FHIR primitive.

    Example:
        >>> field = FieldInfo(annotation=str)
        >>> is_primitive_type(field)
        True
    """
    return _is_primitive_type(field.annotation)


@lru_cache(maxsize=1024)
def _is_list_type(annotation: Any) -> bool:
    """
    Recursively check if a type annotation represents a list.

    Args:
        annotation: The type annotation to check.

    Returns:
        bool: True if the annotation is a list type.
    """
    origin = get_origin(annotation)
    if origin is list:
        return True

    # Check inside Optional/Union (e.g., Optional[list[str]])
    args = get_args(annotation)
    return any(_is_list_type(arg) for arg in args if arg is not type(None))


def is_list_type(field: FieldInfo) -> bool:
    """
    Determine if a Pydantic field is a list type.

    Args:
        field: The Pydantic FieldInfo object to inspect.

    Returns:
        bool: True if the field is a list.

    Example:
        >>> field = FieldInfo(annotation=list[str])
        >>> is_list_type(field)
        True
    """
    return _is_list_type(field.annotation)


def _get_fhir_type_from_annotation(
    annotation: Any, metadata: list[Any], version_prefix: str = ""
) -> Any:
    """
    Internal helper to resolve the FHIR type from annotation and metadata.

    Args:
        annotation: The type annotation to resolve.
        metadata: List of Pydantic field metadata (Annotated items).
        version_prefix: Optional prefix for FHIR versioning (e.g., 'R4.').

    Returns:
        Any: The resolved FHIR type class or string name, or None if not found.
    """

    def resolve(anno):
        # 1. Check if it's a known FHIR primitive
        if anno in FHIR_PRIMITIVES_MAPS:
            # For ambiguous Python types (like str), check metadata
            # for the specific FHIR primitive class
            if anno in PYTHON_PRIMITIVES:
                for meta in metadata:
                    if meta.__class__ in FHIR_PRIMITIVES_MAPS:
                        return meta.__class__
            return anno

        # 2. Check if it's a known FHIR complex type/resource
        try:
            if f"{version_prefix}{anno.__name__}" in FHIR_TYPES_MAPS:
                return anno.__name__
        except AttributeError:
            pass

        return None

    # Try direct resolution
    result = resolve(annotation)
    if result is not None:
        return result

    # Handle Union/Optional/Generic types
    origin = get_origin(annotation)
    if origin is not None:
        for arg in get_args(annotation):
            # Recursively find the FHIR type (ignoring None)
            if arg is not type(None):
                result = _get_fhir_type_from_annotation(arg, metadata, version_prefix)
                if result is not None:
                    return result

    return None


def get_fhir_type_name(field: FieldInfo, prefix: str = "") -> str:
    """
    Retrieve the official FHIR string name for a field (e.g., 'string', 'Patient').

    Args:
        field: The Pydantic FieldInfo object to inspect.
        prefix: Optional FHIR version prefix.

    Returns:
        str: The FHIR type name.

    Raises:
        ValueError: If the FHIR type cannot be determined or found in mappings.

    Example:
        >>> field = FieldInfo(annotation=str)
        >>> get_fhir_type_name(field)
        'string'
    """
    fhir_type = _get_fhir_type_from_annotation(
        field.annotation, field.metadata, version_prefix=prefix
    )

    if fhir_type is None:
        raise ValueError(f"Could not determine FHIR type for field: {field}")

    # Map to primitive string name
    if fhir_type in FHIR_PRIMITIVES_MAPS:
        return FHIR_PRIMITIVES_MAPS[fhir_type]

    # Map to complex type name via imported class
    mapping_key = f"{prefix}{fhir_type}"
    if mapping_key in FHIR_TYPES_MAPS:
        cls = import_string(FHIR_TYPES_MAPS[mapping_key])
        return cls.get_resource_type()

    raise ValueError(f"FHIR type '{fhir_type}' not found in mapping.")


@lru_cache(maxsize=1024)
def determine_version_prefix(class_or_module_path: str) -> str:
    """
    Extract the FHIR version prefix from a module path or class name.

    Args:
        class_or_module_path: The path string to search.

    Returns:
        str: The version prefix (e.g., 'R4.') or an empty string.

    Example:
        >>> determine_version_prefix('onfhir.R4.models.Patient')
        'R4.'
    """
    found = FHIR_VERSIONS.search(class_or_module_path)
    if found:
        return f"{found.group(1)}."
    return ""


def get_base64_encoder(field_info: FieldInfo) -> Any:
    """
    Identify the appropriate Base64 encoder for a field if it contains binary data.

    Args:
        field_info: The Pydantic FieldInfo object.

    Returns:
        Any: The encoder class or instance, or None if not applicable.
    """
    for enc in field_info.metadata:
        if isinstance(enc, EncodedBytes):
            return enc

    # Fallback to class-name based detection
    if "Base64Binary" in str(field_info.annotation):
        return Base64Encoder

    return None
