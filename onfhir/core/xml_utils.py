import datetime
import decimal
import importlib
import logging
import uuid
from collections import OrderedDict, deque
from copy import copy
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast, no_type_check

from lxml import etree
from lxml.etree import QName
from pydantic.fields import FieldInfo
from pydantic_core._pydantic_core import Url

from .utils import (
    determine_version_prefix,
    get_base64_encoder,
    get_fhir_type_name,
    is_list_type,
    is_primitive_type,
)

if TYPE_CHECKING:
    from .abstract import FHIRAbstract


ROOT_NAMESPACE = "http://hl7.org/fhir"
XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
EMPTY_VALUE = None
LOGGER = logging.getLogger(__name__)


def capitalize_first_letter(text: str) -> str:
    """
    Capitalize the first letter of a string.

    Args:
        text: The string to capitalize.

    Returns:
        str: The string with its first letter capitalized.
    """
    if not text:
        return text
    return text[0].upper() + text[1:]


def xml_represent(field: FieldInfo, value: Any, version_prefix: str = "") -> Any:
    """
    Convert a Python value into its FHIR-compliant XML string representation.

    Args:
        field: The Pydantic FieldInfo containing FHIR type metadata.
        value: The Python value to represent.
        version_prefix: Optional FHIR version prefix (e.g., 'R4.').

    Returns:
        Any: The string representation of the value for XML output.

    Raises:
        NotImplementedError: If the FHIR type is unknown or not yet supported.
    """
    if value is None:
        return value

    type_name = get_fhir_type_name(field, prefix=version_prefix)

    if type_name == "boolean":
        return "true" if value is True else "false"

    if type_name in (
        "string",
        "code",
        "id",
        "markdown",
        "xhtml",
        "oid",
        "canonical",
        "uri",
    ):
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    if type_name in (
        "decimal",
        "integer",
        "integer64",
        "unsignedInt",
        "positiveInt",
    ):
        if isinstance(value, decimal.Decimal):
            return str(float(value))
        return str(value)

    if type_name == "base64Binary":
        encoder = get_base64_encoder(field)
        if encoder is not None:
            value = encoder.encode(value)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    if type_name == "date":
        if isinstance(value, str):
            return value
        if isinstance(value, datetime.datetime):
            return value.date().isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        return value

    if type_name == "dateTime":
        if isinstance(value, str):
            return value
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return value

    if type_name == "time":
        if isinstance(value, datetime.time):
            return value.isoformat()
        return value

    if type_name == "instant":
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return value

    if type_name == "url":
        if isinstance(value, Url):
            return str(value)
        return value

    if type_name == "uuid":
        if isinstance(value, uuid.UUID):
            return f"urn:uuid:{str(value)}"
        if not value.startswith("urn:uuid:"):
            return f"urn:uuid:{value}"
        return value

    raise NotImplementedError(
        f"XML representation for FHIR type '{type_name}' is not implemented."
    )


@cache
def get_fhir_root_module(class_module_path: str) -> ModuleType:
    """
    Resolve the root FHIR module for a given class module path.

    Args:
        class_module_path: The __module__ path of a FHIR class.

    Returns:
        ModuleType: The imported root module.
    """
    parent_module_path = ".".join(class_module_path.split(".")[:-1])
    return importlib.import_module(parent_module_path)


class SimpleNodeStorage:
    """
    A generic sequential storage for node-related components like attributes,
    namespaces, or child nodes.
    """

    __slots__ = ("_storage", "node")

    def __init__(self, node: "Node"):
        """
        Initialize the storage.

        Args:
            node: The parent Node instance associated with this storage.
        """
        assert isinstance(node, Node)
        object.__setattr__(self, "node", node)
        object.__setattr__(self, "_storage", deque())

    def __iter__(self):
        return iter(self._storage)

    def __getitem__(self, index: int):
        return self._storage[index]

    def __len__(self) -> int:
        return len(self._storage)

    def append(self, item: Any) -> None:
        """Add an item to the storage."""
        self._storage.append(item)

    def extend(self, items: list[Any]) -> None:
        """Add multiple items to the storage."""
        self._storage.extend(items)

    def as_list(self) -> list[Any]:
        """Return the storage contents as a standard Python list."""
        return list(self._storage)


class NodeContainer(SimpleNodeStorage):
    """
    A specialized container for child Node instances or etree Elements.
    """

    def append(self, item: "Node | etree._Element"):
        """Add a child node."""
        assert isinstance(item, (Node, etree._Element))
        super().append(item)

    def extend(self, items: list["Node | etree._Element"]):
        """Add multiple child nodes."""
        if not all(isinstance(item, (Node, etree._Element)) for item in items):
            raise ValueError("All items must be instances of Node or etree._Element.")
        super().extend(items)


