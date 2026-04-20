"""Functions for creating and validating JSON schemas."""

from __future__ import annotations

import itertools
import json
import re
import typing
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from typing import Any as AnyType

from sparv.api import Config, SparvErrorMessage
from sparv.core import registry

# Sentinel representing an unconditional property. (positive_conditions, negative_conditions), both empty.
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
        choices: Iterable[str] | Callable[[], Iterable[str]] | None = None,
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

    def __init__(
        self, min_value: int | float | None = None, max_value: int | float | None = None, **kwargs: AnyType
    ) -> None:
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

    def __init__(
        self, min_value: int | float | None = None, max_value: int | float | None = None, **kwargs: AnyType
    ) -> None:
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
        # Conditional properties, keyed by (positive_conditions, negative_conditions).
        # Properties in this dict are only valid when the associated conditions are met, and will be rendered
        # as JSON Schema if/then clauses.
        self.allof: defaultdict[tuple[tuple[Object | None, ...], tuple[Object, ...]], list] = defaultdict(list)

    def __hash__(self) -> int:
        """Return a hash of the schema.

        Returns:
            A hash of the schema.
        """
        return hash(json.dumps(self.schema, sort_keys=True))

    def __eq__(self, other: object) -> bool:
        """Compare two objects based on their schema.

        Args:
            other: The object to compare with.

        Returns:
            True if the schema of the current object is equal to the schema of the other object.
        """
        if other is None:
            return False
        if not isinstance(other, Object):
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
        condition: tuple[tuple[Object | None, ...], tuple[Object, ...]] | None = None,
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
            # Build JSON Schema if/then conditionals from the allof dict.
            # Each key is (positive_conditions, negative_conditions), both being tuples of Object schemas.
            # Positive conditions become direct schemas in allOf; negative ones are wrapped in {"not": ...}.
            # None values in positive_conditions (originating from NO_COND) are filtered out.
            conditionals = []
            for condition in self.allof:
                pos_conds, neg_conds = condition
                if len(pos_conds) + len(neg_conds) > 1:
                    # Multiple conditions: combine into an allOf with negations
                    cond_schema = {
                        "allOf": [c.schema for c in pos_conds if c is not None] + [{"not": c.schema} for c in neg_conds]
                    }
                else:
                    # Single condition
                    pos_cond = pos_conds[0]
                    if pos_cond is None:
                        # Unreachable in practice: a lone None means unconditional, which would have been
                        # stored in self.properties instead of self.allof. Kept as a defensive guard.
                        continue
                    cond_schema = pos_cond.schema

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
        is_condition: bool = False,
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
        # Maps (positive_conditions, negative_conditions) -> list of (key, property) pairs.
        # Unconditional children are stored under the key NO_COND = ((), ()).
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
                    # All children share the same condition (or are unconditional)
                    cond = next(iter(children.keys()))
                    for subkey, prop in children[cond]:
                        child_obj.add_property(subkey, prop, required=is_condition)

                    conditionals[cond].append((key, child_obj))
                else:
                    # Children have different conditions. We must generate a separate version of the parent
                    # object for each valid combination of conditions, because JSON Schema if/then applies
                    # at the object level.
                    no_cond = children.get(NO_COND)  # Unconditional children, if any
                    conds = [c for c in children if c != NO_COND]  # Conditional children

                    # Generate all non-empty subsets of conditions:
                    # e.g., for conditions [X, Y]: [(X,), (Y,), (X, Y)]
                    combinations = list(
                        itertools.chain.from_iterable([itertools.combinations(conds, i + 1) for i in range(len(conds))])
                    )

                    # If unconditional children exist, prepend an empty combination so that unconditional
                    # children also get their own entry (with all conditions negated).
                    if no_cond:
                        combinations.insert(0, ())

                    for combination in combinations:
                        # Prepend NO_COND to every combination so unconditional children are always included.
                        if no_cond:
                            combination = (NO_COND, *combination)  # noqa: PLW2901

                        child_obj = Object(additional_properties=False, description=description)

                        # Add all children belonging to this combination of conditions.
                        for cond in combination:
                            for subkey, prop in children[cond]:
                                child_obj.add_property(subkey, prop, required=is_condition)

                        # Collect positive conditions from this combination. For NO_COND entries, c[0] is ()
                        # (falsy), so `c[0] or (None,)` substitutes None as a placeholder. This marks the
                        # presence of unconditional children without contributing a real condition schema.
                        positive_conds = tuple({cc for c in combination for cc in c[0] or (None,)})

                        # Negative conditions: all condition schemas from `conds` that are NOT part of this
                        # combination's positive set. These will be negated in the JSON Schema ({"not": ...}).
                        negative_conds = tuple(
                            {cc for c in conds for cc in c[0] if cc is not None and cc not in positive_conds}
                        )

                        # Only emit this combination if positive and negative conditions don't contradict.
                        if not set(positive_conds).intersection(set(negative_conds)):
                            conditionals[positive_conds, negative_conds].append((key, child_obj))

            elif "_cfg" in value:  # A leaf node with a Config object
                try:
                    prop, condition = handle_property(value["_cfg"])
                except ValueError:
                    full_key = f"{parent_name}.{key}" if parent_name else key
                    raise ValueError(f"Unsupported datatype for '{full_key}': '{value['_cfg'].datatype}'") from None

                # Store with key (condition, ()). condition is a tuple of Object schemas (empty if
                # unconditional), and the second element (negative conditions) starts empty.
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
        cfg_datatypes = typing.get_args(cfg.datatype) if registry.is_union_type(cfg.datatype) else [cfg.datatype]

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
            elif cfg_datatype is list or typing.get_origin(cfg_datatype) is list:
                args = typing.get_args(cfg_datatype)
                if args:
                    if registry.is_union_type(args[0]):
                        kwargs["items"] = [get_class_from_type(a) for a in typing.get_args(args[0])]
                    else:
                        kwargs["items"] = get_class_from_type(args[0])
                datatype = Array(**kwargs)
            elif cfg_datatype is dict or typing.get_origin(cfg_datatype) is dict:
                args = typing.get_args(cfg_datatype)
                if args:
                    kwargs["additionalProperties"] = get_class_from_type(args[1])().schema
                datatype = Object(**kwargs)
            elif cfg_datatype is None:
                datatype = Any(**kwargs)
            else:
                raise ValueError
            datatypes.append(datatype)

        if cfg.conditions:
            # Convert each condition Config into a JSON Schema Object that matches a config where the
            # condition is satisfied. For example, Config("metadata.language", choices=["swe"]) becomes
            # an Object schema requiring {"metadata": {"language": {"enum": ["swe"]}}}.
            conditions = set()
            for condition_cfg in cfg.conditions:
                # Build a nested dict matching the dotted config name structure
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
            conditions = ()  # Unconditional property

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
    import jsonschema_rs  # noqa: PLC0415

    def build_path_string(path: Sequence) -> str:
        parts = []
        for part in path:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, int):
                parts[-1] += f"[{part}]"
        return ".".join(parts)

    try:
        jsonschema_rs.validate(schema, cfg)
    except jsonschema_rs.ValidationError as e:
        msg = ["There was a problem trying to parse the corpus config file.\n"]

        # Rephrase messages about unexpected keys
        unknown_key = re.search(
            r"(?:Unevaluated|Additional) properties are not allowed \('(.+)' was unexpected", e.message
        )
        if unknown_key:
            full_path = build_path_string([*e.instance_path, unknown_key[1]])
            msg.append(f"Unexpected key in config file: {full_path!r}")
        else:
            msg.append(e.message)
            if e.instance_path:
                msg.append(f"Offending config path: {build_path_string(e.instance_path)}")

        raise SparvErrorMessage("\n".join(msg)) from None
