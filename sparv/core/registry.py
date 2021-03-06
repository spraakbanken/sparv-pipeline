"""Builds a registry of all available annotator functions in Sparv modules."""
import importlib
import inspect
import pkgutil
import re
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Type, TypeVar

import typing_inspect
from pkg_resources import iter_entry_points

from sparv.core import config as sparv_config
from sparv.core import paths
from sparv.util.classes import (BaseOutput, Config, ExportAnnotations, ExportAnnotationsAllDocs, SourceStructureParser,
                                ModelOutput, Wildcard)

modules_path = ".".join(("sparv", paths.modules_dir))
core_modules_path = ".".join(("sparv", paths.core_modules_dir))
custom_name = "custom"


class Annotator(Enum):
    """Annotator types."""

    annotator = 1
    importer = 2
    exporter = 3
    installer = 4
    modelbuilder = 5


class Module:
    """Class holding data about Sparv modules."""

    def __init__(self, name):
        self.name = name
        self.functions: Dict[str, dict] = {}
        self.description = None


# All loaded Sparv modules with their functions (possibly limited by the selected language)
modules: Dict[str, Module] = {}

# All available annotation classes for the selected language, collected from modules and corpus config
annotation_classes = {
    # Classes from modules
    "module_classes": defaultdict(list),

    # Classes from annotation usage
    "implicit_classes": {},

    # Classes from config, either new classes or overriding the above
    "config_classes": {}
}

# All available module classes sorted by language. This is only used by the wizard.
all_module_classes = defaultdict(lambda: defaultdict(list))

# All available wizard functions
wizards = []

# All available languages
languages = set()

# All config keys containing lists of automatic annotations (i.e. ExportAnnotations)
annotation_sources = set()

# All explicitly used annotations (with classes expanded)
explicit_annotations = set()

# All explicitly used annotations (without class-expansion)
explicit_annotations_raw = set()


def find_modules(no_import=False, find_custom=False) -> list:
    """Find Sparv modules and optionally import them.

    By importing a module containing annotator functions, the functions will automatically be
    added to the registry.

    Args:
        no_import: Set to True to disable importing of modules.
        find_custom: Set to True to also look for scripts in corpus directory.

    Returns:
        A list of available module names.
    """
    modules_full_path = paths.sparv_path / paths.modules_dir
    core_modules_full_path = paths.sparv_path / paths.core_modules_dir

    for full_path, path in ((core_modules_full_path, core_modules_path), (modules_full_path, modules_path)):
        found_modules = pkgutil.iter_modules([full_path])
        module_names = []
        for module in found_modules:
            module_names.append(module.name)
            if not no_import:
                m = importlib.import_module(".".join((path, module.name)))
                add_module_metadata(m, module.name)

    if find_custom:
        # Also search for modules in corpus dir
        custom_modules = pkgutil.iter_modules([paths.corpus_dir])
        for module in custom_modules:
            module_name = f"{custom_name}.{module.name}"
            module_names.append(module_name)
            if not no_import:
                module_path = paths.corpus_dir.resolve() / f"{module.name}.py"
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                m = importlib.util.module_from_spec(spec)
                add_module_metadata(m, module_name)
                spec.loader.exec_module(m)

    # Search for installed plugins
    for entry_point in iter_entry_points("sparv.plugin"):
        m = entry_point.load()
        add_module_metadata(m, entry_point.name)
        module_names.append(entry_point.name)

    return module_names


def add_module_metadata(module, module_name):
    """Add module metadata."""
    if hasattr(module, "__config__"):
        for cfg in module.__config__:
            handle_config(cfg, module_name)
    if module_name in modules:
        modules[module_name].description = getattr(module, "__description__", module.__doc__)


def wizard(config_keys: List[str], source_structure: bool = False):
    """Return a wizard decorator."""
    def decorator(f):
        """Add wrapped function to wizard registry."""
        wizards.append((f, tuple(config_keys), source_structure))
        return f
    return decorator