class AttributeContainer(SimpleNodeStorage):
    """
    A specialized container for XML Attribute instances.
    Enforces allowed attribute constraints if defined on the parent Node.
    """

    def append(self, item: "Attribute"):
        """Add an attribute."""
        assert isinstance(item, Attribute)
        if self.node._allowed_attrs and item.name not in self.node._allowed_attrs:
            raise ValueError(
                f"'{item.name}' is not an allowed attribute for this node."
            )
        super().append(item)

    def extend(self, items: list["Attribute"]):
        """Add multiple attributes."""
        if not all(isinstance(item, Attribute) for item in items):
            raise ValueError("All items must be instances of Attribute.")

        for item in items:
            if self.node._allowed_attrs and item.name not in self.node._allowed_attrs:
                raise ValueError(
                    f"'{item.name}' is not an allowed attribute for this node."
                )

        super().extend(items)


class NamespaceContainer(SimpleNodeStorage):
    """
    A specialized container for XML Namespace definitions.
    """

    def append(self, item: "Namespace"):
        """Add a namespace."""
        assert isinstance(item, Namespace)
        super().append(item)

    def extend(self, items: list["Namespace"]):
        """Add multiple namespaces."""
        if not all(isinstance(item, Namespace) for item in items):
            raise ValueError("All items must be instances of Namespace.")
        super().extend(items)


class CommentContainer(SimpleNodeStorage):
    """
    A specialized container for XML Comment instances.
    """

    def append(self, item: "Comment"):
        """Add a comment."""
        assert isinstance(item, Comment)
        super().append(item)

    def extend(self, items: list["Comment"]):
        """Add multiple comments."""
        if not all(isinstance(item, Comment) for item in items):
            raise ValueError("All items must be instances of Comment.")
        super().extend(items)


class AttributeValue:
    """
    Represents an XML attribute value, optionally quoted.
    """

    def __init__(self, raw_value: bytes | str, quote: bool = False):
        """
        Initialize the attribute value.

        Args:
            raw_value: The unquoted value.
            quote: Whether the value should be wrapped in single quotes.
        """
        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode()
        self.raw: str = raw_value
        self.quote = quote

    def to_xml(self) -> str:
        """Return the XML string representation."""
        value = self.raw
        if self.quote:
            value = f"'{value}'"
        return value

    def __str__(self):
        return self.to_xml()

    @no_type_check
    def __eq__(self, other: "AttributeValue"):
        return (self.raw == other.raw) and (self.quote == other.quote)


class Attribute:
    """
    Represents an XML attribute with a name and a value.
    """

    def __init__(
        self,
        name: QName | str,
        value: AttributeValue | bytes | str | None,
    ):
        """
        Initialize the attribute.

        Args:
            name: The attribute name (can be a string or a QName).
            value: The attribute value.
        """
        self.name: QName | str = name
        if isinstance(value, (AttributeValue, str)):
            self.value = value
        else:
            if isinstance(value, bytes):
                value = value.decode()
            self.value = value

    def __str__(self):
        name, value = self.to_xml()
        return f'{name}="{value}"'

    def to_xml(self) -> tuple[str, str | None]:
        """
        Convert to a format suitable for XML generation.

        Returns:
            tuple: A pair of (name, string_value).
        """
        string_value: str | None = None

        if isinstance(self.value, AttributeValue):
            string_value = self.value.to_xml()
        elif self.value is not None:
            string_value = cast(str, self.value)

        return str(self.name), string_value

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.__str__()}>"

    @no_type_check
    def __eq__(self, other: "Attribute"):
        return (self.name == other.name) and (self.value == other.value)


class Namespace:
    """
    Represents an XML namespace definition (xmlns).
    """

    def __init__(self, name: str | None, location: bytes | str):
        """
        Initialize the namespace.

        Args:
            name: The namespace prefix (None for default namespace).
            location: The namespace URI.
        """
        self.name: str | None = name
        if isinstance(location, bytes):
            location = location.decode()
        self.location = location

    def __str__(self):
        prefix_part = f":{self.name}" if self.name else ""
        return f'xmlns{prefix_part}="{self.location}"'

    def to_xml(self) -> tuple[str | None, str]:
        """Return the name and location as a tuple."""
        return self.name, self.location

    def __repr__(self):
        return f"<{self.__class__.__name__} {self}>"

    @no_type_check
    def __eq__(self, other: "Namespace"):
        return (self.name == other.name) and (self.location == other.location)


