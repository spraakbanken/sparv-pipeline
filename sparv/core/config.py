"""Functions for parsing the Sparv configuration files."""

import copy
import logging
from collections import defaultdict
from functools import reduce
from pathlib import Path
from typing import Any, Optional

import yaml
import yaml.scanner

from sparv import util
from sparv.core import paths, registry

log = logging.getLogger(__name__)

DEFAULT_CONFIG = paths.default_config_file
PRESETS_DIR = paths.presets_dir
PARENT = "parent"
MAX_THREADS = "threads"

config = {}  # Full configuration
presets = {}  # Annotation presets
_config_user = {}  # Local corpus config
_config_default = {}  # Default config

# Dict with info about config structure, prepopulated with some module-independent keys
config_structure = {
    "classes": {"_source": "core"},
    "custom_annotations": {"_source": "core"},
    "install": {"_source": "core"},
    PARENT: {"_source": "core"},
    MAX_THREADS: {"_source": "core"},
    "preload":  {"_source": "core"}
}

config_usage = defaultdict(set)  # For each config key, a list of annotators using that key


class Unset:
    """Class used to represent a config value that isn't set."""
    pass


def read_yaml(yaml_file):
    """Read YAML file and handle errors."""
    try:
        with open(yaml_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.parser.ParserError as e:
        raise util.SparvErrorMessage("Could not parse the configuration file:\n" + str(e))
    except yaml.scanner.ScannerError as e:
        raise util.SparvErrorMessage("An error occurred while reading the configuration file:\n" + str(e))
    except FileNotFoundError:
        raise util.SparvErrorMessage(f"Could not find the config file '{yaml_file}'")

    return data or {}


def load_config(config_file: Optional[str], config_dict: Optional[dict] = None) -> None:
    """Load both default config and corpus config and merge into one config structure.

    Args:
        config_file: Path to corpus config file. If None, only the default config is read.
        config_dict: Get corpus config from dictionary instead of config file.
    """
    assert not (config_file and config_dict), "config_file and config_dict can not be used together"
    # Read default config
    global _config_default
    if DEFAULT_CONFIG.is_file():
        _config_default = read_yaml(DEFAULT_CONFIG)
    else:
        log.warning("Default config file is missing: {}".format(DEFAULT_CONFIG))
        _config_default = {}

    if config_file:
        # Read corpus config
        global _config_user
        _config_user = read_yaml(config_file) or {}

        def handle_parents(cfg, current_dir="."):
            """Combine parent configs recursively."""
            combined_parents = {}
            if cfg.get(PARENT):
                parents = cfg[PARENT]
                if isinstance(parents, str):
                    parents = [parents]
                for parent in parents:
                    parent_path = Path(current_dir, parent)
                    config_parent = read_yaml(parent_path)
                    config_parent = handle_parents(config_parent, parent_path.parent)
                    combined_parents = _merge_dicts(config_parent, combined_parents)
                cfg = _merge_dicts(cfg, combined_parents)
            return cfg

        # If parent configs are specified, inherit their contents
        _config_user = handle_parents(_config_user)
    elif config_dict:
        _config_user = config_dict
    else:
        _config_user = {}

    # Merge default and corpus config and save to global config variable
    global config
    config = _merge_dicts(copy.deepcopy(_config_user), _config_default)

    # Make sure that the root level only contains dictionaries or lists to save us a lot of headache
    for key in config:
        if key == PARENT:
            continue
        if not isinstance(config[key], (dict, list)):
            raise util.SparvErrorMessage(f"The config section '{key}' could not be parsed.", module="sparv",
                                         function="config")


def dump_config(data, resolve_alias=False, sort_keys=False):
    """Dump config YAML to string.

    Args:
        data: The data to be dumped.
        resolve_alias: Will replace aliases with their anchor's content if set to True.
        sort_keys: Whether to sort the keys alphabetically.
    """
    class IndentDumper(yaml.Dumper):
        """Customized YAML dumper that indents lists."""

        def increase_indent(self, flow=False, indentless=False):
            """Force indentation."""
            return super(IndentDumper, self).increase_indent(flow)

    # Add custom string representer for prettier multiline strings
    def str_presenter(dumper, data):
        if len(data.splitlines()) > 1:  # check for multiline string
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    yaml.add_representer(str, str_presenter)

    if resolve_alias:
        # Resolve aliases and replace them with their anchors' contents
        yaml.Dumper.ignore_aliases = lambda *args: True

    return yaml.dump(data, sort_keys=sort_keys, allow_unicode=True, Dumper=IndentDumper, indent=4,
                     default_flow_style=False)


def _get(name: str, config_dict=None):
    """Try to get value from config, raising an exception if key doesn't exist."""
    config_dict = config_dict if config_dict is not None else config
    # Handle dot notation
    return reduce(lambda c, k: c[k], name.split("."), config_dict)


def set_value(name: str, value: Any, overwrite=True, config_dict=None):
    """Set value in config, possibly using dot notation."""
    keys = name.split(".")
    prev = config_dict if config_dict is not None else config
    for key in keys[:-1]:
        prev.setdefault(key, {})
        prev = prev[key]
    if overwrite:
        prev[keys[-1]] = value
    else:
        prev.setdefault(keys[-1], value)


def get(name: str, default=None):
    """Get value from config, or return the supplied 'default' if key doesn't exist."""
    try:
        return _get(name)
    except KeyError:
        return default


def set_default(name: str, default=None):
    """Set default value for config variable."""
    # If config variable is already set to None but we get a better default value, replace the existing
    if default is not None:
        try:
            if _get(name) is None:
                set_value(name, default)
        except KeyError:
            set_value(name, default, overwrite=False)
    else:
        set_value(name, default, overwrite=False)


def extend_config(new_config):
    """Extend existing config with new values for missing keys."""
    _merge_dicts(config, new_config)


def update_config(new_config):
    """Update existing config with new values, replacing existing values."""
    global config
    config = _merge_dicts(copy.deepcopy(new_config), config)


def _merge_dicts(user, default):
    """Merge corpus config with default config, letting user values override default values."""
    if isinstance(user, dict) and isinstance(default, dict):
        for k, v in default.items():
            if k not in user:
                user[k] = v
            else:
                user[k] = _merge_dicts(user[k], v)
    return user


def add_to_structure(name, default=None, description=None, annotator: Optional[str] = None):
    """Add config variable to config structure."""
    set_value(name,
              {"_default": default,
               "_description": description,
               "_source": "module"},
              config_dict=config_structure
              )

    if annotator:
        add_config_usage(name, annotator)


def get_config_description(name):
    """Get description for config key."""
    return _get(name, config_structure).get("_description")


def add_config_usage(config_key, annotator):
    """Add an annotator to the list of annotators that are using a given config key."""
    config_usage[config_key].add(annotator)


def validate_module_config():
    """Make sure that modules don't try to access undeclared config keys."""
    for config_key in config_usage:
        try:
            _get(config_key, config_structure)
        except KeyError:
            annotators = config_usage[config_key]
            raise util.SparvErrorMessage(
                "The annotator{} {} {} trying to access the config key '{}' which isn't declared anywhere.".format(
                    "s" if len(annotators) > 1 else "", ", ".join(annotators),
                    "are" if len(annotators) > 1 else "is", config_key), "sparv", "config")


def validate_config(config_dict=None, structure=None, parent=""):
    """Make sure the corpus config doesn't contain invalid keys."""
    config_dict = config_dict or config
    structure = structure or config_structure
    for key in config_dict:
        path = (parent + "." + key) if parent else key
        if key not in structure:
            if not parent:
                raise util.SparvErrorMessage(f"Unknown key in config file: '{path}'. No module with that name found.",
                                             module="sparv", function="config")
            else:
                module_name = parent.split(".", 1)[0]
                raise util.SparvErrorMessage(f"Unknown key in config file: '{path}'. The module '{module_name}' "
                                             f"doesn't have an option with that name.",
                                             module="sparv", function="config")
        elif not structure[key].get("_source"):
            validate_config(config_dict[key], structure[key], path)


def load_presets(lang):
    """Read presets files, set global presets variable and return dictionary with preset classes."""
    global presets
    class_dict = {}

    for f in PRESETS_DIR.rglob("*.yaml"):
        presets_yaml = read_yaml(f)

        # Skip preset if it is not valid for lang
        if lang:
            languages = presets_yaml.get("languages", [])
            if languages and lang not in languages:
                continue

        # Make sure preset names are upper case
        p_name = f.stem.upper()
        c = presets_yaml.get("classes", {})
        p = presets_yaml.get("presets", {})
        for key, value in p.items():
            if isinstance(value, list):
                # Prefix all preset keys with preset name
                for i, v in enumerate(value):
                    if v in p:
                        value[i] = f"{p_name}.{v}"
            # Extend presets and class_dict
            k_name = f"{p_name}.{key}"
            presets[k_name] = value
            if c:
                class_dict[k_name] = c
    return class_dict


def resolve_presets(annotations):
    """Resolve annotation presets into actual annotations."""
    result = []
    for annotation in annotations:
        if annotation in presets:
            result.extend(resolve_presets(presets[annotation]))
        else:
            result.append(annotation)
    return result


def apply_presets():
    """Resolve annotations from presets and set preset classes."""
    # Load annotation presets and classes
    class_dict = load_presets(get("metadata.language"))

    preset_classes = {}  # Classes set by presets

    # Go through annotation lists in config to find references to presets
    for a in registry.annotation_sources:
        annotations = get(a)
        if not annotations:
            continue
        # Update classes set by presets
        for annotation in annotations:
            preset_classes.update(class_dict.get(annotation, {}))

        # Resolve presets and update annotation list in config
        set_value(a, resolve_presets(annotations))

    # Update classes
    default_classes = _config_default.get("classes", {})
    user_classes = _config_user.get("classes", {}).copy()
    combined_classes = _merge_dicts(preset_classes, default_classes)
    classes = _merge_dicts(user_classes, combined_classes)
    config["classes"] = classes


def handle_document_annotation():
    """Copy document annotation to text class."""
    doc_elem = get("import.document_annotation")

    # Make sure that if both classes.text and import.document_annotation are set, that they have the same value
    if get("classes.text") and doc_elem and get("classes.text") != doc_elem:
        raise util.SparvErrorMessage(
            "The config keys 'classes.text' and 'import.document_annotation' can't have different values.",
            "sparv", "config")

    # If import.document_annotation is set, copy value to classes.text
    if doc_elem:
        set_default("classes.text", doc_elem)


def inherit_config(source: str, target: str) -> None:
    """Let 'target' inherit config values from 'source' for evey key that is supported and not already populated.

    Only keys which are either missing or with a value of None in the target will inherit the source's value, meaning
    that falsy values like empty strings or lists will not be overwritten.

    Args:
        source: Module name of source.
        target: Module name of target.
    """
    for key in config.get(source, []):
        if key in config_structure.get(target, []):
            value = None
            try:
                value = _get(f"{target}.{key}")
            except KeyError:
                pass
            if value is None:
                set_value(f"{target}.{key}", config[source][key])