def _get_module_name(module_string: str) -> str:
    """Extract module name from dotted path, i.e. 'modulename.submodule' -> 'modulename'."""
    if module_string.startswith(modules_path):
        # Built-in Sparv module
        module_name = module_string[len(modules_path) + 1:].split(".")[0]
    elif module_string.startswith(core_modules_path):
        # Built-in Sparv core module
        module_name = module_string[len(core_modules_path) + 1:].split(".")[0]
    elif module_string.split(".")[0] == custom_name:
        # Custom user module
        module_name = module_string
    else:
        # External plugin
        module_name = module_string.split(".")[0]
    return module_name


def _annotator(description: str, a_type: Annotator, name: Optional[str] = None, file_extension: Optional[str] = None,
               outputs=(), document_annotation=None, structure=None, language: Optional[List[str]] = None,
               config: Optional[List[Config]] = None, order: Optional[int] = None, abstract: bool = False,
               wildcards: Optional[List[Wildcard]] = None):
    """Return a decorator for annotator functions, adding them to annotator registry."""
    def decorator(f):
        """Add wrapped function to registry."""
        module_name = _get_module_name(f.__module__)
        _add_to_registry({
            "module_name": module_name,
            "description": description,
            "function": f,
            "name": name,
            "type": a_type,
            "file_extension": file_extension,
            "outputs": outputs,
            "document_annotation": document_annotation,
            "structure": structure,
            "language": language,
            "config": config,
            "order": order,
            "abstract": abstract,
            "wildcards": wildcards
        })
        return f

    return decorator


def annotator(description: str, name: Optional[str] = None, language: Optional[List[str]] = None,
              config: Optional[List[Config]] = None, order: Optional[int] = None,
              wildcards: Optional[List[Wildcard]] = None):
    """Return a decorator for annotator functions, adding them to the annotator registry."""
    return _annotator(description=description, a_type=Annotator.annotator, name=name, language=language,
                      config=config, order=order, wildcards=wildcards)


def importer(description: str, file_extension: str, name: Optional[str] = None, outputs=None,
             document_annotation: Optional[str] = None, structure: Optional[Type[SourceStructureParser]] = None,
             config: Optional[List[Config]] = None):
    """Return a decorator for importer functions.

    Args:
        description: Description of importer.
        file_extension: The file extension of the type of source this importer handles, e.g. "xml" or "txt".
        name: Optional name to use instead of the function name.
        outputs: A list of annotations and attributes that the importer is guaranteed to generate.
            May also be a Config instance referring to such a list.
            It may generate more outputs than listed, but only the annotations listed here will be available
            to use as input for annotator functions.
        document_annotation: An annotation from 'outputs' that should be used as the value for the
            import.document_annotation config variable, unless it or classes.text has been set manually.
        structure: A class used to parse and return the structure of source documents.
        config: List of Config instances defining config options for the importer.

    Returns:
        A decorator
    """
    return _annotator(description=description, a_type=Annotator.importer, name=name, file_extension=file_extension,
                      outputs=outputs, document_annotation=document_annotation, structure=structure, config=config)


def exporter(description: str, name: Optional[str] = None, config: Optional[List[Config]] = None,
             language: Optional[List[str]] = None, order: Optional[int] = None, abstract: bool = False):
    """Return a decorator for exporter functions.

    Args:
        description: Description of exporter.
        name: Optional name to use instead of the function name.
        config: List of Config instances defining config options for the exporter.
        language: List of supported languages.
        order: If several exporters have the same output, this integer value will help decide which to try to use first.
        abstract: Set to True if this exporter has no output.

    Returns:
        A decorator
    """
    return _annotator(description=description, a_type=Annotator.exporter, name=name, config=config, language=language,
                      order=order, abstract=abstract)


def installer(description: str, name: Optional[str] = None, config: Optional[List[Config]] = None):
    """Return a decorator for installer functions."""
    return _annotator(description=description, a_type=Annotator.installer, name=name, config=config)


def modelbuilder(description: str, name: Optional[str] = None, config: Optional[List[Config]] = None,
                 language: Optional[List[str]] = None, order: Optional[int] = None):
    """Return a decorator for modelbuilder functions."""
    return _annotator(description=description, a_type=Annotator.modelbuilder, name=name, config=config,
                      language=language, order=order)


