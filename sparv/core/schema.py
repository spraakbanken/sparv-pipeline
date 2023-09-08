"""
Functions for creating and validating JSON schemas.
"""

import itertools
import json
import re
from collections import defaultdict
from typing import DefaultDict, List, Optional, Tuple, Type, Union

import typing_inspect
from sparv.api import Config, SparvErrorMessage
from sparv.core import registry

NO_COND = ((), ())

class BaseProperty:
    def __init__(self, prop_type: Optional[str], allow_null: Optional[bool] = False, **kwargs):
        self.schema = {
            "type": prop_type if not allow_null else [prop_type, "null"],
            **kwargs
        } if prop_type else kwargs

class Any(BaseProperty):
    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)

class String(BaseProperty):
    def __init__(self, pattern=None, choices=None, min=None, max=None, allow_null=False, **kwargs):
        if pattern:
            kwargs["pattern"] = pattern
        if choices:
            if callable(choices):
                choices = choices()
            kwargs["enum"] = list(choices)
        if min:
            kwargs["min"] = min
        if max:
            kwargs["max"] = max
        super().__init__("string", allow_null, **kwargs)

class Integer(BaseProperty):
    def __init__(self, **kwargs):
        super().__init__("integer", **kwargs)

class Number(BaseProperty):
    def __init__(self, **kwargs):
        super().__init__("number", **kwargs)

class Boolean(BaseProperty):
    def __init__(self, **kwargs):
        super().__init__("boolean", **kwargs)

class Null(BaseProperty):
    def __init__(self, **kwargs):
        super().__init__("null", **kwargs)

class Array(BaseProperty):
    def __init__(
        self,
        items: Optional[Type[Union[String, Integer, Number, Boolean, Null, Any, "Array", "Object"]]] = None,
        **kwargs
    ):
        if items:
            kwargs["items"] = items().schema
        super().__init__("array", **kwargs)

class Object:
    def __init__(self, additional_properties: bool = True, description: Optional[str] = None, **kwargs):
        if not additional_properties:
            kwargs["additionalProperties"] = False
        if description:
            kwargs["description"] = description
        self.obj_schema = {"type": "object", **kwargs}
        self.properties = {}
        self.required = []
        self.allof: DefaultDict[Tuple[Tuple[Object, ...], Tuple[Object, ...]], list] = defaultdict(list)

    def __hash__(self):
        return hash(json.dumps(self.schema, sort_keys=True))

    def __eq__(self, other):
        if other is None:
            return False
        return json.dumps(self.schema, sort_keys=True) == json.dumps(other.schema, sort_keys=True)

    def __lt__(self, other):
        if other is None:
            return False
        return json.dumps(self.schema, sort_keys=True) < json.dumps(other.schema, sort_keys=True)

    def add_property(
        self,
        name: str,
        prop_obj: Union[List, Union[String, Integer, Number, "Object", Any]],
        required: bool = False,
        condition: Optional[Tuple[Tuple["Object", ...], Tuple["Object", ...]]] = None
    ):
        if condition and not condition == NO_COND:
            self.allof[condition].append((name, prop_obj))
        else:
            self.properties[name] = prop_obj
        if required:
            self.required.append(name)
        return self

    @property
    def schema(self):
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
                        "allOf": [c.schema for c in pos_conds if not c is None] + [  # noqa
                            {"not": c.schema}
                            for c in neg_conds
                        ]
                    }
                else:
                    cond_schema = pos_conds[0].schema

                conditionals.append(
                    {
                        "if": cond_schema,
                        "then": {
                            "properties": {name: prop_obj.schema for name, prop_obj in self.allof[condition]}
                        }
                    }
                )
            self.obj_schema["allOf"] = conditionals
        return self.obj_schema

class JsonSchema(Object):

    def __init__(self):
        super().__init__(**{
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://spraakbanken.gu.se/sparv/schema.json",
            "type": "object",
            "properties": {},
            "required": [],
            "unevaluatedProperties": False
        })

    def to_json(self):
        return json.dumps(self.schema, indent=2)


def get_class_from_type(t):
    """Get JSON schema class from Python type."""
    types = {
        str: String,
        int: Integer,
        float: Number,
        bool: Boolean,
        type(None): Null,
        list: Array,
        dict: Object,
        None: Any
    }
    return types[t]


