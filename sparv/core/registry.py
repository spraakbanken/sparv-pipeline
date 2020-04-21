"""Builds a registry of all available annotator functions in Sparv modules."""
import importlib
import inspect
import os
import pkgutil
import re
from collections import defaultdict

from sparv.core import config, paths
from sparv.util import split_annotation
from sparv.util.classes import Output

modules_path = ".".join(("sparv", paths.modules_dir))

# All available annotator functions
annotators = {}

# All available annotation classes, collected from different sources
annotation_classes = {
    # Classes from modules
    "module_classes": defaultdict(list),

    # Classes from config, either new classes or overriding the above
    "config_classes": {}
}


def find_modules(sparv_path, no_import=False):
    """Find Sparv modules and optionally import them."""
    modules_full_path = os.path.join(sparv_path, paths.modules_dir)
    found_modules = pkgutil.iter_modules([modules_full_path])
    modules = []
    for module in found_modules:
        modules.append(module.name)
        if not no_import:
            importlib.import_module(".".join((modules_path, module.name)))
    return modules


def _annotator(description: str, name=None, importer=False, exporter=False, source_type=None, outputs=()):
    """Return a decorator for annotator, importer and exporter functions, adding them to annotator registry."""
    def decorator(f):
        """Add wrapped function to registry."""
        module_name = f.__module__[len(modules_path) + 1:].split(".")[0]
        _add_to_registry(module_name, description, f, name, importer, exporter, source_type, outputs)
        return f

    return decorator


def annotator(description: str, name=None):
    """Return a decorator for annotator functions, adding them to the annotator registry."""
    return _annotator(description, name)


def importer(description: str, source_type: str, name=None, outputs=None):
    """Return a decorator for importer functions.

    Args:
        description: Description of importer.
        source_type: The file extension of the type of source this importer handles, e.g. "xml" or "txt".
        name: Optional name to use instead of the function name.
        outputs: A list of annotations and attributes that the importer is guaranteed to generate.
            May also be a Config instance referring to such a list.
            It may generate more outputs than listed, but only the annotations listed here will be available
            to use as input for annotator functions.

    Returns:
        A decorator
    """
    return _annotator(description, name, importer=True, source_type=source_type, outputs=outputs)


def exporter(description: str, name=None):
    """Return a decorator for exporter functions."""
    return _annotator(description, name, exporter=True)


def _add_to_registry(module_name: str, description: str, f, name, importer, exporter, source_type, outputs):
    """Add function to annotator registry. Used by annotator."""
    for param, val in inspect.signature(f).parameters.items():
        if (val.annotation == Output or isinstance(val.default, Output)) and not val.default == inspect.Parameter.empty:
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
                if ":" in cls and not cls.startswith(":") and ann_name and attr:
                    annotation_classes["module_classes"][cls].append(ann)
                elif cls.startswith(":") and attr:
                    annotation_classes["module_classes"][cls].append(attr)
                elif ":" not in cls:
                    annotation_classes["module_classes"][cls].append(ann_name)
                else:
                    print("Malformed class name: '{}'".format(cls))

    annotators.setdefault(module_name, {})
    f_name = f.__name__ if not name else name
    if f_name in annotators[module_name]:
        print("Annotator function '{}' collides with other function with same name in module '{}'.".format(f_name,
                                                                                                           module_name))
    else:
        annotators[module_name][f_name] = (f, description, importer, exporter, source_type, outputs)


def _expand_class(cls):
    annotation = None
    if cls in annotation_classes["config_classes"]:
        annotation = annotation_classes["config_classes"][cls]
    elif cls in annotation_classes["module_classes"]:
        annotation = annotation_classes["module_classes"][cls][0]
    return annotation


def expand_variables(string):
    """Take a string and replace <class> references with real annotations, and [config] references with config values.

    Return the resulting string.
    """
    # Convert config keys to config values
    while True:
        cfgs = list(re.finditer(r"\[([^\]=[]+)(?:=([^\][]+))?\]", string))
        if not cfgs:
            break
        for cfg in cfgs:
            cfg_value = config.get(cfg.group(1), cfg.group(2))
            if cfg_value is not None:
                string = string.replace(cfg.group(), cfg_value)
            else:
                print("WARNING: Could not convert " + cfg.group() + " into config value.")
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
            assert real_ann, "Could not convert " + cls.group() + " into a real annotation."
            string = string.replace(cls.group(), real_ann)

    return string


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

    elif type(haystack) == needle or (type(needle) == type and haystack == needle):
        # We've found what we're looking for
        return [haystack]

    return needles