def _add_to_registry(annotator):
    """Add function to annotator registry. Used by annotator."""
    module_name = annotator["module_name"]
    f_name = annotator["function"].__name__ if not annotator["name"] else annotator["name"]
    rule_name = f"{module_name}:{f_name}"

    if annotator["language"]:
        # Add to set of supported languages...
        languages.update(annotator["language"])
        # ... but skip annotators for other languages than the one specified in the config
        if sparv_config.get("metadata.language") and sparv_config.get("metadata.language") not in annotator["language"]:
            return

    # Add config variables to config
    if annotator["config"]:
        for c in annotator["config"]:
            handle_config(c, module_name, rule_name)

    # Handle document annotation for selected importer
    if annotator["type"] == Annotator.importer and rule_name == sparv_config.get("import.importer"):
        if annotator["document_annotation"] and not sparv_config.get("classes.text"):
            sparv_config.set_value("import.document_annotation", annotator["document_annotation"])
            sparv_config.handle_document_annotation()

    for param, val in inspect.signature(annotator["function"]).parameters.items():
        if isinstance(val.default, BaseOutput):
            ann = val.default
            cls = val.default.cls
            ann_name, attr = ann.split()

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
                cls_target = None
                if ":" in cls and not cls.startswith(":") and ann_name and attr:
                    cls_target = ann.name
                elif cls.startswith(":") and attr:
                    cls_target = attr
                elif ":" not in cls:
                    cls_target = ann_name
                else:
                    print("Malformed class name: '{}'".format(cls))

                if cls_target:
                    if annotator["language"]:
                        if not annotator["language"]:
                            all_module_classes[None][cls].append(cls_target)
                        else:
                            for language in annotator["language"]:
                                all_module_classes[language][cls].append(cls_target)

                    # Only add classes for relevant languages
                    if not annotator["language"] or (
                            annotator["language"] and sparv_config.get("metadata.language") in annotator["language"]):
                        annotation_classes["module_classes"][cls].append(cls_target)

        elif isinstance(val.default, ModelOutput):
            modeldir = val.default.name.split("/")[0]
            if not modeldir.startswith(module_name):
                raise ValueError("Output model '{}' in module '{}' doesn't include module "
                                 "name as sub directory.".format(val.default, module_name))
        elif isinstance(val.default, Config):
            sparv_config.add_config_usage(val.default.name, rule_name)
        elif isinstance(val.default, (ExportAnnotations, ExportAnnotationsAllDocs)):
            sparv_config.add_config_usage(val.default.config_name, rule_name)
            annotation_sources.add(val.default.config_name)

    if module_name not in modules:
        modules[module_name] = Module(module_name)
    if f_name in modules[module_name].functions:
        print("Annotator function '{}' collides with other function with same name in module '{}'.".format(f_name,
                                                                                                           module_name))
    else:
        del annotator["module_name"]
        del annotator["name"]
        modules[module_name].functions[f_name] = annotator


def find_implicit_classes() -> None:
    """Figure out implicitly defined classes from annotation usage."""

    annotation_to_class = defaultdict(set)
    for class_source in ("module_classes", "config_classes"):
        for cls, anns in annotation_classes[class_source].items():
            if not isinstance(anns, list):
                anns = [anns]
            for ann in anns:
                annotation_to_class[ann].add(cls)
                annotation_to_class[expand_variables(ann)[0]].add(cls)

    for annotation in explicit_annotations_raw:
        for cls in annotation_to_class[annotation]:
            if cls not in annotation_classes["config_classes"] and cls not in annotation_classes["implicit_classes"]:
                annotation_classes["implicit_classes"][cls] = annotation


def handle_config(cfg, module_name, rule_name: Optional[str] = None) -> None:
    """Handle Config instances."""
    if not cfg.name.startswith(module_name + "."):
        raise ValueError("Config option '{}' in module '{}' doesn't include module "
                         "name as prefix.".format(cfg.name, module_name))
    # Check that config variable hasn't already been declared
    prev = sparv_config.config_structure
    for k in cfg.name.split("."):
        if k not in prev:
            break
        prev = prev[k]
    else:
        raise Exception(f"The config variable '{cfg.name}' in '{rule_name or module_name}' has already been declared.")
    if cfg.default is not None:
        sparv_config.set_default(cfg.name, cfg.default)
    sparv_config.add_to_structure(cfg.name, cfg.default, description=cfg.description, annotator=rule_name)
    if not cfg.description:
        raise Exception(f"Missing description for configuration key '{cfg.name}' in module '{module_name}'.")


