"""Functions for parsing the Sparv configuration files."""

import copy
import logging
from functools import reduce
from typing import Any

import yaml

from sparv.core import paths

log = logging.getLogger(__name__)

DEFAULT_CONFIG = paths.pipeline_path / paths.default_config_file
PRESETS_DIR = paths.pipeline_path / paths.presets_dir

config = {}  # Dict holding full configuration
config_undeclared = set()  # Config variables collected from use but not declared anywhere
presets = {}  # Dict holding annotation presets


def load_config(config_file: str) -> None:
    """Load both default config and corpus config and merge into one config structure.

    Args:
        config_file: Path to corpus config file.
    """
    # Read default config
    if DEFAULT_CONFIG.is_file():
        with open(DEFAULT_CONFIG) as f:
            default_config = yaml.load(f, Loader=yaml.FullLoader)
    else:
        log.warning("Default config file is missing: " + DEFAULT_CONFIG)
        default_config = {}
    default_classes = default_config.get("classes", {})

    # Read corpus config
    user_config = {}
    with open(config_file) as f:
        loaded_config = yaml.load(f, Loader=yaml.FullLoader)
        if loaded_config:
            user_config = loaded_config
    user_classes = user_config.get("classes", {})

    # Merge default and corpus config
    combined_config = _merge_dicts(copy.deepcopy(user_config), default_config)

    # Merge with config, overriding existing values
    global config
    config = _merge_dicts(combined_config, config)

    # Load and resolve annotation presets
    class_dict = load_presets(config.get("language", None))
    annotations = resolve_presets(config.get("annotations", []))

    # Update classes and annotations from presets
    preset_classes = collect_classes(config.get("annotations", []), class_dict)
    config["annotations"] = sorted(annotations)
    combined_classes = _merge_dicts(preset_classes, default_classes)
    classes = _merge_dicts(user_classes, combined_classes)
    config["classes"] = classes


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
        with open(f) as ff:
            presets_yaml = yaml.load(ff, Loader=yaml.FullLoader)

            # Skip preset if it is not valid for lang
            if lang:
                languages = presets_yaml.get("languages", [])
                if languages and lang not in languages:
                    continue

            # Make sure preset names are upper case
            p_name = (f.stem).upper()
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


def collect_classes(user_annotations, class_dict):
    """Collect classes from chosen presets."""
    result = {}
    for annotation in user_annotations:
        result.update(class_dict.get(annotation, {}))
    return result
