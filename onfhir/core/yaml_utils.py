"""
This module provides FHIR-compliant YAML serialization and deserialization utilities.
It uses a custom Dumper to ensure that special types (Decimal, Url, OrderedDict)
are represented correctly without polluting the global PyYAML state.
"""

from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic_core._pydantic_core import Url
from yaml import Node, ScalarNode, YAMLError, dump, load
from yaml.representer import SafeRepresenter

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader

__all__ = ["yaml_loads", "yaml_dumps"]


class FHIRRepresenter(SafeRepresenter):
    """
    Custom YAML representer for FHIR-specific and Pydantic types.
    """

    def represent_datetime(self, data: datetime) -> ScalarNode:
        """Represent datetime objects as ISO 8601 strings."""
        return self.represent_scalar(
            "tag:yaml.org,2002:timestamp",
            data.isoformat(),
        )

    def represent_decimal(self, data: Decimal) -> Node:
        """
        Represent Decimal objects as floats.
        Note: Converting to float may lose precision for extremely large/small decimals.
        """
        return self.represent_float(float(data))

    def represent_url(self, data: Url) -> Node:
        """Represent Pydantic Url objects as plain strings."""
        return self.represent_str(str(data))


class FHIRDumper(Dumper, FHIRRepresenter):
    """
    A dedicated YAML Dumper that includes FHIR-specific representers.
    """

    pass


# Register representers only on FHIRDumper to avoid global side effects
FHIRDumper.add_representer(datetime, FHIRRepresenter.represent_datetime)
FHIRDumper.add_representer(Decimal, FHIRRepresenter.represent_decimal)
FHIRDumper.add_representer(Url, FHIRRepresenter.represent_url)

# Treat OrderedDict as a regular dict to avoid Python-specific tags in YAML output
FHIRDumper.add_representer(OrderedDict, SafeRepresenter.represent_dict)


def yaml_loads(stream: Any, loader: Any = None) -> Any:
    """
    Parse a YAML stream or string into Python objects.

    Args:
        stream: The YAML content to parse (string or file-like object).
        loader: Custom YAML Loader class. Defaults to CLoader if available.

    Returns:
        Any: The parsed Python objects.

    Raises:
        ValueError: If there is a syntax error in the YAML content.

    Example:
        >>> data = yaml_loads("name: 'John Doe'")
        >>> print(data['name'])
        John Doe
    """
    loader = loader or Loader
    try:
        return load(stream, Loader=loader)
    except YAMLError as exc:
        # Wrap in ValueError for compatibility with Pydantic's expected error types
        raise ValueError(f"YAMLError: {exc}") from exc


def yaml_dumps(
    data: Any,
    *,
    stream: Any = None,
    indent: int = None,
    width: int = None,
    line_break: str = None,
    sort_keys: bool = False,
    encoding: str = "utf-8",
    return_bytes: bool = True,
) -> Any:
    """
    Serialize a Python object to a YAML string or stream.

    Args:
        data: The Python object to serialize.
        stream: File-like object to write to. If None, returns a string/bytes.
        indent: Number of spaces for indentation.
        width: Maximum line width for the output.
        line_break: Character(s) to use for line breaks.
        sort_keys: Whether to sort dictionary keys alphabetically.
        encoding: Character encoding for the output.
        return_bytes: If True and stream is None, returns bytes. Otherwise, a string.

    Returns:
        Any: The serialized YAML content.

    Raises:
        ValueError: If the object cannot be serialized to YAML.

    Example:
        >>> yaml_dumps({"active": True}, return_bytes=False)
        'active: true\n'
    """
    try:
        res = dump(
            data,
            stream=stream,
            Dumper=FHIRDumper,
            indent=indent,
            width=width,
            line_break=line_break,
            sort_keys=sort_keys,
            encoding=encoding,
        )
    except YAMLError as exc:
        raise ValueError(f"YAMLError: {exc}") from exc

    if stream is None and not return_bytes:
        res = res.decode(encoding) if isinstance(res, bytes) else res

    return res