def _expand_class(cls):
    """Convert class name to annotation.

    Classes from config takes precedence over classes automatically collected from modules.
    """
    annotation = None
    if cls in annotation_classes["config_classes"]:
        annotation = annotation_classes["config_classes"][cls]
    elif cls in annotation_classes["implicit_classes"]:
        annotation = annotation_classes["implicit_classes"][cls]
    elif cls in annotation_classes["module_classes"]:
        annotation = annotation_classes["module_classes"][cls][0]
    return annotation


def find_config_variables(string, match_objects: bool = False):
    """Find all config variables in a string and return a list of strings or match objects."""
    if match_objects:
        result = list(re.finditer(r"\[([^\]=[]+)(?:=([^\][]+))?\]", string))
    else:
        result = [c.group()[1:-1] for c in re.finditer(r"\[([^\]=[]+)(?:=([^\][]+))?\]", string)]
    return result


def find_classes(string, match_objects: bool = False):
    """Find all class references in a string and return a list of strings or match objects."""
    if match_objects:
        result = list(re.finditer(r"<([^>]+)>", string))
    else:
        result = [c.group()[1:-1] for c in re.finditer(r"<([^>]+)>", string)]
    return result


def expand_variables(string, rule_name: Optional[str] = None, is_annotation: bool = False) -> Tuple[str, List[str]]:
    """Take a string and replace <class> references with real annotations, and [config] references with config values.

    Args:
        string: The string to process.
        rule_name: Name of rule using the string, for logging config usage.
        is_annotation: Set to True if string refers to an annotation.

    Returns:
        The resulting string and a list of any unresolved config references.
    """
    rest = []

    if is_annotation:
        # Split if list of alternatives
        strings = string.split(", ")
    else:
        strings = [string]

    for i, string in enumerate(strings):
        # Convert config keys to config values
        while True:
            cfgs = find_config_variables(string, True)
            if not cfgs:
                break
            for cfg in cfgs:
                cfg_value = sparv_config.get(cfg.group(1), cfg.group(2))
                if rule_name:
                    sparv_config.add_config_usage(cfg.group(1), rule_name)
                if cfg_value is not None:
                    string = string.replace(cfg.group(), cfg_value)
                else:
                    rest.append(cfg.group()[1:-1])
                    break
            else:
                # No break occurred, continue outer loop
                continue
            break

        strings[i] = string

    if is_annotation:
        # Split if list of alternatives
        strings = [s for s in string.split(", ") for string in strings]

    for string in strings:
        # Convert class names to real annotations
        while True:
            clss = find_classes(string, True)
            if not clss:
                break
            for cls in clss:
                real_ann = _expand_class(cls.group(1))
                if real_ann:
                    string = string.replace(cls.group(), real_ann)
                else:
                    rest.append(cls.group())
                    break
            else:
                continue
            break

        if is_annotation and len(strings) > 1:
            # If multiple alternative annotations, return the first one that is explicitly used, or the last
            if string in explicit_annotations or clss and set(clss).intersection(explicit_annotations):
                break

    return string, rest


def get_type_hint_type(type_hint):
    """Given a type hint, return the type, whether it's contained in a List and whether it's Optional."""
    optional = typing_inspect.is_optional_type(type_hint)
    if optional:
        type_hint = typing_inspect.get_args(type_hint)[0]
    origin = typing_inspect.get_origin(type_hint)

    is_list = False

    if origin in (list, List, tuple, Tuple):
        is_list = True
        args = typing_inspect.get_args(type_hint)
        if args and not type(args[0]) == TypeVar:
            type_ = args[0]
        else:
            type_ = origin
    else:
        type_ = type_hint

    return type_, is_list, optional
