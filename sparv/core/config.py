"""Functions for parsing the Sparv configuration files."""

import copy
import logging
from collections import defaultdict
from functools import reduce
from typing import Any, Optional

import yaml

from sparv import util
from sparv.core import paths

log = logging.getLogger(__name__)

DEFAULT_CONFIG = paths.default_config_file
PRESETS_DIR = paths.presets_dir

config_user = {}  # Dict holding local corpus config
config = {}  # Dict holding full configuration
config_undeclared = set()  # Config variables collected from use in modules but not declared anywhere
presets = {}  # Dict holding annotation presets

# Dict with info about config structure, prepopulated with some module-independent keys
config_structure = {
    "metadata": {
        "id": {"_source": "core"},
        "name": {"_source": "core"},
        "language": {"_source": "core"},
        "description": {"_source": "core"}
    },
    "classes": {"_source": "core"},
    "import": {
        "document_annotation": {"_source": "core"},
        "encoding": {"_source": "core"},
        "importer": {"_source": "core"},
        "keep_control_chars": {"_source": "core"},
        "normalize": {"_source": "core"},
        "source_dir": {"_source": "core"}
    },
    "export": {
        "default": {"_source": "core"},
        "annotations": {"_source": "core"},
        "source_annotations": {"_source": "core"},
        "header_annotations": {"_source": "core"},
        "word": {"_source": "core"},
        "remove_module_namespaces": {"_source": "core"},
        "sparv_namespace": {"_source": "core"},
        "source_namespace": {"_source": "core"},
        "scramble_on": {"_source": "core"}
    },
    "custom_annotations": {"_source": "core"},
    "install": {"_source": "core"}
}

config_usage = defaultdict(set)  # For each config key, a list of annotators using that key


def read_yaml(yaml_file):
    """Read YAML file and handle errors."""
    try:
        with open(yaml_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.scanner.ScannerError as e:
        raise util.SparvErrorMessage("An error occurred while reading the configuration file:\n" + str(e))

    return data


def load_config(config_file: Optional[str], config_dict: Optional[dict] = None) -> None:
    """Load both default config and corpus config and merge into one config structure.

    Args:
        config_file: Path to corpus config file. If None, only the default config is read.
        config_dict: Get corpus config from dictionary instead of config file.
    """
    # Read default config
    if DEFAULT_CONFIG.is_file():
        default_config = read_yaml(DEFAULT_CONFIG)
    else:
        log.warning("Default config file is missing: {}".format(DEFAULT_CONFIG))
        default_config = {}
    default_classes = default_config.get("classes", {})

    if config_file:
        # Read corpus config
        global config_user
        config_user = read_yaml(config_file) or {}
    elif config_dict:
        config_user = config_dict
    else:
        config_user = {}
    user_classes = config_user.get("classes", {})

    # Merge default and corpus config and save to global config variable
    global config
    config = _merge_dicts(copy.deepcopy(config_user), default_config)

    # Set correct classes and annotations from presets
    apply_presets(user_classes, default_classes)

    if config_file:
        fix_document_annotation()

    # Make sure that the root level only contains dictionaries or lists to save us a lot of headache
    for key in config:
        if not isinstance(config[key], (dict, list)):
            raise util.SparvErrorMessage(f"The config section '{key}' could not be parsed.", module="sparv",
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
        config_undeclared.add(name)
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


def add_to_structure(name, default=None, description=None, annotator=None):
    """Add config variable to config structure."""
    set_value(name,
              {"_default": default,
               "_description": description,
               "_source": "module"},
              config_dict=config_structure
              )

    add_config_usage(name, annotator)


def get_config_description(name):
    """Get discription for config key."""
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
                "The annotator{} {} is trying to access the config key '{}' which isn't declared anywhere.".format(
                    "s" if len(annotators) > 1 else "", ", ".join(annotators), config_key), "sparv", "config")


def validate_config(config_dict=None, structure=None, parent=""):
    """Make sure the corpus config doesn't contain invalid keys."""
    config_dict = config_dict or config_user
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


def resolve_presets(annotations, omits=set()):
    """Resolve annotation presets into actual annotations."""
    result = []
    for annotation in annotations:
        if annotation in presets:
            current_result, current_omits = resolve_presets(presets[annotation], omits)
            result.extend(current_result)
            omits.update(current_omits)
        elif annotation.startswith("not "):
            omits.add(annotation[4:])
        else:
            result.append(annotation)
    # Remove omitted annotations
    result = [a for a in result if a not in omits]
    return result, omits


def apply_presets(user_classes, default_classes):
    """Set correct classes and annotations from presets."""
    # Load annotation presets and classes
    class_dict = load_presets(get("metadata.language"))
    annotation_elems = _find_annotations("", config)
    preset_classes = {}

    for a in annotation_elems:
        # Update annotations
        preset_classes.update(_collect_classes(get(a), class_dict))
        annotations, _omits = resolve_presets(get(a))
        set_value(a, annotations)

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


def fix_document_annotation():
    """Do special treatment for document annotation."""
    # Check that classes.text is not set
    if get("classes.text") is not None:
        raise util.SparvErrorMessage(
            "The config value 'classes.text' cannot be set manually. Use 'import.document_annotation' instead!",
            "sparv", "config")

    # Check that import.document_annotation is set
    doc_elem = get("import.document_annotation")
    if doc_elem is None:
        raise util.SparvErrorMessage("The config value 'import.document_annotation' must be set!", "sparv", "config")

    # Set classes.text and
    set_default("classes.text", doc_elem)

    # Add doc_elem to xml_import.elements
    xml_import_elems = get("xml_import.elements")
    if xml_import_elems is None:
        set_default("xml_import.elements", [doc_elem])
    elif doc_elem not in xml_import_elems:
        xml_import_elems.append(doc_elem)


def inherit_config(source: str, target: str) -> None:
    """Let 'target' inherit config values from 'source' for evey key that is supported and not already populated.

    Only keys which are either missing or with a value of None in the target will inherit the source's value, meaning
    that falsy values like empty strings or lists will not be overwritten.

    Args:
        source: Module name of source.
        target: Module name of target.
    """
    for key in config[source]:
        if key in config_structure.get(target, []):
            value = None
            try:
                value = _get(f"{target}.{key}")
            except KeyError:
                pass
            if value is None:
                set_value(f"{target}.{key}", config[source][key])