class Comment:
    """
    Represents an XML comment.
    """

    __slots__ = ("_text",)

    def __init__(self, text: bytes | str):
        """
        Initialize the comment.

        Args:
            text: The comment text.
        """
        if isinstance(text, str):
            text = text.encode()
        self._text: bytes = text

    def to_xml(self) -> etree._Comment:
        """Convert to an lxml Comment element."""
        return etree.Comment(b" " + self._text + b" ")

    def to_string(self) -> str:
        """Return the comment text as a string."""
        return self._text.decode()

    @classmethod
    def from_element(cls, element: etree._Comment) -> "Comment":
        """Create a Comment instance from an lxml Comment element."""
        return cls(element.text)

    def __str__(self):
        return self.to_string()


class Node:
    """
    Represents an XML node in the FHIR document structure.
    """

    _allowed_attrs: set[str] = set()
    version_prefix: str = ""

    def __init__(
        self,
        name: QName | str,
        *,
        value: bytes | str | None = None,
        text: bytes | str | "Node" | None = None,
        attributes: list[Attribute] | None = None,
        namespaces: list[Namespace] | None = None,
        comments: list[Comment] | None = None,
        parent: "Node" | None = None,
        children: list["Node"] | None = None,
        version_prefix: str = "",
    ):
        """
        Initialize the Node.

        Args:
            name: The XML tag name.
            value: The 'value' attribute of the node (common in FHIR).
            text: The text content of the node.
            attributes: List of XML attributes.
            namespaces: List of namespace definitions.
            comments: List of XML comments.
            parent: Reference to the parent Node.
            children: List of child Nodes.
            version_prefix: Optional FHIR version prefix.
        """
        self.name = name
        self._value = None
        self._text: str | None = None
        self.attributes = AttributeContainer(self)
        self.namespaces = NamespaceContainer(self)
        self.comments = CommentContainer(self)
        self.parent = None
        self.children = NodeContainer(self)

        if text:
            self.set_text(text)
        if value:
            self.value = value

        if attributes:
            self.attributes.extend(attributes)
        if namespaces:
            self.namespaces.extend(namespaces)
        if comments:
            self.comments.extend(comments)
        if parent:
            assert isinstance(parent, Node)
            self.parent = parent
        if children:
            self.children.extend(children)
        self.version_prefix = version_prefix

    def rename(self, new_name: str) -> None:
        """
        Rename the current Node.

        Args:
            new_name: The new tag name.

        Raises:
            ValueError: If the new name is identical to the current name.
        """
        if self.name == new_name:
            raise ValueError("Current Node name and provided name are identical!")
        self.name = new_name

    def add_namespace(
        self,
        namespace: Namespace | str | None,
        location: bytes | str | None = None,
    ) -> None:
        """
        Add a namespace to the node.

        Args:
            namespace: A Namespace instance or a prefix string.
            location: The namespace URI (required if prefix is provided).

        Raises:
            ValueError: If location is missing when providing a prefix.
        """
        if isinstance(namespace, Namespace):
            self.namespaces.append(namespace)
            return
        if location is None:
            raise ValueError("'location' value is required.")

        self.namespaces.append(Namespace(namespace, location))

    def add_attribute(
        self,
        attribute: Attribute | str,
        value: bytes | str | None = None,
    ) -> None:
        """
        Add an attribute to the node.

        Args:
            attribute: An Attribute instance or a name string.
            value: The attribute value (if name string is provided).
        """
        if isinstance(attribute, Attribute):
            self.attributes.append(attribute)
            return
        self.attributes.append(Attribute(attribute, value))

    @property
    def text(self):
        """ """
        return self._text

    @text.setter
    def text(self, value: Any):
        """Set the text content of the node."""
        self._text = value

    @property
    def value(self):
        """Return the 'value' attribute of the node."""
        return self._value

    @value.setter
    def value(self, value: Any):
        """Set the 'value' attribute of the node."""
        self._value = value

    def set_text(self, value):
        """ """
        if isinstance(value, Node):
            value = value.to_string(pretty_print=False, xml_declaration=False)
        self._text = value

    def add_text(self, value, prefix="", suffix=""):
        """ """
        if isinstance(value, Node):
            value = value.to_string(pretty_print=False, xml_declaration=False)
        if not isinstance(value, str):
            if isinstance(value, bytes):
                value = value.decode()
            else:
                value = str(value)

        value = prefix + value + suffix
        if not self._text:
            self._text = ""
        self._text += value

    @classmethod
    def create(
        cls,
        name: str,
        *,
        value: bytes | str | None = None,
        text: str | bytes | "Node" | None = None,
        attributes: (
            dict[str, bytes | str] | list[Attribute | tuple[str, bytes | str]] | None
        ) = None,
        namespaces: (
            dict[str | None, bytes | str]
            | list[Namespace | tuple[str | None, bytes | str]]
            | None
        ) = None,
        version_prefix: str = "",
    ) -> "Node":
        """
        Create a new Node with the specified components.

        Args:
            name: The tag name for the new node.
            value: The 'value' attribute.
            text: The text content.
            attributes: A dictionary or list of attributes.
            namespaces: A dictionary or list of namespace definitions.
            version_prefix: Optional FHIR version prefix.

        Returns:
            Node: The newly created Node instance.
        """
        node_instance = cls(
            name=name, value=value, text=text, version_prefix=version_prefix
        )

        if attributes:
            if isinstance(attributes, dict):
                attributes = list(attributes.items())
            if isinstance(attributes, list):
                for attribute in attributes:
                    if isinstance(attribute, tuple):
                        node_instance.add_attribute(*attribute)
                    else:
                        node_instance.add_attribute(attribute)

        if namespaces:
            if isinstance(namespaces, dict):
                namespaces = list(namespaces.items())

            if isinstance(namespaces, list):
                for namespace in namespaces:
                    if isinstance(namespace, tuple):
                        node_instance.add_namespace(*namespace)
                    else:
                        node_instance.add_namespace(namespace)

        return node_instance

    @staticmethod
    def clean_tag(element: etree._Element) -> str:
        """
        Remove namespace prefix from an XML tag.

        Args:
            element: The lxml element to clean.

        Returns:
            str: The local name of the tag.
        """
        return QName(element.tag).localname

    @classmethod
    def from_element(
        cls,
        element: etree._Element,
        parent: "Node" | None = None,
        existing_namespaces: list[Namespace] | None = None,
        comments: list[Comment] | None = None,
        fhir_class: type["FHIRAbstract"] | None = None,
    ) -> "Node":
        """
        Parse an lxml Element into a Node tree.

        Args:
            element: The lxml element to parse.
            parent: The parent Node instance.
            existing_namespaces: List of namespaces already defined upstream.
            comments: List of comments associated with this element.
            fhir_class: The FHIR model class expected for this node.

        Returns:
            Node: The populated Node instance.
        """
        if parent is not None:
            version_prefix = parent.version_prefix
        elif fhir_class is not None:
            version_prefix = determine_version_prefix(fhir_class.__module__)
        else:
            raise ValueError("Either 'parent' or 'fhir_class' must be provided.")

        name = Node.clean_tag(element)
        node_instance = cls(name, version_prefix=version_prefix)
        if element.text:
            node_instance.text = element.text

        # Attributes
        for attribute_name, attribute_value in element.attrib.items():
            if attribute_name == "value":
                node_instance.value = attribute_value
            else:
                node_instance.add_attribute(attribute_name, attribute_value)

        if existing_namespaces is None:
            existing_namespaces = []

        if parent is not None:
            existing_namespaces += parent.namespaces.as_list()

        # Handle namespaces
        for prefix, location in element.nsmap.items():
            namespace = Namespace(prefix, location)
            if namespace in existing_namespaces:
                continue
            node_instance.namespaces.append(namespace)
            existing_namespaces.append(namespace)

        # Handle comments
        if comments:
            node_instance.comments.extend(comments)

        # Potential comments for children
        child_comments: list[Comment] | None = None
        for child in element:
            if isinstance(child, etree._Comment):
                if child_comments is None:
                    child_comments = []
                child_comments.append(Comment.from_element(child))
                continue

            if child.nsmap.get(None) == XHTML_NAMESPACE:
                node_instance.children.append(child)
                continue

            child_tag = Node.clean_tag(child)
            # Try to resolve a specific Node subclass if it exists
            child_node_class = globals().get(child_tag, Node)
            child_node_class.from_element(
                child,
                parent=node_instance,
                existing_namespaces=copy(existing_namespaces),
                comments=child_comments,
            )
            # Reset comments for the next child
            child_comments = None

        if parent is not None:
            parent.children.append(node_instance)

        return node_instance

    @staticmethod
    def inject_comments(node: "Node", comments: str | list[str]) -> None:
        """
        Inject XML comments as children of a Node.

        Args:
            node: The Node to inject comments into.
            comments: A single string or a list of comment strings.
        """
        if comments is None:
            return
        if comments:
            if isinstance(comments, str):
                comments = [comments]
            for comment in comments:
                node.comments.append(Comment(comment))

    @staticmethod
    def add_fhir_element(
        parent: "Node",
        field: FieldInfo,
        field_name: str,
        value: Any,
        extension: Any = None,
        extension_field: FieldInfo = None,
        summary_only: bool = False,
    ) -> None:
        """
        Recursively add FHIR elements to a Node tree.
        Handles primitives, complex types, and extensions.

        Args:
            parent: The parent Node.
            field: The Pydantic FieldInfo for this element.
            value: The value to add.
            extension: Optional extension associated with a primitive value.
            extension_field: The FieldInfo for the extension.
            summary_only: Whether to include only summary elements.
        """
        # Skip fields not included in summary if summary mode is active
        if summary_only and not field.json_schema_extra.get(  # type: ignore
            "summary_element_property", False
        ):
            return

        if isinstance(value, dict):
            value = value.items()

        tag_name = field.alias if field.alias else field_name
        child = Node.create(tag_name, version_prefix=parent.version_prefix)

        # -------------------
        # Primitive Types
        # -------------------
        if is_primitive_type(field):
            # Handle list of primitives
            if isinstance(value, list):
                if extension and not isinstance(extension, list):
                    extension = [extension]

                if extension is None:
                    extension = []

                if len(value) < len(extension):
                    LOGGER.warning(
                        f"Some {(len(extension) - len(value))} extension(s) are ignored"
                    )

                for index, element_value in enumerate(value):
                    try:
                        ext_item = extension[index]
                    except IndexError:
                        ext_item = None
                    if ext_item is None and element_value is None:
                        continue
                    Node.add_fhir_element(
                        parent,
                        field,
                        field_name,
                        value=element_value,
                        extension=ext_item,
                        extension_field=extension_field,
                    )
            # Handle single primitive value
            elif value is not None:
                child.value = xml_represent(field, value, child.version_prefix)
                if extension is not None and not summary_only:
                    Node.inject_comments(
                        parent, extension.__dict__.get("fhir_comments", None)
                    )
                    Node.add_fhir_element(
                        child,
                        field=extension_field,
                        field_name=extension_field.alias or "extension",
                        value=extension,
                        extension=None,
                        extension_field=None,
                        summary_only=summary_only,
                    )
                parent.children.append(child)
            # Handle empty/null value (can still have extensions)
            else:
                child.value = EMPTY_VALUE
                if extension is not None and not summary_only:
                    extensions = (
                        not isinstance(extension, list) and [extension] or extension
                    )
                    for ext_item in extensions:
                        if ext_item is None:
                            continue
                        Node.inject_comments(
                            parent, ext_item.__dict__.get("fhir_comments", None)
                        )
                        Node.add_fhir_element(
                            child,
                            field=extension_field,
                            field_name=extension_field.alias or "extension",
                            value=ext_item,
                            extension=None,
                            extension_field=None,
                            summary_only=summary_only,
                        )
                parent.children.append(child)
            return

        # -------------------
        # Complex Types
        # -------------------

        # Handle list of complex types
        if isinstance(value, list):
            for element_value in value:
                Node.add_fhir_element(
                    parent,
                    field,
                    field_name,
                    element_value,
                    extension=extension,
                    extension_field=extension_field,
                    summary_only=summary_only,
                )
            return

        # Handle Polymorphic/Resource types
        parent_resource_container = None
        fhir_type_name = get_fhir_type_name(field, prefix=parent.version_prefix)
        if fhir_type_name == "Resource":
            # FHIR resources are wrapped in a container in XML
            parent_resource_container = child
            child = Node.create(
                value.get_resource_type(), version_prefix=parent.version_prefix
            )
            parent_resource_container.children.append(child)

        # Handle Primitive Extensions
        # (special case for extensions on primitive elements)
        if fhir_type_name == "FHIRPrimitiveExtension":
            extension_inner_field = value.__class__.model_fields["extension"]
            extension_inner_value = value.__dict__.get(
                extension_inner_field.alias, None
            )
            if not extension_inner_value:
                return
            Node.add_fhir_element(
                parent,
                extension_inner_field,
                field_name,
                extension_inner_value,
                extension=extension,
                extension_field=extension_field,
                summary_only=summary_only,
            )
            return

        if not summary_only:
            comments = value.__dict__.get("fhir_comments", None)
            Node.inject_comments(parent, comments)

        # Iterate through model fields in their specified sequence
        alias_mapping = value.__class__.get_alias_mapping()
        summary_sequence = value.__class__.summary_elements_sequence()
        for prop_name in value.__class__.elements_sequence():
            if summary_only and prop_name not in summary_sequence:
                continue

            field_instance = value.__class__.model_fields[alias_mapping[prop_name]]
            field_key = alias_mapping[field_instance.alias]
            actual_value = value.__dict__.get(field_key)

            # Extensions and IDs are often serialized as attributes
            if (
                fhir_type_name == "Extension"
                and field_instance.alias in ("url", "id")
                and actual_value
            ):
                child.add_attribute(field_instance.alias, actual_value)
                continue

            # Handle XHTML (Narrative)
            if (
                get_fhir_type_name(field_instance, prefix=parent.version_prefix)
                == "xhtml"
                and actual_value
            ):
                xhtml_element = etree.fromstring(actual_value)
                # Ensure the namespace is correct
                if xhtml_element.nsmap.get(None) == XHTML_NAMESPACE and str(
                    etree.QName(XHTML_NAMESPACE, field_instance.alias)
                ):
                    child.children.append(xhtml_element)
                    continue
                else:
                    raise ValueError("Invalid XHTML namespace or tag.")

            # Look for companion extensions for primitives
            primitive_extension_value, primitive_extension_field = None, None
            if is_primitive_type(field_instance):
                extension_key = f"{field_key}__ext"
                primitive_extension_value = value.__dict__.get(extension_key, None)
                if primitive_extension_value:
                    primitive_extension_field = value.__class__.model_fields[
                        extension_key
                    ]

            if primitive_extension_value is None and actual_value is None:
                continue

            Node.add_fhir_element(
                child,
                field_instance,
                field_name,
                actual_value,
                extension=primitive_extension_value,
                extension_field=primitive_extension_field,
                summary_only=summary_only,
            )

        if parent_resource_container is None:
            parent.children.append(child)
        else:
            parent.children.append(parent_resource_container)

    @classmethod
    def from_fhir_obj(
        cls,
        model: "FHIRAbstract",
        summary_only: bool = False,
    ) -> "Node":
        """
        Create a Node tree from a FHIR model instance.

        Args:
            model: The FHIR model instance to convert.

        Returns:
            Node: The root Node of the resulting XML tree.
        """
        version_prefix = determine_version_prefix(model.__module__)
        resource_node = cls(
            model.get_resource_type(),
            namespaces=[Namespace(None, ROOT_NAMESPACE)],
            version_prefix=version_prefix,
        )

        if hasattr(model, "fhir_comments") and model.fhir_comments:
            Node.inject_comments(resource_node, model.fhir_comments)

        alias_mapping = model.__class__.get_alias_mapping()
        summary_sequence = model.__class__.summary_elements_sequence()

        for prop_name in model.__class__.elements_sequence():
            if summary_only and prop_name not in summary_sequence:
                continue

            field_key = alias_mapping[prop_name]
            field = model.__class__.model_fields[field_key]
            value = model.__dict__.get(field_key, None)

            primitive_extension_value, primitive_extension_field = None, None
            if is_primitive_type(field):
                extension_key = f"{field_key}__ext"
                primitive_extension_value = model.__dict__.get(extension_key, None)
                if primitive_extension_value:
                    primitive_extension_field = model.__class__.model_fields[
                        extension_key
                    ]

            if primitive_extension_value is None and value is None:
                continue

            Node.add_fhir_element(
                resource_node,
                field,
                prop_name,
                value,
                extension=primitive_extension_value,
                extension_field=primitive_extension_field,
                summary_only=summary_only,
            )

        return resource_node

    def to_xml(self, parent_element: etree._Element = None) -> etree._Element:
        """
        Convert the Node tree into an lxml Element tree.

        Args:
            parent_element: Optional parent lxml element.

        Returns:
            etree._Element: The root lxml element.
        """
        params = {}
        nsmap = self.normalize_namespaces()
        if nsmap:
            params["nsmap"] = nsmap

        attrib = self.normalize_attributes()
        if attrib:
            params["attrib"] = attrib

        if self.value:
            params["value"] = (
                self.value.to_xml()
                if isinstance(self.value, AttributeValue)
                else self.value
            )

        if parent_element is None:
            # Root element
            element = etree.Element(str(self.name), **params)
            # Handle comments before the child element
            if self.comments:
                for comment in self.comments:
                    element.append(comment.to_xml())
        else:
            # Handle comments before the child element
            if self.comments:
                parent_element.extend([comment.to_xml() for comment in self.comments])
            element = parent_element.makeelement(str(self.name), **params)

        if self.text:
            element.text = (
                self.text.to_xml()
                if isinstance(self.text, AttributeValue)
                else self.text
            )

        if not self.children:
            return element

        for child in self.children:
            if isinstance(child, Node):
                child_element = child.to_xml(element)
            elif isinstance(child, etree._Element):
                child_element = child
            elif isinstance(child, (str, bytes)):
                child_element = etree.fromstring(child)
            else:
                raise NotImplementedError(f"Cannot convert {type(child)} to XML.")

            element.append(child_element)

        return element

    def normalize_attributes(self) -> OrderedDict:
        """Return attributes as an OrderedDict."""
        attributes_dict = OrderedDict()
        for attribute in self.attributes:
            key, value = attribute.to_xml()
            attributes_dict[key] = value
        return attributes_dict

    def normalize_namespaces(self) -> OrderedDict:
        """Return namespaces as an OrderedDict."""
        namespaces_dict = OrderedDict()
        for namespace in self.namespaces:
            key, value = namespace.to_xml()
            namespaces_dict[key] = value
        return namespaces_dict

    @classmethod
    def validate(
        cls,
        element: "Node" | etree._Element | bytes,
        xsd_file: Path | None = None,
        xml_parser: etree.XMLParser | None = None,
    ) -> None:
        """
        Validate XML content against an XSD schema.

        Args:
            element: The XML content (Node, Element, or bytes).
            xsd_file: Path to the XSD schema file.
            xml_parser: Optional custom XML parser with schema already loaded.

        Raises:
            ValueError: If validation fails or required parameters are missing.
        """
        if isinstance(element, cls):
            element_str = element.to_string(pretty_print=False).encode("utf-8")
        elif isinstance(element, etree._Element):
            element_str = etree.tostring(element)
        else:
            element_str = element

        if xml_parser is None and xsd_file is None:
            raise ValueError("Either 'xsd_file' or 'xml_parser' is required.")

        if xml_parser is None:
            assert xsd_file and xsd_file.exists() and xsd_file.is_file()
            schema = etree.XMLSchema(file=str(xsd_file))
            xml_parser = etree.XMLParser(schema=schema)

        try:
            etree.fromstring(element_str, parser=xml_parser)
        except (etree.XMLSchemaError, etree.XMLSyntaxError) as exception:
            raise ValueError(str(exception)) from exception

    def to_string(
        self,
        pretty_print: bool = False,
        xml_declaration: bool = True,
        with_comments: bool = True,
        strip_text: bool = False,
    ) -> str:
        """
        Convert the Node tree into an XML string.

        lxml does not allow ``xml_declaration=True`` combined with
        ``encoding="unicode"`` (it raises a ``ValueError``). We therefore
        serialize without the declaration and prepend it manually when the
        caller requests it.

        Args:
            pretty_print: Whether to format the XML with indentation.
            xml_declaration: Whether to prepend the ``<?xml ...?>`` header.
            with_comments: Whether to include XML comments.
            strip_text: Whether to strip whitespace from text content.

        Returns:
            str: The serialized XML as a Unicode string.
        """
        element = self.to_xml()
        if not with_comments:
            for comment in element.iter(etree.Comment):
                comment.getparent().remove(comment)
        body = etree.tostring(
            element,
            encoding="unicode",
            method="xml",
            pretty_print=pretty_print,
            strip_text=strip_text,
        )
        if xml_declaration:
            body = "<?xml version='1.0' encoding='UTF-8'?>\n" + body
        return body

    @staticmethod
    def get_fhir_value(
        obj: "Node" | etree._Element,
        field: FieldInfo,
        root_module: ModuleType,
    ) -> Any:
        """
        Extract the FHIR value from a Node or Element based on the field type.

        Args:
            obj: The Node or Element to extract from.
            field: The Pydantic FieldInfo.
            root_module: The FHIR version root module.

        Returns:
            Any: The extracted value.
        """
        prefix = determine_version_prefix(root_module.__name__)
        if is_primitive_type(field):
            type_name = get_fhir_type_name(field, prefix=prefix)
            if type_name == "xhtml":
                if isinstance(obj, etree._Element):
                    return etree.tostring(obj)
                return obj.to_string(pretty_print=False, xml_declaration=False)

            value = obj.value

            if type_name == "uuid" and value:
                if value.startswith("urn:uuid:"):
                    value = value[len("urn:uuid:") :]
            return value

        # Complex type or Resource
        model_class = root_module.get_fhir_model_class(
            get_fhir_type_name(field, prefix=prefix)
        )
        return obj.to_fhir(model_class, root_module)

    def to_fhir(
        self, model_class: type["FHIRAbstract"], root_module: ModuleType = None
    ) -> "FHIRAbstract":
        """
        Convert the Node tree into a FHIR model instance.

        Args:
            model_class: The target FHIR model class.
            root_module: The FHIR version root module.

        Returns:
            FHIRAbstract: The populated model instance.
        """
        root_module = root_module or get_fhir_root_module(model_class.__module__)
        version_prefix = determine_version_prefix(root_module.__name__)

        # Polymorphic Resource handling
        if model_class.get_resource_type() == "Resource" and self.children:
            child = self.children[0]
            actual_model_class = root_module.get_fhir_model_class(child.name)
            return child.to_fhir(actual_model_class, root_module)

        params: dict[str, Any] = {"resource_type": model_class.get_resource_type()}
        alias_mapping = model_class.get_alias_mapping()
        primitive_extension_values: dict[str, Any] = {}

        # Handle comments
        if self.comments:
            comment_strings = [comment.to_string() for comment in self.comments]
            params["fhir_comments"] = (
                comment_strings[0] if len(comment_strings) == 1 else comment_strings
            )

        # Handle Extension specific attributes
        if model_class.get_resource_type() == "Extension":
            for attribute in self.attributes:
                name, value = attribute.to_xml()
                params[name] = value

        # Iterate through child nodes to populate model parameters
        for child in self.children:
            child_tag = (
                Node.clean_tag(child)
                if isinstance(child, etree._Element)
                else child.name
            )

            field_name = alias_mapping.get(child_tag)
            if not field_name:
                continue

            field_info = model_class.model_fields[field_name]
            is_list = is_list_type(field_info)
            value = Node.get_fhir_value(child, field_info, root_module)

            if is_list:
                if field_name not in params:
                    params[field_name] = []
                params[field_name].append(value)
            else:
                params[field_name] = value

            # Handle primitive extensions stored in XML
            # as children of the primitive element
            if (
                is_primitive_type(field_info)
                and isinstance(child, Node)
                and (child.children or child.comments)
            ):
                extension_field_name = f"{field_name}__ext"
                prim_ext_class = root_module.get_fhir_model_class(
                    "FHIRPrimitiveExtension"
                )
                inner_ext_class = root_module.get_fhir_model_class(
                    get_fhir_type_name(
                        prim_ext_class.model_fields["extension"], prefix=version_prefix
                    )
                )

                prim_ext_params = {}
                if child.comments:
                    child_comment_strings = [c.to_string() for c in child.comments]
                    prim_ext_params["fhir_comments"] = (
                        child_comment_strings[0]
                        if len(child_comment_strings) == 1
                        else child_comment_strings
                    )

                if child.children:
                    prim_ext_params["extension"] = [
                        item.to_fhir(inner_ext_class, root_module)
                        for item in child.children
                    ]

                primitive_extension_instance = prim_ext_class(**prim_ext_params)
                if is_list:
                    if extension_field_name not in primitive_extension_values:
                        primitive_extension_values[extension_field_name] = {}
                    primitive_extension_values[extension_field_name][
                        len(params[field_name]) - 1
                    ] = primitive_extension_instance
                else:
                    params[extension_field_name] = primitive_extension_instance

        # Post-process list-type primitive extensions
        # to ensure correct alignment with values
        for extension_name, index_map in primitive_extension_values.items():
            base_field_name = extension_name[:-5]
            extensions_list = []
            for i in range(len(params[base_field_name])):
                extensions_list.append(index_map.get(i))
            params[extension_name] = extensions_list

        return model_class(**params)

    def __str__(self):
        return self.to_string(pretty_print=False, xml_declaration=False)


