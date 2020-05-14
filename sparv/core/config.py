"""Functions for parsing the Sparv configuration files."""

import copy
import logging
import os
from functools import reduce
from typing import Any

import yaml

from sparv.core import paths

log = logging.getLogger(__name__)

DEFAULT_CONFIG = os.path.join(paths.sparv_path, "..", paths.default_config_file)

# Dict holding full configuration
config = {}
config_undeclared = set()  # Config variables collected from use but not declared anywhere


def load_config(config_file: str) -> None:
    """Load both default config and corpus config and merge into one config structure.

    Args:
        config_file: Path to corpus config file.
    """
    # Read default config
    if os.path.isfile(DEFAULT_CONFIG):
        with open(DEFAULT_CONFIG) as f:
            default_config = yaml.load(f, Loader=yaml.FullLoader)
    else:
        log.warning("Default config file is missing: " + DEFAULT_CONFIG)
        default_config = {}

    # Read corpus config
    user_config = {}

    with open(config_file) as f:
        loaded_config = yaml.load(f, Loader=yaml.FullLoader)
        if loaded_config:
            user_config = loaded_config

    # Merge default and corpus config
    combined_config = _merge_dicts(copy.deepcopy(user_config), default_config)

    # Merge with config, overriding existing values
    global config
    config = _merge_dicts(combined_config, config)

    # Resolve annotation presets
    annotations = []
    resolve_presets(config.get("annotations", []), config.get("presets", []), annotations)
    config["annotations"] = annotations


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


def resolve_presets(annotations, presets, resolved_values):
    """Resolve annotation presets into actual annotations."""
    for annotation in annotations:
        if annotation in presets:
            resolve_presets(presets[annotation], presets, resolved_values)
        else:
            resolved_values.append(annotation)
