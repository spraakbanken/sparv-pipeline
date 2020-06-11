"""Builds a registry of all available annotator functions in Sparv modules."""
import importlib
import inspect
import pkgutil
import re
from collections import defaultdict
from enum import Enum
from typing import List, Optional

from sparv.core import config as sparv_config
from sparv.core import paths
from sparv.util import split_annotation
from sparv.util.classes import Config, ModelOutput, Output

modules_path = ".".join(("sparv", paths.modules_dir))


class Annotator(Enum):
    """Annotator types."""

    annotator = 1
    importer = 2
    exporter = 3
    installer = 4
    modelbuilder = 5
    custom_annotator = 6


# All available annotator functions
annotators = {}

# All available annotation classes, collected from different sources
annotation_classes = {
    # Classes from modules
    "module_classes": defaultdict(list),

    # Classes from config, either new classes or overriding the above
    "config_classes": {}
}


def find_modules(no_import=False) -> list:
    """Find Sparv modules and optionally import them.

    By importing a module containing annotator functions, the functions will automatically be
    added to the registry.

    Args:
        no_import: Set to True to disable importing of modules.

    Returns:
        A list of available module names.
    """
    modules_full_path = paths.sparv_path / paths.modules_dir
    found_modules = pkgutil.iter_modules([modules_full_path])
    modules = []
    for module in found_modules:
        modules.append(module.name)
        if not no_import:
            importlib.import_module(".".join((modules_path, module.name)))
    return modules


def _annotator(description: str, a_type: Annotator, name: Optional[str] = None, source_type: Optional[str] = None,
               outputs=(), language: Optional[List[str]] = None, config: Optional[List[Config]] = None,
               order: Optional[int] = None):
    """Return a decorator for annotator functions, adding them to annotator registry."""
    def decorator(f):
        """Add wrapped function to registry."""
        module_name = f.__module__[len(modules_path) + 1:].split(".")[0]
        _add_to_registry({
            "module_name": module_name,
            "description": description,
            "function": f,
            "name": name,
            "type": a_type,
            "source_type": source_type,
            "outputs": outputs,
            "language": language,
            "config": config,
            "order": order
        })
        return f

    return decorator


def annotator(description: str, name: Optional[str] = None, language: Optional[List[str]] = None,
              config: Optional[List[Config]] = None, order: Optional[int] = None):
    """Return a decorator for annotator functions, adding them to the annotator registry."""
    return _annotator(description=description, a_type=Annotator.annotator, name=name, language=language,
                      config=config, order=order)


def importer(description: str, source_type: str, name: Optional[str] = None, outputs=None,
             config: Optional[List[Config]] = None):
    """Return a decorator for importer functions.

    Args:
        description: Description of importer.
        source_type: The file extension of the type of source this importer handles, e.g. "xml" or "txt".
        name: Optional name to use instead of the function name.
        outputs: A list of annotations and attributes that the importer is guaranteed to generate.
            May also be a Config instance referring to such a list.
            It may generate more outputs than listed, but only the annotations listed here will be available
            to use as input for annotator functions.
        config: List of Config instances defining config options for the importer.

    Returns:
        A decorator
    """
    return _annotator(description=description, a_type=Annotator.importer, name=name, source_type=source_type,
                      outputs=outputs, config=config)


def exporter(description: str, name: Optional[str] = None, config: Optional[List[Config]] = None,
             language: Optional[List[str]] = None, order: Optional[int] = None):
    """Return a decorator for exporter functions."""
    return _annotator(description=description, a_type=Annotator.exporter, name=name, config=config, language=language,
                      order=order)


def installer(description: str, name: Optional[str] = None, config: Optional[List[Config]] = None):
    """Return a decorator for installer functions."""
    return _annotator(description=description, a_type=Annotator.installer, name=name, config=config)


def modelbuilder(description: str, name: Optional[str] = None, config: Optional[List[Config]] = None,
                 language: Optional[List[str]] = None, order: Optional[int] = None):
    """Return a decorator for modelbuilder functions."""
    return _annotator(description=description, a_type=Annotator.modelbuilder, name=name, config=config,
                      language=language, order=order)


def custom_annotator(description: Optional[str] = None, name: Optional[str] = None,
                     config: Optional[List[Config]] = None, language: Optional[List[str]] = None,
                     order: Optional[int] = None):
    """Return a decorator for custom_annotator functions."""
    return _annotator(description=description, a_type=Annotator.custom_annotator, name=name, config=config, language=language,
                      order=order)


