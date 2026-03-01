"""Functions for parsing Sparv configuration files."""
# ruff: noqa: PLW0603

from __future__ import annotations

import copy
from collections import defaultdict
from functools import reduce
from pathlib import Path
from typing import Any

import yaml
import yaml.composer
import yaml.parser
import yaml.scanner

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from sparv.api.classes import Config
from sparv.core import registry
from sparv.core.misc import SparvErrorMessage, get_logger
from sparv.core.paths import paths

logger = get_logger(__name__)

DEFAULT_CONFIG = paths.default_config_file
PRESETS_DIR = paths.presets_dir
PARENT = "parent"
MAX_THREADS = "threads"

config = {}  # Full configuration
presets = {}  # Annotation presets, needs to be global (accessed by Snakefile)
_config_user = {}  # Local corpus config
_config_default = {}  # Default config

# Dict with info about config structure, prepopulated with some module-independent keys
config_structure = {
    "classes": {
        "_source": "core",
        "_cfg": Config("classes", description="Mapping of annotation classes to annotations", datatype=dict),
    },  # Default classes are set in apply_presets()
    "custom_annotations": {"_source": "core", "_cfg": Config("custom_annotations", datatype=list)},
    "install": {
        "_source": "core",
        "_cfg": Config("install", description="List of default installers to run", datatype=list),
    },
    PARENT: {
        "_source": "core",
        "_cfg": Config(PARENT, description="Path to one or more parent config files", datatype=str | list[str]),
    },
    MAX_THREADS: {"_source": "core", "_cfg": Config(MAX_THREADS, datatype=dict[str, int])},
    "preload": {
        "_source": "core",
        "_cfg": Config("preload", description="List of processors to preload", datatype=list),
    },
    "uninstall": {
        "_source": "core",
        "_cfg": Config("uninstall", description="List of default uninstallers to run", datatype=list),
    },
}

config_usage = defaultdict(set)  # For each config key, a list of annotators using that key


class Unset:
    """Class used to represent a config value that is not set."""


def read_yaml(yaml_file: str | Path) -> dict:
    """Read a YAML file and handle errors.

    Args:
        yaml_file: Path to the YAML file.

    Returns:
        Dictionary with parsed YAML data.

    Raises:
        SparvErrorMessage: If the config cannot be parsed or read.
    """
    # Handle dates as strings
    yaml.constructor.SafeConstructor.yaml_constructors["tag:yaml.org,2002:timestamp"] = (
        yaml.constructor.SafeConstructor.yaml_constructors["tag:yaml.org,2002:str"]
    )
    try:
        with Path(yaml_file).open(encoding="utf-8") as f:
            data = yaml.load(f, Loader=SafeLoader)
    except (yaml.parser.ParserError, yaml.composer.ComposerError) as e:
        raise SparvErrorMessage("Could not parse the configuration file:\n" + str(e)) from e
    except yaml.scanner.ScannerError as e:
        raise SparvErrorMessage("An error occurred while reading the configuration file:\n" + str(e)) from e
    except FileNotFoundError as e:
        raise SparvErrorMessage(f"Could not find the config file '{yaml_file}'") from e

    return data or {}


def load_config(config_file: str | Path | None, config_dict: dict | None = None) -> None:
    """Load both the default config and corpus config, and merge them into one config structure.

    Args:
        config_file: Path to the corpus config file. If None, only the default config is read.
        config_dict: Get corpus config from a dictionary instead of a config file.

    Raises:
        SparvErrorMessage: If the config cannot be parsed.
    """
    assert not (config_file and config_dict), "config_file and config_dict cannot be used together"
    # Read default config
    global _config_default
    if DEFAULT_CONFIG.is_file():
        _config_default = read_yaml(DEFAULT_CONFIG)
    else:
        logger.warning("Default config file is missing: %s", DEFAULT_CONFIG)
        _config_default = {}

    if config_file:
        # Read corpus config
        global _config_user
        _config_user = read_yaml(config_file) or {}

        def handle_parents(cfg: dict, current_dir: Path = Path()) -> dict:
            """Combine parent configs recursively.

            Args:
                cfg: Config dictionary.
                current_dir: Current directory.

            Returns:
                Combined config.
            """
            combined_parents = {}
            if parents := cfg.get(PARENT):
                if isinstance(parents, str):
                    parents = [parents]
                for parent in parents:
                    parent_path = current_dir / parent
                    config_parent = read_yaml(parent_path)
                    config_parent = handle_parents(config_parent, parent_path.parent)
                    _merge_dicts(config_parent, combined_parents)
                    combined_parents = config_parent
                _merge_dicts(cfg, combined_parents)
            return cfg

        # If parent configs are specified, inherit their contents
        _config_user = handle_parents(_config_user)
    elif config_dict:
        _config_user = config_dict
    else:
        _config_user = {}

    # Merge default and corpus config and save to global config variable
    global config
    config = copy.deepcopy(_config_user)
    _merge_dicts(config, _config_default)

    # Ensure that the root level only contains dictionaries or lists to avoid issues
    for key in config:
        if key == PARENT:
            continue
        if not isinstance(config[key], (dict, list)):
            raise SparvErrorMessage(
                f"The config section '{key}' could not be parsed.", module="sparv", function="config"
            )


