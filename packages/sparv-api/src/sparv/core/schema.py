"""Functions for creating and validating JSON schemas."""

from __future__ import annotations

import itertools
import json
import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from typing import Any as AnyType

import typing_inspect

from sparv.api import Config, SparvErrorMessage
from sparv.core import registry

NO_COND = ((), ())


class BaseProperty:
    """Base class for other property types."""

    def __init__(self, prop_type: str | None, allow_null: bool | None = False, **kwargs: AnyType) -> None:
        """Initialize the class.

        Args:
            prop_type: The type of the property.
            allow_null: Whether null values are allowed.
            **kwargs: Additional keyword arguments.
        """
        self.schema = {"type": [prop_type, "null"] if allow_null else prop_type, **kwargs} if prop_type else kwargs


class Any(BaseProperty):
    """Class representing any type."""

    def __init__(self, **kwargs: AnyType) -> None:
        """Initialize the class.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init__(None, **kwargs)


class String(BaseProperty):
    """Class representing a string."""

    def __init__(
        self,
        pattern: str | None = None,
        choices: Iterable[str] | Callable | None = None,
        min_len: int | None = None,
        max_len: int | None = None,
        allow_null: bool = False,
        **kwargs: AnyType,
    ) -> None:
        """Initialize the class.

        Args:
            pattern: A regex pattern.
            choices: An iterable of possible choices, or a function that returns such an iterable.
            min_len: The minimum length of the string.
            max_len: The maximum length of the string.
            allow_null: Whether null values are allowed.
            **kwargs: Additional keyword arguments.
        """
        if pattern:
            kwargs["pattern"] = pattern
        if choices:
            if callable(choices):
                choices = choices()
            kwargs["enum"] = list(choices)
        if min_len is not None:
            kwargs["minLength"] = min_len
        if max_len is not None:
            kwargs["maxLength"] = max_len
        super().__init__("string", allow_null, **kwargs)


class Integer(BaseProperty):
    """Class representing an integer."""

    def __init__(self, min_value: int | None = None, max_value: int | None = None, **kwargs: AnyType) -> None:
        """Initialize the class.

        Args:
            min_value: The minimum value.
            max_value: The maximum value.
            **kwargs: Additional keyword arguments.
        """
        if min_value is not None:
            kwargs["minimum"] = min_value
        if max_value is not None:
            kwargs["maximum"] = max_value
        super().__init__("integer", **kwargs)


class Number(BaseProperty):
    """Class representing either a float or an integer."""

    def __init__(self, min_value: int | float | None, max_value: int | float | None, **kwargs: AnyType) -> None:
        """Initialize the class.

        Args:
            min_value: The minimum value.
            max_value: The maximum value.
            **kwargs: Additional keyword arguments.
        """
        if min_value is not None:
            kwargs["minimum"] = min_value
        if max_value is not None:
            kwargs["maximum"] = max_value
        super().__init__("number", **kwargs)


class Boolean(BaseProperty):
    """Class representing a boolean."""

    def __init__(self, **kwargs: AnyType) -> None:
        """Initialize the class.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init__("boolean", **kwargs)


