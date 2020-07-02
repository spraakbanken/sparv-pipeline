"""Functions for parsing the Sparv configuration files."""

import copy
import logging
import os
from functools import reduce
from typing import Any

import yaml

from sparv import util
from sparv.core import log_handler, paths

log = logging.getLogger(__name__)

DEFAULT_CONFIG = paths.pipeline_path / paths.default_config_file
PRESETS_DIR = paths.pipeline_path / paths.presets_dir

config = {}  # Dict holding full configuration
config_undeclared = set()  # Config variables collected from use but not declared anywhere
presets = {}  # Dict holding annotation presets


def read_yaml(yaml_file):
    """Read YAML file and handle errors."""
    try:
        with open(yaml_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.scanner.ScannerError as e:
        raise util.SparvErrorMessage("An error occurred while reading the configuration file:\n" + str(e))

    return data


def load_config(config_file: str) -> None:
    """Load both default config and corpus config and merge into one config structure.

    Args:
        config_file: Path to corpus config file.
    """
    # Read default config
    if DEFAULT_CONFIG.is_file():
        default_config = read_yaml(DEFAULT_CONFIG)
    else:
        log.warning("Default config file is missing: " + DEFAULT_CONFIG)
        default_config = {}
    default_classes = default_config.get("classes", {})

    # Read corpus config
    user_config = {}
    loaded_config = read_yaml(config_file)
    if loaded_config:
        user_config = loaded_config
    user_classes = user_config.get("classes", {})

    # Merge default and corpus config
    combined_config = _merge_dicts(copy.deepcopy(user_config), default_config)

    # Merge with config, overriding existing values
    global config
    config = _merge_dicts(combined_config, config)

    # Set correct classes and annotations from presets
    apply_presets(user_classes, default_classes)

    fix_document_element()


def _get(name: str):
    """Try to get value from config, raising an exception if key doesn't exist."""
    # Handle dot notation
    return reduce(lambda c, k: c[k], name.split("."), config)


def _set(name: str, value: Any, overwrite=False):
    """Set value in config, possibly using dot notation."""
    keys = name.split(".")
    prev = config
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
        config_undeclared.add(name)
        return default


def set_default(name: str, default=None):
    """Set default value for config variable."""
    # If config variable is already set to None but we get a better default value, replace the existing
    if default is not None:
        try:
            if _get(name) is None:
                _set(name, default, overwrite=True)
        except KeyError:
            _set(name, default)
    else:
        _set(name, default)


def extend_config(new_config):
    """Extend existing config with new values for missing keys."""
    _merge_dicts(config, new_config)


def _merge_dicts(user, default):
    """Merge user config with default config, letting user values override default values."""
    if isinstance(user, dict) and isinstance(default, dict):
        for k, v in default.items():
            if k not in user:
                user[k] = v
            else:
                user[k] = _merge_dicts(user[k], v)
    return user


def load_presets(lang):
    """Read presets files and return all presets in one dictionary."""
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


def apply_presets(user_classes, default_classes):
    """Set correct classes and annotations from presets."""
    # Load annotation presets and classes
    class_dict = load_presets(get("metadata.language"))
    annotation_elems = _find_annotations("", config)
    preset_classes = {}

    for a in annotation_elems:
        # Update annotations
        preset_classes.update(_collect_classes(get(a), class_dict))
        annotations = resolve_presets(get(a))
        _set(a, annotations, overwrite=True)

    # Update classes
    combined_classes = _merge_dicts(preset_classes, default_classes)
    classes = _merge_dicts(user_classes, combined_classes)
    config["classes"] = classes


def _collect_classes(user_annotations, class_dict):
    """Collect classes from chosen presets."""
    result = {}
    for annotation in user_annotations:
        result.update(class_dict.get(annotation, {}))
    return result


def _find_annotations(name, config_obj):
    """Return a list of config objects containing an 'annotations' element."""
    result = []
    if isinstance(config_obj, dict):
        if "annotations" in config_obj:
            result.append(f"{name}.annotations")
        else:
            for k, v in config_obj.items():
                new_name = f"{name}.{k}" if name else k
                result.extend(_find_annotations(new_name, v))
    return result


def fix_document_element():
    """Do special treatment for document element."""
    # Check that classes.text is not set
    if get("classes.text") is not None:
        error = "The config value 'classes.text' cannot be set manually. Use 'xml_parser.document_element' instead!"
        log_handler.exit_with_message(error, os.getpid(), None, "sparv", "config")

    # Check that xml_parser.document_element is set
    doc_elem = get("xml_parser.document_element")
    if doc_elem is None:
        error = "The config value 'xml_parser.document_element' must be set!"
        log_handler.exit_with_message(error, os.getpid(), None, "sparv", "config")

    # Set classes.text and
    set_default("classes.text", doc_elem)

    # Add doc_elem to xml_parser.elements
    xml_parser_elems = get("xml_parser.elements")
    if xml_parser_elems is None:
        set_default("xml_parser.elements", [doc_elem])
    elif doc_elem not in xml_parser_elems:
        xml_parser_elems.append(doc_elem)