def xml_dumps(
    model: "FHIRAbstract",
    *,
    pretty_print: bool = False,
    xml_declaration: bool = True,
    with_comments: bool = True,
    exclude_comments: bool = False,
    strip_text: bool = False,
    summary_only: bool = False,
) -> str:
    """
    Serialize a FHIR model instance to XML.

    Args:
        model: The FHIR model instance.
        pretty_print: Whether to format the XML.
        xml_declaration: Whether to include the XML header.
        with_comments: Whether to include XML comments.
        exclude_comments: If True, suppress all XML comments (overrides with_comments).
        strip_text: Whether to strip whitespace.
        summary_only: Whether to include only summary elements.

    Returns:
        str: The XML string.
    """
    node = Node.from_fhir_obj(model, summary_only=summary_only)
    return node.to_string(
        pretty_print=pretty_print,
        xml_declaration=xml_declaration,
        with_comments=with_comments and not exclude_comments,
        strip_text=strip_text,
    )


def xml_loads(
    model_class: type["FHIRAbstract"],
    xml_bytes: str | bytes | bytearray,
    xml_parser: etree.XMLParser = None,
) -> "FHIRAbstract":
    """
    Parse XML into a FHIR model instance.

    Args:
        model_class: The target FHIR model class.
        xml_bytes: The XML content to parse.
        xml_parser: Optional custom lxml parser.

    Returns:
        FHIRAbstract: The populated model instance.
    """
    root = etree.fromstring(xml_bytes, parser=xml_parser)
    node = Node.from_element(root, fhir_class=model_class)
    return node.to_fhir(model_class)