def _get(name: str, config_dict: dict | None = None) -> Any:
    """Try to get value from config, raising an exception if key doesn't exist.

    Args:
        name: Config key to look up.
        config_dict: Dictionary to look up key in. If None, the global config is used.

    Returns:
        The value of the config key. If the key is not found, a KeyError is raised.
    """
    config_dict = config_dict if config_dict is not None else config
    # Handle dot notation
    return reduce(lambda c, k: c[k], name.split("."), config_dict)


def set_value(name: str, value: Any, overwrite: bool = True, config_dict: dict | None = None) -> None:
    """Set value in config, possibly using dot notation.

    Args:
        name: Config key to set.
        value: Value to set.
        overwrite: If False, only set value if key doesn't exist.
        config_dict: Dictionary to set key in. If None, the global config is used.
    """
    keys = name.split(".")
    prev = config_dict if config_dict is not None else config
    for key in keys[:-1]:
        prev.setdefault(key, {})
        prev = prev[key]
    if overwrite:
        prev[keys[-1]] = value
    else:
        prev.setdefault(keys[-1], value)


def get(name: str, default: Any = None) -> Any:
    """Get value from config, or return the supplied 'default' if key doesn't exist.

    Args:
        name: Config key to look up.
        default: Value to return if key doesn't exist.

    Returns:
        The value of the config key, or the default value if the key is not found.
    """
    try:
        return _get(name)
    except KeyError:
        return default


def set_default(name: str, default: Any = None) -> None:
    """Set config value to default if key is not already set, or if it is set to None.

    Args:
        name: Config key.
        default: Value to set if key is not already set.
    """
    if default is not None:
        try:
            if _get(name) is None:
                set_value(name, default)
        except KeyError:
            set_value(name, default, overwrite=False)
    else:
        set_value(name, default, overwrite=False)


def extend_config(new_config: dict) -> None:
    """Extend existing config with new values for missing keys.

    Args:
        new_config: Dictionary with new config values.
    """
    _merge_dicts(config, new_config)


def update_config(new_config: dict) -> None:
    """Update existing config with new values, replacing existing values.

    Args:
        new_config: Dictionary with new config values.
    """
    _merge_dicts_replace(config, new_config)


def _merge_dicts(d: dict, default: dict) -> None:
    """Merge dict 'd' with dict 'default', adding missing keys from 'default'.

    The dictionary 'd' is modified in place.

    Args:
        d: Main dictionary to merge into.
        default: Dictionary with default values to merge.
    """
    if isinstance(d, dict) and isinstance(default, dict):
        for k, v in default.items():
            if k not in d:
                d[k] = v
            else:
                _merge_dicts(d[k], v)


def _merge_dicts_replace(d: dict, new_dict: dict) -> None:
    """Merge dict 'd' with dict 'new_dict', replacing existing values.

    The dictionary 'd' is modified in place.

    Args:
        d: Main dictionary to merge into.
        new_dict: Dictionary with new values to merge.
    """
    if isinstance(d, dict) and isinstance(new_dict, dict):
        for k, v in new_dict.items():
            if k in d:
                if isinstance(d[k], dict) and isinstance(v, dict):
                    _merge_dicts_replace(d[k], v)
                else:
                    d[k] = v
            else:
                d[k] = v


def add_to_structure(cfg: Config, annotator: str | None = None) -> None:
    """Add config variable to config structure.

    Args:
        cfg: Config object to add.
        annotator: Name of annotator using the config.
    """
    set_value(cfg.name, {"_cfg": cfg, "_source": "module"}, config_dict=config_structure)

    if annotator:
        add_config_usage(cfg.name, annotator)


def get_config_description(name: str) -> str | None:
    """Get description for config key.

    Args:
        name: Config key.

    Returns:
        Description of the config key.
    """
    cfg = _get(name, config_structure).get("_cfg")
    return cfg.description if cfg else None


