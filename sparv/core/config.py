"""Functions for parsing the Sparv configuration files."""

import copy
from collections import defaultdict
from functools import reduce
from pathlib import Path
from typing import Any, Optional, Union

import yaml
import yaml.scanner

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from sparv.api.classes import Config
from sparv.core import paths, registry
from sparv.core.misc import SparvErrorMessage, get_logger

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
    "classes": {"_source": "core", "_cfg": Config("classes", datatype=dict)},
    "custom_annotations": {"_source": "core", "_cfg": Config("custom_annotations", datatype=list)},
    "install": {
        "_source": "core",
        "_cfg": Config("install", description="List of default installers to run", datatype=list)
    },
    PARENT: {"_source": "core", "_cfg": Config(PARENT, datatype=str)},
    MAX_THREADS: {"_source": "core", "_cfg": Config(MAX_THREADS, datatype=dict[str, int])},
    "preload": {"_source": "core", "_cfg": Config("preload", datatype=list)},
    "uninstall": {"_source": "core", "_cfg": Config("uninstall", datatype=list)}
}

config_usage = defaultdict(set)  # For each config key, a list of annotators using that key


class Unset:
    """Class used to represent a config value that isn't set."""


def read_yaml(yaml_file: Union[str, Path]) -> dict:
    """Read YAML file and handle errors."""
    try:
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.load(f, Loader=SafeLoader)
    except yaml.parser.ParserError as e:
        raise SparvErrorMessage("Could not parse the configuration file:\n" + str(e))
    except yaml.scanner.ScannerError as e:
        raise SparvErrorMessage("An error occurred while reading the configuration file:\n" + str(e))
    except FileNotFoundError:
        raise SparvErrorMessage(f"Could not find the config file '{yaml_file}'")

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
        logger.warning("Default config file is missing: %s", DEFAULT_CONFIG)
        _config_default = {}

    if config_file:
        # Read corpus config
        global _config_user
        _config_user = read_yaml(config_file) or {}

        def handle_parents(cfg, current_dir=Path()) -> dict:
            """Combine parent configs recursively."""
            combined_parents = {}
            if cfg.get(PARENT):
                parents = cfg[PARENT]
                if isinstance(parents, str):
                    parents = [parents]
                for parent in parents:
                    parent_path = current_dir / parent
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
            raise SparvErrorMessage(f"The config section '{key}' could not be parsed.", module="sparv",
                                    function="config")


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


def _merge_dicts(d: dict, default: dict):
    """Merge dict 'd' with dict 'default', letting values from 'd' override default values."""
    if isinstance(d, dict) and isinstance(default, dict):
        for k, v in default.items():
            if k not in d:
                d[k] = v
            else:
                d[k] = _merge_dicts(d[k], v)
    return d


def add_to_structure(cfg: Config, annotator: Optional[str] = None):
    """Add config variable to config structure."""
    set_value(
        cfg.name,
        {
            "_cfg": cfg,
            "_source": "module"
        },
        config_dict=config_structure
    )

    if annotator:
        add_config_usage(cfg.name, annotator)


def get_config_description(name):
    """Get description for config key."""
    cfg = _get(name, config_structure).get("_cfg")
    return cfg.description if cfg else None


def get_config_object(name: str) -> Optional[Config]:
    """Get original Config object for config key."""
    return _get(name, config_structure).get("_cfg")


def add_config_usage(config_key, annotator):
    """Add an annotator to the list of annotators that are using a given config key."""
    config_usage[config_key].add(annotator)


def validate_module_config():
    """Make sure that modules don't try to access undeclared config keys."""
    for config_key in config_usage:
        try:
            _get(config_key, config_structure)
        except KeyError:  # noqa: PERF203
            annotators = config_usage[config_key]
            raise SparvErrorMessage(
                "The annotator{} {} {} trying to access the config key '{}' which isn't declared anywhere.".format(
                    "s" if len(annotators) > 1 else "", ", ".join(annotators),
                    "are" if len(annotators) > 1 else "is", config_key), "sparv", "config") from None


def load_presets(lang, lang_variety):
    """Read presets files and return dictionaries with all available presets annotations and preset classes."""
    class_dict = {}
    full_lang = lang
    if lang_variety:
        full_lang = lang + "-" + lang_variety

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


def resolve_presets(annotations, class_dict, preset_classes):
    """Resolve annotation presets into actual annotations."""
    result_annotations = []
    for annotation in annotations:
        if annotation in presets:
            if annotation in class_dict:
                preset_classes = _merge_dicts(preset_classes, class_dict[annotation])
            result_annotations.extend(resolve_presets(presets[annotation], class_dict, preset_classes)[0])
        else:
            result_annotations.append(annotation)
    return result_annotations, preset_classes


def apply_presets():
    """Resolve annotations from presets and set preset classes."""
    # Load annotation presets and classes
    class_dict = load_presets(get("metadata.language"), get("metadata.variety"))
    preset_classes = {}

    # Go through annotation lists in config to find references to presets
    for a in registry.annotation_sources:
        annotations = get(a)
        if not annotations:
            continue

        # Resolve presets and update annotation list in config
        annotations, preset_classes = resolve_presets(annotations, class_dict, preset_classes)
        set_value(a, annotations)

    # Update classes
    default_classes = _config_default.get("classes", {})
    user_classes = _config_user.get("classes", {}).copy()
    combined_classes = _merge_dicts(preset_classes, default_classes)
    classes = _merge_dicts(user_classes, combined_classes)
    config["classes"] = classes


def handle_text_annotation():
    """Copy text annotation to text class."""
    text_ann = get("import.text_annotation")

    # Make sure that if both classes.text and import.text_annotation are set, that they have the same value
    if get("classes.text") and text_ann and get("classes.text") != text_ann:
        raise SparvErrorMessage(
            "The config keys 'classes.text' and 'import.text_annotation' can't have different values.",
            "sparv", "config")

    # If import.text_annotation is set, copy value to classes.text
    if text_ann:
        set_default("classes.text", text_ann)


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