def build_json_schema(config_structure: dict) -> dict:
    """Build a JSON schema based on Sparv's config structure."""
    schema = JsonSchema()

    def handle_object(
        structure: dict,
        parent_obj: Optional[Object] = None,
        parent_name: Optional[str] = None,
        is_condition: Optional[bool] = False
    ) -> DefaultDict[Tuple[Tuple[Optional[Object], ...], Tuple[Object, ...]], list]:
        """Handle dictionary which will become an object in the JSON schema.

        Return a dictionary with conditionals as keys and lists of children to each conditional as values.
        """
        conditionals: DefaultDict[Tuple[Tuple[Optional[Object], ...], Tuple[Object, ...]], list] = defaultdict(list)

        for key in structure:
            if not structure[key].get("_source"):  # Not a leaf, has children
                description = None
                if parent_name is None and key in registry.modules:
                    # This is a module
                    description = registry.modules[key].description
                child_obj = Object(additional_properties=is_condition, description=description)
                children = handle_object(structure[key], parent_name=key, is_condition=is_condition)

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
                        itertools.chain.from_iterable(
                            [itertools.combinations(conds, i + 1) for i in range(len(conds))]
                        )
                    )

                    if no_cond:
                        combinations.insert(0, ())

                    for combination in combinations:
                        if no_cond:
                            combination = (NO_COND,) + combination

                        child_obj = Object(additional_properties=False, description=description)

                        for cond in combination:
                            for subkey, prop in children[cond]:
                                child_obj.add_property(subkey, prop, required=is_condition)
                        positive_conds = tuple(set(cc for c in combination for cc in c[0] or (None,)))
                        negative_conds = tuple(
                            set(cc for c in conds if c != NO_COND for cc in c[0] if cc not in positive_conds)
                        )

                        if not set(positive_conds).intersection(set(negative_conds)):
                            conditionals[(positive_conds, negative_conds)].append((key, child_obj))

            elif "_cfg" in structure[key]:  # A leaf
                try:
                    prop, condition = handle_property(structure[key]["_cfg"])
                except ValueError:
                    full_key = f"{parent_name}.{key}" if parent_name else key
                    raise ValueError(f"Unsupported datatype for '{full_key}': '{structure[key]['_cfg'].datatype}'")

                conditionals[(condition, ())].append((key, prop))

            else:
                full_key = f"{parent_name}.{key}" if parent_name else key
                raise SparvErrorMessage(f"Unknown error while handling config variable {full_key!r}.")

        if parent_obj:
            # Either this is the root, or we're constructing a condition object
            for condition in conditionals:
                for key, prop in conditionals[condition]:
                    parent_obj.add_property(key, prop, condition=condition, required=is_condition)

        return conditionals

    def handle_property(
        cfg: Config
    ) -> Tuple[Union[BaseProperty, List[BaseProperty]], Tuple[Object, ...]]:
        """
        Handle a property and its conditions.

        Args:
            cfg: A Config object

        Returns:
            A tuple with two values. The first is either a datatype object or a list of datatype objects, and the
            second is a tuple of conditions (possible empty).
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
                    pattern=cfg.pattern,
                    choices=cfg.choices,
                    min=cfg.min,
                    max=cfg.max,
                    **kwargs
                )
            elif cfg_datatype is int:
                datatype = Integer(**kwargs)
            elif cfg_datatype is float:
                datatype = Number(**kwargs)
            elif cfg_datatype is bool:
                datatype = Boolean(**kwargs)
            elif cfg_datatype is type(None):
                datatype = Null(**kwargs)
            elif cfg_datatype is list or typing_inspect.get_origin(cfg_datatype) is list:
                args = typing_inspect.get_args(cfg_datatype)
                if args:
                    kwargs["items"] = get_class_from_type(args[0])
                datatype = Array(**kwargs)
            elif cfg_datatype is dict:
                datatype = Object(**kwargs)
            elif cfg_datatype is None:
                datatype = Any(**kwargs)
            else:
                raise ValueError()
            datatypes.append(datatype)

        if cfg.conditions:
            conditions = set()
            for condition_cfg in cfg.conditions:
                cond_structure = {}
                prev = cond_structure
                for part in condition_cfg.name.split(".")[:-1]:
                    prev.setdefault(part, {})
                    prev = prev[part]
                prev[condition_cfg.name.split(".")[-1]] = {
                    "_cfg": condition_cfg,
                    "_source": "condition"
                }

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
    """Validate a Sparv config using JSON schema."""
    import jsonschema

    try:
        jsonschema.validate(cfg, schema)
    except jsonschema.ValidationError as e:
        msg = ["There was a problem trying to parse the corpus config file.\n"]

        if e.validator == "unevaluatedProperties":
            # This only happens for unexpected keys at the root level
            prop = re.search(r"'(.+)' was unexpected", e.message)
            if prop:
                msg.append(f"Unexpected property at root level: {prop.group(1)!r}")
            else:
                msg.append(e.message)
        else:
            if e.absolute_path:
                msg.append(f"Offending config path: {'.'.join(e.absolute_path)}")
            msg.append(e.message)

        raise SparvErrorMessage("\n".join(msg))