def _add_to_registry(annotator):
    """Add function to annotator registry. Used by annotator."""
    module_name = annotator["module_name"]

    # Add config variables to config
    if annotator["config"]:
        # Only add config for relevant languages
        if not annotator["language"] or (
                annotator["language"] and sparv_config.get("metadata.language") in annotator["language"]):
            for c in annotator["config"]:
                if not c.name.startswith(module_name + "."):
                    raise ValueError("Config option '{}' in module '{}' doesn't include module "
                                     "name as prefix.".format(c.name, module_name))
                sparv_config.set_default(c.name, c.default)

    for param, val in inspect.signature(annotator["function"]).parameters.items():
        if isinstance(val.default, Output):
            ann = val.default
            cls = val.default.cls
            ann_name, attr = split_annotation(ann)

            # Make sure annotation names include module names as prefix
            if not attr:
                if not ann_name.startswith(module_name + "."):
                    raise ValueError("Output annotation '{}' in module '{}' doesn't include module "
                                     "name as prefix.".format(ann_name, module_name))
            else:
                if not attr.startswith(module_name + "."):
                    raise ValueError("Output annotation '{}' in module '{}' doesn't include module "
                                     "name as prefix in attribute.".format(ann, module_name))

            # Add to class registry
            if cls:
                # Only add classes for relevant languages
                if not annotator["language"] or (
                        annotator["language"] and sparv_config.get("metadata.language") in annotator["language"]):
                    if ":" in cls and not cls.startswith(":") and ann_name and attr:
                        annotation_classes["module_classes"][cls].append(ann)
                    elif cls.startswith(":") and attr:
                        annotation_classes["module_classes"][cls].append(attr)
                    elif ":" not in cls:
                        annotation_classes["module_classes"][cls].append(ann_name)
                    else:
                        print("Malformed class name: '{}'".format(cls))

        if isinstance(val.default, ModelOutput):
            modeldir = val.default.split("/")[0]
            if not modeldir.startswith(module_name):
                raise ValueError("Output model '{}' in module '{}' doesn't include module "
                                 "name as sub directory.".format(ann, module_name))

    annotators.setdefault(module_name, {})
    f_name = annotator["function"].__name__ if not annotator["name"] else annotator["name"]
    if f_name in annotators[module_name]:
        print("Annotator function '{}' collides with other function with same name in module '{}'.".format(f_name,
                                                                                                           module_name))
    else:
        del annotator["module_name"]
        del annotator["name"]
        annotators[module_name][f_name] = annotator


def _expand_class(cls):
    """Convert class name to annotation.

    Classes from config takes precedence over classes automatically collected from modules.
    """
    annotation = None
    if cls in annotation_classes["config_classes"]:
        annotation = annotation_classes["config_classes"][cls]
    elif cls in annotation_classes["module_classes"]:
        annotation = annotation_classes["module_classes"][cls][0]
    return annotation


def expand_variables(string, module_name):
    """Take a string and replace <class> references with real annotations, and [config] references with config values.

    Return the resulting string.
    """
    rest = []
    # Convert config keys to config values
    while True:
        cfgs = list(re.finditer(r"\[([^\]=[]+)(?:=([^\][]+))?\]", string))
        if not cfgs:
            break
        for cfg in cfgs:
            cfg_value = sparv_config.get(cfg.group(1), cfg.group(2))
            if cfg_value is not None:
                string = string.replace(cfg.group(), cfg_value)
            else:
                rest.append(cfg.group()[1:-1])
                break
        else:
            # No break occurred, continue outer loop
            continue
        break

    # Convert class names to real annotations
    while True:
        clss = list(re.finditer(r"<([^>]+)>", string))
        if not clss:
            break
        for cls in clss:
            real_ann = _expand_class(cls.group(1))
            assert real_ann, "Could not convert " + cls.group() + " into a real annotation (used in " + module_name + ")."
            string = string.replace(cls.group(), real_ann)

    return string, rest


def dig(needle, haystack):
    """Go though 'haystack' and return any objects of the type 'needle' found.

    The haystack may be a list, tuple, dict or a combination of the three. It may also be equal to or an instance of
    the needle.
    The needle can be any type except for list, tuple and dict.
    """
    needles = []
    if isinstance(haystack, list):
        for item in haystack:
            found = dig(needle, item)
            needles.extend(found)

    elif isinstance(haystack, dict):
        for key in haystack:
            found = dig(needle, haystack[key])
            needles.extend(found)

    elif type(haystack) == needle or haystack == needle:
        # We've found what we're looking for
        return [haystack]

    return needles