class Null(BaseProperty):
    """Class representing a null value."""

    def __init__(self, **kwargs: AnyType) -> None:
        """Initialize the class.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init__("null", **kwargs)


class Array(BaseProperty):
    """Class representing an array of values."""

    def __init__(
        self,
        items: type[String | Integer | Number | Boolean | Null | Any | Array | Object] | None = None,
        **kwargs: AnyType,
    ) -> None:
        """Initialize the class.

        Args:
            items: The type of items in the array.
            **kwargs: Additional keyword arguments.
        """
        if items:
            if isinstance(items, list):
                kwargs["items"] = {"type": []}
                for item in items:
                    item_schema = item().schema
                    kwargs["items"]["type"].append(item_schema.pop("type"))
                    kwargs["items"].update(item_schema)
            else:
                kwargs["items"] = items().schema
        super().__init__("array", **kwargs)


class Object:
    """Class representing an object."""

    def __init__(
        self, additional_properties: dict | bool = True, description: str | None = None, **kwargs: AnyType
    ) -> None:
        """Initialize the class.

        Args:
            additional_properties: Whether additional properties are allowed.
            description: A description of the object.
            **kwargs: Additional keyword arguments.
        """
        if additional_properties is False or isinstance(additional_properties, dict):
            kwargs["additionalProperties"] = additional_properties
        if description:
            kwargs["description"] = description
        self.obj_schema = {"type": "object", **kwargs}
        self.properties = {}
        self.required = []
        self.allof: defaultdict[tuple[tuple[Object, ...], tuple[Object, ...]], list] = defaultdict(list)

    def __hash__(self) -> int:
        """Return a hash of the schema.

        Returns:
            A hash of the schema.
        """
        return hash(json.dumps(self.schema, sort_keys=True))

    def __eq__(self, other: Object) -> bool:
        """Compare two objects based on their schema.

        Args:
            other: The object to compare with.

        Returns:
            True if the schema of the current object is equal to the schema of the other object.
        """
        if other is None:
            return False
        return json.dumps(self.schema, sort_keys=True) == json.dumps(other.schema, sort_keys=True)

    def __lt__(self, other: Object) -> bool:
        """Compare two objects based on their schema.

        Args:
            other: The object to compare with.

        Returns:
            True if the schema of the current object is less than the schema of the other object.
        """
        if other is None:
            return False
        return json.dumps(self.schema, sort_keys=True) < json.dumps(other.schema, sort_keys=True)

    def add_property(
        self,
        name: str,
        prop_obj: list | String | Integer | Number | Object | Any,
        required: bool = False,
        condition: tuple[tuple[Object, ...], tuple[Object, ...]] | None = None,
    ) -> Object:
        """Add a property to the object.

        Args:
            name: The name of the property.
            prop_obj: The property object.
            required: Whether the property is required.
            condition: A tuple with two tuples of conditions (positive and negative).

        Returns:
            The object itself.
        """
        if condition and condition != NO_COND:
            self.allof[condition].append((name, prop_obj))
        else:
            self.properties[name] = prop_obj
        if required:
            self.required.append(name)
        return self

    @property
    def schema(self) -> dict:
        """Return the JSON schema for the current object and its children as a dictionary."""
        prop_schemas = {}
        for name, prop_obj in self.properties.items():
            if isinstance(prop_obj, list):
                combined_schema = {"type": []}
                for obj in prop_obj:
                    obj_schema = obj.schema
                    for key in obj_schema:
                        if key == "type":
                            combined_schema["type"].append(obj_schema[key])
                        else:
                            combined_schema[key] = obj_schema[key]
                prop_schemas[name] = combined_schema
            else:
                prop_schemas[name] = prop_obj.schema
        self.obj_schema["properties"] = prop_schemas
        if self.required:
            self.obj_schema["required"] = self.required
        if self.allof:
            conditionals = []
            for condition in self.allof:
                pos_conds, neg_conds = condition
                if len(pos_conds) + len(neg_conds) > 1:
                    cond_schema = {
                        "allOf": [c.schema for c in pos_conds if c is not None] + [{"not": c.schema} for c in neg_conds]
                    }
                else:
                    cond_schema = pos_conds[0].schema

                conditionals.append(
                    {
                        "if": cond_schema,
                        "then": {"properties": {name: prop_obj.schema for name, prop_obj in self.allof[condition]}},
                    }
                )
            self.obj_schema["allOf"] = conditionals
        return self.obj_schema


class JsonSchema(Object):
    """Class representing a JSON schema."""

    def __init__(self) -> None:
        """Initialize the JSON schema."""
        super().__init__(
            **{
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://spraakbanken.gu.se/sparv/schema.json",
                "type": "object",
                "properties": {},
                "required": [],
                "unevaluatedProperties": False,
            }
        )

    def to_json(self) -> str:
        """Return the JSON schema as a string."""
        return json.dumps(self.schema, indent=2)


def get_class_from_type(t: type) -> type:
    """Get the JSON schema class from a Python type.

    Args:
        t: A Python type.

    Returns:
        A JSON schema class.
    """
    types = {
        str: String,
        int: Integer,
        float: Number,
        bool: Boolean,
        type(None): Null,
        list: Array,
        dict: Object,
        None: Any,
    }
    return types[t]


def build_json_schema(config_structure: dict) -> dict:
    """Build a JSON schema based on Sparv's config structure.

    Args:
        config_structure: A dictionary with information about the structure of the config file.

    Returns:
        A dictionary with the JSON schema.
    """
    schema = JsonSchema()

    def handle_object(
        structure: dict,
        parent_obj: Object | None = None,
        parent_name: str | None = None,
        is_condition: bool | None = False,
    ) -> defaultdict[tuple[tuple[Object | None, ...], tuple[Object, ...]], list]:
        """Handle a dictionary which will become an object in the JSON schema.

        Args:
            structure: The dictionary to handle.
            parent_obj: The parent object.
            parent_name: The name of the parent object.
            is_condition: Whether this object is a condition.

        Returns:
            A dictionary with conditionals as keys and lists of children for each conditional as values.

        Raises:
            ValueError: If the datatype is not supported.
            SparvErrorMessage: If an unknown error occurs.
        """
        conditionals: defaultdict[tuple[tuple[Object | None, ...], tuple[Object, ...]], list] = defaultdict(list)

        for key, value in structure.items():
            if not value.get("_source"):  # Not a leaf, has children
                description = None
                if parent_name is None and key in registry.modules:
                    # This is a module
                    description = registry.modules[key].description
                child_obj = Object(additional_properties=is_condition, description=description)
                children = handle_object(value, parent_name=key, is_condition=is_condition)

                if len(children) == 1:
                    # Same or no condition for all children
                    cond = next(iter(children.keys()))
                    for subkey, prop in children[cond]:
                        child_obj.add_property(subkey, prop, required=is_condition)

                    conditionals[cond].append((key, child_obj))
                else:
                    no_cond = children.get(NO_COND)
                    conds = [c for c in children if c != NO_COND]
                    combinations = list(
                        itertools.chain.from_iterable([itertools.combinations(conds, i + 1) for i in range(len(conds))])
                    )

                    if no_cond:
                        combinations.insert(0, ())

                    for combination in combinations:
                        if no_cond:
                            combination = (NO_COND, *combination)  # noqa: PLW2901

                        child_obj = Object(additional_properties=False, description=description)

                        for cond in combination:
                            for subkey, prop in children[cond]:
                                child_obj.add_property(subkey, prop, required=is_condition)
                        positive_conds = tuple({cc for c in combination for cc in c[0] or (None,)})
                        negative_conds = tuple(
                            {cc for c in conds if c != NO_COND for cc in c[0] if cc not in positive_conds}
                        )

                        if not set(positive_conds).intersection(set(negative_conds)):
                            conditionals[positive_conds, negative_conds].append((key, child_obj))

            elif "_cfg" in value:  # A leaf
                try:
                    prop, condition = handle_property(value["_cfg"])
                except ValueError:
                    full_key = f"{parent_name}.{key}" if parent_name else key
                    raise ValueError(f"Unsupported datatype for '{full_key}': '{value['_cfg'].datatype}'") from None

                conditionals[condition, ()].append((key, prop))

            else:
                full_key = f"{parent_name}.{key}" if parent_name else key
                raise SparvErrorMessage(f"Unknown error while handling config variable {full_key!r}.")

        if parent_obj:
            # Either this is the root, or we're constructing a condition object
            for condition in conditionals:
                for key, prop in conditionals[condition]:
                    parent_obj.add_property(key, prop, condition=condition, required=is_condition)

        return conditionals

    def handle_property(cfg: Config) -> tuple[BaseProperty | list[BaseProperty], tuple[Object, ...]]:
        """Handle a property and its conditions.

        Args:
            cfg: A Config object.

        Returns:
            A tuple with two values. The first is either a datatype object or a list of datatype objects, and the
                second is a tuple of conditions (possibly empty).

        Raises:
            ValueError: If the datatype is not supported.
        """
        kwargs = {}
        if cfg.description:
            kwargs["description"] = cfg.description
        if cfg.default is not None:
            kwargs["default"] = cfg.default
        if cfg.const is not None:
            kwargs["const"] = cfg.const

        # Datatype is either a single type or a union of types
        if typing_inspect.is_union_type(cfg.datatype):
            cfg_datatypes = typing_inspect.get_args(cfg.datatype)
        else:
            cfg_datatypes = [cfg.datatype]

        datatypes = []

        for cfg_datatype in cfg_datatypes:
            if cfg_datatype is str:
                datatype = String(
                    pattern=cfg.pattern, choices=cfg.choices, min_len=cfg.min_len, max_len=cfg.max_len, **kwargs
                )
            elif cfg_datatype is int:
                datatype = Integer(min_value=cfg.min_value, max_value=cfg.max_value, **kwargs)
            elif cfg_datatype is float:
                datatype = Number(min_value=cfg.min_value, max_value=cfg.max_value, **kwargs)
            elif cfg_datatype is bool:
                datatype = Boolean(**kwargs)
            elif cfg_datatype is type(None):
                datatype = Null(**kwargs)
            elif cfg_datatype is list or typing_inspect.get_origin(cfg_datatype) is list:
                args = typing_inspect.get_args(cfg_datatype)
                if args:
                    if typing_inspect.is_union_type(args[0]):
                        kwargs["items"] = [get_class_from_type(a) for a in typing_inspect.get_args(args[0])]
                    else:
                        kwargs["items"] = get_class_from_type(args[0])
                datatype = Array(**kwargs)
            elif cfg_datatype is dict or typing_inspect.get_origin(cfg_datatype) is dict:
                args = typing_inspect.get_args(cfg_datatype)
                if args:
                    kwargs["additionalProperties"] = get_class_from_type(args[1])().schema
                datatype = Object(**kwargs)
            elif cfg_datatype is None:
                datatype = Any(**kwargs)
            else:
                raise ValueError
            datatypes.append(datatype)

        if cfg.conditions:
            conditions = set()
            for condition_cfg in cfg.conditions:
                cond_structure = {}
                prev = cond_structure
                for part in condition_cfg.name.split(".")[:-1]:
                    prev.setdefault(part, {})
                    prev = prev[part]
                prev[condition_cfg.name.split(".")[-1]] = {"_cfg": condition_cfg, "_source": "condition"}

                condition = Object()
                handle_object(cond_structure, condition, is_condition=True)
                conditions.add(condition)
            conditions = tuple(sorted(conditions))
        else:
            conditions = ()

        return datatypes if len(datatypes) > 1 else datatypes[0], conditions

    handle_object(config_structure, schema)

    return schema.schema


def validate(cfg: dict, schema: dict) -> None:
    """Validate a Sparv config using a JSON schema.

    Args:
        cfg: The config to validate.
        schema: The JSON schema to validate against.

    Raises:
        SparvErrorMessage: If the config is invalid.
    """
    import jsonschema  # noqa: PLC0415

    def build_path_string(path: Sequence) -> str:
        parts = []
        for part in path:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, int):
                parts[-1] += f"[{part}]"
        return ".".join(parts)

    try:
        jsonschema.validate(cfg, schema)
    except jsonschema.ValidationError as e:
        msg = ["There was a problem trying to parse the corpus config file.\n"]

        # Rephrase messages about unexpected keys
        unknown_key = re.search(r"properties are not allowed \('(.+)' was unexpected", e.message)
        if unknown_key:
            full_path = ".".join([*list(e.absolute_path), unknown_key[1]])
            msg.append(f"Unexpected key in config file: {full_path!r}")
        else:
            msg.append(e.message)
            if e.absolute_path:
                msg.append(f"Offending config path: {build_path_string(e.absolute_path)}")
                if "description" in e.schema:
                    msg.append(f"Description of config key: {e.schema['description']}")

        raise SparvErrorMessage("\n".join(msg)) from None