def get_config_object(name: str) -> Config | None:
    """Get original Config object for config key.

    Args:
        name: Config key.

    Returns:
        Config object for the config key.
    """
    return _get(name, config_structure).get("_cfg")


def add_config_usage(config_key: str, annotator: str) -> None:
    """Add an annotator to the list of annotators that are using a given config key.

    Args:
        config_key: Config key.
        annotator: Name of annotator using the config key.
    """
    config_usage[config_key].add(annotator)


def validate_module_config() -> None:
    """Make sure that modules don't try to access undeclared config keys.

    Raises:
        SparvErrorMessage: If an annotator tries to access a config key that isn't declared anywhere.
    """
    for config_key in config_usage:
        try:
            _get(config_key, config_structure)
        except KeyError:
            annotators = config_usage[config_key]
            raise SparvErrorMessage(
                "The annotator{} {} {} trying to access the config key '{}' which isn't declared anywhere.".format(
                    "s" if len(annotators) > 1 else "",
                    ", ".join(annotators),
                    "are" if len(annotators) > 1 else "is",
                    config_key,
                ),
                "sparv",
                "config",
            ) from None


def load_presets(lang: str, lang_variety: str | None) -> dict:
    """Read presets files and return dictionaries with all available preset annotations and preset classes.

    Args:
        lang: Language code.
        lang_variety: Language variety.

    Returns:
        Dictionary with all available preset annotations and preset classes.
    """
    class_dict = {}
    full_lang = f"{lang}-{lang_variety}" if lang_variety else lang

    for f in PRESETS_DIR.rglob("*.yaml"):
        presets_yaml = read_yaml(f)

        # Skip preset if it is not valid for lang
        if lang:
            languages = presets_yaml.get("languages", [])
            if languages and lang not in languages and full_lang not in languages:
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


def resolve_presets(annotations: list[str], class_dict: dict) -> tuple[list[str], dict]:
    """Resolve annotation presets into actual annotations.

    Args:
        annotations: List of annotations with possible presets to resolve.
        class_dict: Dictionary with classes set by each preset.

    Returns:
        Tuple with resolved annotations and classes set by the used presets.
    """
    result_annotations = []
    preset_classes = {}
    for annotation in annotations:
        if annotation in presets:
            if annotation in class_dict:
                _merge_dicts(preset_classes, class_dict[annotation])
            resolved_annotations, resolved_classes = resolve_presets(presets[annotation], class_dict)
            result_annotations.extend(resolved_annotations)
            _merge_dicts(preset_classes, resolved_classes)
        else:
            result_annotations.append(annotation)
    return result_annotations, preset_classes


def apply_presets() -> None:
    """Resolve annotations from presets in all annotation lists, and set preset classes."""
    # Load annotation presets and classes
    class_dict = load_presets(get("metadata.language"), get("metadata.variety"))
    all_preset_classes = {}

    # Go through annotation lists in config to find references to presets
    for a in registry.annotation_sources:
        annotations = get(a)
        if not annotations:
            continue

        # Resolve presets and update annotation list in config
        annotations, preset_classes = resolve_presets(annotations, class_dict)
        _merge_dicts(all_preset_classes, preset_classes)
        set_value(a, annotations)

    # Update classes
    default_classes = _config_default.get(
        "classes",
        {
            "sentence": "segment.sentence",
            "token": "segment.token",
            "token:word": "<token>:misc.word",
            "token:ref": "<token>:misc.ref",
        },
    )
    user_classes = _config_user.get("classes", {}).copy()
    _merge_dicts(all_preset_classes, default_classes)
    _merge_dicts(user_classes, all_preset_classes)
    config["classes"] = user_classes


def handle_text_annotation() -> None:
    """Copy text annotation to text class.

    Raises:
        SparvErrorMessage: If classes.text and import.text_annotation have different values.
    """
    text_ann = get("import.text_annotation")

    # Make sure that if both classes.text and import.text_annotation are set, that they have the same value
    if get("classes.text") and text_ann and get("classes.text") != text_ann:
        raise SparvErrorMessage(
            "The config keys 'classes.text' and 'import.text_annotation' can't have different values.",
            "sparv",
            "config",
        )

    # If import.text_annotation is set, copy value to classes.text
    if text_ann:
        set_default("classes.text", text_ann)


def inherit_config(source: str, target: str) -> None:
    """Let 'target' inherit config values from 'source' for every key that is supported and not already populated.

    Only keys that are either missing or have a value of None in the target will inherit the source's value. Falsy
    values like empty strings or lists will not be overwritten.

    Args:
        source: Module name of the source.
        target: Module name of the target.
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
