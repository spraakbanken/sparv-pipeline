"""Builds a registry of all available annotator functions in Sparv modules."""
# ruff: noqa: PLC0415

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from collections import UserDict, defaultdict
from collections.abc import Container, Iterable
from collections.abc import Iterable as TypingIterable
from enum import Enum
from types import ModuleType
from typing import Any, Callable, List, Tuple, TypeVar  # noqa: UP035

import typing_inspect
from sparv.api.classes import (
    BaseOutput,
    Config,
    Export,
    ExportAnnotations,
    ExportAnnotationsAllSourceFiles,
    ModelOutput,
    OutputMarker,
    SourceAnnotations,
    SourceStructureParser,
    Wildcard,
)
from sparv.core import config as sparv_config
from sparv.core.console import console
from sparv.core.misc import SparvErrorMessage
from sparv.core.paths import paths

modules_path = f"sparv.{paths.modules_dir}"
core_modules_path = f"sparv.{paths.core_modules_dir}"
custom_name = "custom"


class Annotator(Enum):
    """Annotator types."""

    annotator = 1
    importer = 2
    exporter = 3
    installer = 4
    uninstaller = 5
    modelbuilder = 6


class Module:
    """Class holding data about Sparv modules."""

    def __init__(self, name: str) -> None:
        """Initialize module."""
        self.name = name
        self.functions: dict[str, dict] = {}
        self.description = None
        self.language = None


class LanguageRegistry(UserDict):
    """Registry for supported languages."""

    def add_language(self, lang: str) -> str:
        """Add language to registry.

        Args:
            lang: Language code plus optional suffix.

        Returns:
            The full language name.
        """
        from sparv.api import util

        if lang not in self:
            langcode, _, suffix = lang.partition("-")
            if iso_lang := util.misc.get_language_name_by_part3(langcode):
                self[lang] = f"{iso_lang} ({suffix})" if suffix else iso_lang
            else:
                self[lang] = lang
        return self[lang]


# Dictionary with annotators that will be added to Sparv unless they are excluded (e.g. due to incompatible language)
_potential_annotators = defaultdict(list)

# All loaded Sparv modules with their functions (possibly limited by the selected language)
modules: dict[str, Module] = {}

# All available annotation classes for the selected language, collected from modules and corpus config
annotation_classes = {
    # Classes from modules
    "module_classes": defaultdict(list),
    # Classes from annotation usage
    "implicit_classes": {},
    # Classes from config, either new classes or overriding the above
    "config_classes": {},
}

# All available module classes sorted by language. This is only used by the wizard.
all_module_classes = defaultdict(lambda: defaultdict(list))

# All available wizard functions
wizards = []

# All supported languages
languages = LanguageRegistry()

# All config keys containing lists of automatic annotations (i.e. ExportAnnotations)
annotation_sources = {"export.annotations"}

# All explicitly used annotations (with classes expanded)
explicit_annotations = set()

# All explicitly used annotations (without class-expansion)
explicit_annotations_raw = set()


def find_modules(no_import: bool = False, find_custom: bool = False, skip_language_check: bool = False) -> list:
    """Find Sparv modules and optionally import them.

    By importing a module containing annotator functions, the functions will automatically be
    added to the registry.

    Args:
        no_import: Set to True to disable importing of modules.
        find_custom: Set to True to also look for scripts in corpus directory.
        skip_language_check: Set to True to skip checking of language compatibility.

    Returns:
        A list of available module names.

    Raises:
        SparvErrorMessage: If a module cannot be imported due to an error.
    """
    from importlib.metadata import entry_points

    from packaging.requirements import Requirement

    # from sparv import __version__ as sparv_version

    print(f"{paths.sparv_path=}")
    modules_full_path = paths.sparv_path.parent.parent.parent / "sparv-modules" / "src" / "sparv" / paths.modules_dir
    modules_stanza_full_path = (
        paths.sparv_path.parent.parent.parent / "sparv-modules-stanza" / "src" / "sparv" / paths.modules_dir
    )
    core_modules_full_path = paths.sparv_path / paths.core_modules_dir

    module_names = []

    for full_path, path, include in (
        (core_modules_full_path, core_modules_path, False),
        (modules_full_path, modules_path, True),
        (modules_stanza_full_path, modules_path, True),
    ):
        print(f"{full_path=}, {path=}, {include=}")
        found_modules = pkgutil.iter_modules([str(full_path)])
        for module in found_modules:
            print(f"{module=}")
            if include:
                # Don't include core modules in the returned list of modules, as they are only used for configuration
                module_names.append(module.name)
            if not no_import:
                m = importlib.import_module(f"{path}.{module.name}")
                add_module_to_registry(m, module.name, skip_language_check=skip_language_check)

    if find_custom:
        custom_annotators = [a.get("annotator", "").split(":")[0] for a in sparv_config.get("custom_annotations", [])]
        # Also search for modules in corpus dir
        custom_modules = pkgutil.iter_modules([str(paths.corpus_dir)])
        for module in custom_modules:
            module_name = f"{custom_name}.{module.name}"
            # Skip modules in corpus dir if they are not used in the corpus config
            if module_name not in custom_annotators:
                continue
            module_names.append(module_name)
            if not no_import:
                module_path = paths.corpus_dir.resolve() / f"{module.name}.py"
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                m = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(m)
                except Exception as e:
                    raise SparvErrorMessage(
                        f"Module '{module_name}' cannot be imported due to an error in file '{module_path}': {e}"
                    ) from None
                add_module_to_registry(m, module_name, skip_language_check=skip_language_check)

    module_name_regex = re.compile(r"^[a-z][a-z0-9]+_[a-z0-9](?:[a-z0-9_]*[a-z0-9])?$")

    # Search for installed plugins
    for entry_point in entry_points(group="sparv.plugin"):
        skip = False

        # Validate module name
        if not module_name_regex.match(entry_point.name):
            console.print(
                f"[red]:warning-emoji:  The plugin module {entry_point.name!r} has an invalid name. The name must, "
                "in addition to being a valid Python identifier, consist of the following parts, in this order:\n\n"
                "    - A namespace prefix representing the plugin author (at least two characters)\n"
                "    - An underscore\n"
                "    - One or more letters, digits, or underscores\n\n"
                "All letters must be lowercase, and the first and last character of the name can not be an "
                "underscore."
            )
            continue

        # Check compatibility with Sparv version
        for requirement in entry_point.dist.requires:
            req = Requirement(requirement)
            if req.name in {"sparv", "sparv-pipeline"}:
                req.specifier.prereleases = True  # Accept pre-release versions of Sparv
                if sparv_version not in req.specifier:
                    console.print(
                        f"[red]:warning-emoji:  The plugin {entry_point.name} ({entry_point.dist.name}) could not "
                        f"be loaded. It requires Sparv version {req.specifier}, but the currently running Sparv "
                        f"version is {sparv_version}.\n"
                    )
                    skip = True
                break

        if skip:
            continue

        if not no_import:
            try:
                m = entry_point.load()
            except Exception as e:
                console.print(
                    f"[red]:warning-emoji:  The plugin {entry_point.name} ({entry_point.dist.name}) could not be "
                    f"loaded:\n\n    {e}"
                )
                continue
            add_module_to_registry(m, entry_point.name, skip_language_check=skip_language_check)

        module_names.append(entry_point.name)

    return module_names


def add_module_to_registry(module: ModuleType, module_name: str, skip_language_check: bool = False) -> None:
    """Add module and its annotators to registry.

    Args:
        module: The Python module to add.
        module_name: The name of the Sparv module.
        skip_language_check: Set to True to skip checking of language compatibility.
    """
    if not skip_language_check and hasattr(module, "__language__"):
        # Add to set of supported languages...
        for lang in module.__language__:
            languages.add_language(lang)
        # ...but skip modules for other languages than the one specified in the config
        if not check_language(
            sparv_config.get("metadata.language"), module.__language__, sparv_config.get("metadata.variety")
        ):
            del _potential_annotators[module_name]
            return
    if hasattr(module, "__config__"):
        for cfg in module.__config__:
            handle_config(cfg, module_name)

    # Add module to registry
    modules[module_name] = Module(module_name)
    modules[module_name].description = getattr(module, "__description__", module.__doc__)
    modules[module_name].language = getattr(module, "__language__", None)

    if not modules[module_name].description:
        console.print(f"[red]WARNING:[/] Module '{module_name}' is missing a description.")

    # Register annotators with Sparv
    for a in _potential_annotators[module_name]:
        if not a["description"]:
            console.print(
                "[red]WARNING:[/] "
                f"{a['type'].name.capitalize()} '{module_name}:{a['name'] or a['function'].__name__}' has no "
                "description."
            )
        # Set annotator language to same as module, unless overridden
        if hasattr(module, "__language__") and not a["language"]:
            a["language"] = module.__language__
        _add_to_registry(a, skip_language_check=skip_language_check)
    del _potential_annotators[module_name]


def wizard(config_keys: list[str], source_structure: bool = False) -> Callable:
    """Decorate a function to register it as a wizard.

    A wizard is a function that is used to generate questions for the corpus config wizard.

    Note:
        The wizard functionality is deprecated and will be removed in a future version of Sparv.

    Args:
        config_keys: A list of config keys to be set or changed by the decorated function.
        source_structure: Set to `True` if the decorated function needs access to a `SourceStructureParser` instance
          (holding information on the structure of the source files).
    """  # noqa: DOC201

    def decorator(f: Callable) -> Callable:
        """Add wrapped function to wizard registry.

        Args:
            f: The function to add to the wizard registry.

        Returns:
            The function.
        """
        wizards.append((f, tuple(config_keys), source_structure))
        return f

    return decorator


def _get_module_name(module_string: str) -> str:
    """Extract module name from dotted path, i.e. 'modulename.submodule' -> 'modulename'.

    Args:
        module_string: Dotted path to module.

    Returns:
        The module name.
    """
    if module_string.startswith(modules_path):
        # Built-in Sparv module
        module_name = module_string[len(modules_path) + 1 :].split(".", maxsplit=1)[0]
    elif module_string.startswith(core_modules_path):
        # Built-in Sparv core module
        module_name = module_string[len(core_modules_path) + 1 :].split(".", maxsplit=1)[0]
    elif module_string.split(".", maxsplit=1)[0] == custom_name:
        # Custom user module
        module_name = module_string
    else:
        # External plugin
        module_name = module_string.split(".", maxsplit=1)[0]
    return module_name


def _annotator(
    description: str,
    a_type: Annotator,
    name: str | None = None,
    file_extension: str | None = None,
    outputs: list[str | Config] | Config | None = None,
    text_annotation: str | None = None,
    structure: type[SourceStructureParser] | None = None,
    language: list[str] | None = None,
    config: list[Config] | None = None,
    priority: int | None = None,
    order: int | None = None,
    abstract: bool = False,
    wildcards: list[Wildcard] | None = None,
    preloader: Callable | None = None,
    preloader_params: list[str] | None = None,
    preloader_target: str | None = None,
    preloader_cleanup: Callable | None = None,
    preloader_shared: bool = True,
    uninstaller: str | None = None,
) -> Callable:
    """Return a decorator for annotator functions, adding them to annotator registry.

    Args:
        description: Description of annotator.
        a_type: Type of annotator.
        name: Optional name to use instead of the function name.
        file_extension: (importer) The file extension of the type of source this importer handles, e.g. "xml" or
            "txt".
        outputs: (importer) A list of annotations and attributes that the importer is guaranteed to generate.
            The list may also contain one or more Config instances referring to such lists. Alternatively, 'outputs'
            may refer to a single Config instance referring to such a list.
            It may generate more outputs than listed, but only the annotations listed here will be available
            to use as input for annotator functions.
        text_annotation: (importer) An annotation from 'outputs' that should be used as the value for the
            import.text_annotation config variable, unless it or classes.text has been set manually.
        structure: (importer) A class used to parse and return the structure of source files.
        language: List of supported languages.
        config: List of Config instances defining config options for the annotator.
        priority: Functions with higher priority (higher number) will be preferred when scheduling which functions to
            run. The default priority is 0.
        order: If several annotators have the same output, this integer value will help decide which to try to use
            first. A lower number indicates higher priority.
        abstract: (exporter) Set to True if this exporter has no output.
        wildcards: List of wildcards used in the annotator function's arguments.
        preloader: Reference to a preloader function, used to preload models or processes.
        preloader_params: List of names of parameters for the annotator, which will be used as arguments for the
            preloader.
        preloader_target: The name of the annotator parameter which should receive the return value of the preloader.
        preloader_cleanup: Reference to an optional cleanup function, which will be executed after each annotator use.
        preloader_shared: Set to False if the preloader result should not be shared among preloader processes.
        uninstaller: (installer) Name of related uninstaller.

    Returns:
        A decorator adding the wrapped function to the annotator registry.
    """

    def decorator(f: Callable) -> Callable:
        """Add wrapped function to registry.

        Args:
            f: The function to add to the registry.

        Returns:
            The function.
        """
        module_name = _get_module_name(f.__module__)
        _potential_annotators[module_name].append(
            {
                "module_name": module_name,
                "description": description,
                "function": f,
                "name": name,
                "type": a_type,
                "file_extension": file_extension,
                "outputs": outputs,
                "text_annotation": text_annotation,
                "structure": structure,
                "language": language,
                "config": config,
                "priority": priority,
                "order": order,
                "abstract": abstract,
                "wildcards": wildcards,
                "preloader": preloader,
                "preloader_params": preloader_params,
                "preloader_target": preloader_target,
                "preloader_cleanup": preloader_cleanup,
                "preloader_shared": preloader_shared,
                "uninstaller": uninstaller,
            }
        )
        return f

    return decorator


def annotator(
    description: str,
    name: str | None = None,
    language: list[str] | None = None,
    config: list[Config] | None = None,
    priority: int | None = None,
    order: int | None = None,
    wildcards: list[Wildcard] | None = None,
    preloader: Callable | None = None,
    preloader_params: list[str] | None = None,
    preloader_target: str | None = None,
    preloader_cleanup: Callable | None = None,
    preloader_shared: bool = True,
) -> Callable:
    """Decorate a function to register it as an annotator.

    An annotator is a function that processes input data and generates new annotations.

    Args:
        description: A description of the annotator, used for displaying help texts in the CLI. The first line should be
            a short summary of what the annotator does. Optionally, a longer description can be added below the first
            line, separated by a blank line.
        name: Optional name to use instead of the function name.
        language: A list of supported languages. If no list is provided, all languages are supported.
        config: A list of `Config` instances defining configuration parameters for the annotator.
        priority: Functions with higher priority (higher number) will be preferred when scheduling which functions to
            run. The default priority is 0.
        order: If multiple annotators produce the same output, this integer value helps determine which to try to use
            first. A lower number indicates higher priority.
        wildcards: A list of wildcards used in the annotator function's arguments.
        preloader: A reference to a preloader function, used to preload models or processes.
        preloader_params: A list of names of parameters for the annotator, which will be used as arguments for the
            preloader.
        preloader_target: The name of the annotator parameter that should receive the return value of the preloader.
        preloader_cleanup: A reference to an optional cleanup function, which will be executed after each annotator use.
        preloader_shared: Set to `False` if the preloader result should not be shared among preloader processes.
    """  # noqa: DOC201 - Don't document the return value, to prevent it from being included in the documentation.
    return _annotator(
        description=description,
        a_type=Annotator.annotator,
        name=name,
        language=language,
        config=config,
        priority=priority,
        order=order,
        wildcards=wildcards,
        preloader=preloader,
        preloader_params=preloader_params,
        preloader_target=preloader_target,
        preloader_cleanup=preloader_cleanup,
        preloader_shared=preloader_shared,
    )


def importer(
    description: str,
    file_extension: str,
    name: str | None = None,
    outputs: list[str | Config] | Config | None = None,
    text_annotation: str | None = None,
    structure: type[SourceStructureParser] | None = None,
    config: list[Config] | None = None,
) -> Callable:
    """Decorate a function to register it as an importer.

    An importer is a function that is responsible for importing corpus files of a specific file format. Its task is to
    read a corpus file, extract the corpus text and any existing markup (if applicable), and write annotation files for
    the corpus text and markup.

    Importers do not use the `Output` class to specify their outputs. Instead, outputs are listed using the `outputs`
    argument of the decorator. Any output that needs to be used as explicit input by another part of the pipeline must
    be listed here, although additional unlisted outputs may also be created.

    Two outputs are implicit (and thus not listed in `outputs`) but required for every importer: the corpus text, saved
    using the `Text` class, and a list of the annotations created from existing markup, saved using the
    `SourceStructure` class.

    Args:
        description: A description of the importer, used for displaying help texts in the CLI. The first line should be
            a short summary of what the importer does. Optionally, a longer description can be added below the first
            line, separated by a blank line.
        file_extension: The file extension of the type of source this importer handles, e.g. "xml" or "txt".
        name: An optional name to use instead of the function name.
        outputs: A list specifying the annotations and attributes that the importer is guaranteed to generate. This list
            can include annotation names directly, or one or more `Config` instances that refer to such lists or single
            annotations. Alternatively, `outputs` can point to a single `Config` instance that refers to such a list.
        text_annotation: An annotation from 'outputs' that should be used as the value for the
            import.text_annotation config variable, unless it or classes.text has been set manually.
        structure: A class used to parse and return the structure of source files.
        config: A list of `Config` instances defining config parameters for the importer.
    """  # noqa: DOC201
    return _annotator(
        description=description,
        a_type=Annotator.importer,
        name=name,
        file_extension=file_extension,
        outputs=outputs,
        text_annotation=text_annotation,
        structure=structure,
        config=config,
    )


def exporter(
    description: str,
    name: str | None = None,
    config: list[Config] | None = None,
    language: list[str] | None = None,
    priority: int | None = None,
    order: int | None = None,
    abstract: bool = False,
) -> Callable:
    """Decorate a function to register it as an exporter.

    An exporter is a function that is responsible for generating final outputs, in Sparv referred to as *exports*.
    These outputs typically combine information from multiple annotations into a single file. The output produced by an
    exporter is generally not used as input for any other module. An export can consist of any kind of data, such as a
    frequency list, XML files, or a database dump. It can create one file per source file, combine information from all
    source files into a single output file, or follow any other structure as needed.

    Args:
        description: A description of the exporter, used for displaying help texts in the CLI. The first line should be
            a short summary of what the exporter does. Optionally, a longer description can be added below the first
            line, separated by a blank line.
        name: An optional name to use instead of the function name.
        config: A list of `Config` instances defining config parameters for the exporter.
        language: A list of supported languages. If no list is provided, all languages are supported.
        priority: Functions with higher priority (higher number) will be preferred when scheduling which functions to
            run. The default priority is 0.
        order: If several exporters produce the same output, this integer value will help decide which to try to use
            first. A lower number indicates higher priority.
        abstract: Set to `True` if this exporter does not produce any output files itself, but instead triggers other
            processors to produce their output files by using their output as input.
    """  # noqa: DOC201
    return _annotator(
        description=description,
        a_type=Annotator.exporter,
        name=name,
        config=config,
        language=language,
        priority=priority,
        order=order,
        abstract=abstract,
    )


def installer(
    description: str,
    name: str | None = None,
    config: list[Config] | None = None,
    language: list[str] | None = None,
    priority: int | None = None,
    uninstaller: str | None = None,
) -> Callable:
    """Decorate a function to register it as an installer.

    An installer is a function that is responsible for deploying the corpus or related files to a remote location. For
    example, it can copy XML output to a web server or insert SQL data into a database.

    Every installer must create a marker of the type `OutputMarker` at the end of a successful installation. Simply call
    the `write()` method on the marker to create the required marker.

    It is recommended that an installer removes any related uninstaller's marker to enable uninstallation. Use the
    `MarkerOptional` class to refer to the uninstaller's marker without triggering an unnecessary installation.

    Args:
        description: A description of the installer, used for displaying help texts in the CLI. The first line should be
            a short summary of what the installer does. Optionally, a longer description can be added below the first
            line, separated by a blank line.
        name: An optional name to use instead of the function name.
        config: A list of `Config` instances defining config parameters for the installer.
        language: A list of supported languages. If no list is provided, all languages are supported.
        priority: Functions with higher priority (higher number) will be preferred when scheduling which functions to
            run. The default priority is 0.
        uninstaller: The name of the related uninstaller.
    """  # noqa: DOC201
    return _annotator(
        description=description,
        a_type=Annotator.installer,
        name=name,
        config=config,
        language=language,
        priority=priority,
        uninstaller=uninstaller,
    )


def uninstaller(
    description: str,
    name: str | None = None,
    config: list[Config] | None = None,
    language: list[str] | None = None,
    priority: int | None = None,
) -> Callable:
    """Decorate a function to register it as an uninstaller.

    An uninstaller is a function that undoes the actions performed by an installer, such as removing corpus files from a
    remote location or deleting corpus data from a database.

    Every uninstaller must create a marker of the type `OutputMarker` at the end of a successful uninstallation. Simply
    call the `write()` method on the marker to create the required marker.

    It is recommended that an uninstaller removes any related installer's marker to enable re-installation. Use the
    `MarkerOptional` class to refer to the installer's marker without triggering an unnecessary installation.

    Args:
        description: A description of the uninstaller, used for displaying help texts in the CLI. The first line should
            be a short summary of what the uninstaller does. Optionally, a longer description can be added below the
            first line, separated by a blank line.
        name: An optional name to use instead of the function name.
        config: A list of `Config` instances defining config parameters for the uninstaller.
        language: A list of supported languages. If no list is provided, all languages are supported.
        priority: Functions with higher priority (higher number) will be preferred when scheduling which functions to
            run. The default priority is 0.
    """  # noqa: DOC201
    return _annotator(
        description=description,
        a_type=Annotator.uninstaller,
        name=name,
        config=config,
        language=language,
        priority=priority,
    )


def modelbuilder(
    description: str,
    name: str | None = None,
    config: list[Config] | None = None,
    language: list[str] | None = None,
    priority: int | None = None,
    order: int | None = None,
) -> Callable:
    """Decorate a function to register it as a model builder.

    A model builder is a function that sets up one or more models that other Sparv processors (typically annotators)
    rely on. Setting up a model might involve tasks such as downloading a file, unzipping it, converting it to a
    different format, and saving it in Sparv's data directory. Models are generally not specific to a single corpus;
    once a model is set up on your system, it will be available for any corpus.

    Args:
        description: A description of the model builder, used for displaying help texts in the CLI. The first line
            should be a short summary of what the model builder does. Optionally, a longer description can be added
            below the first line, separated by a blank line.
        name: An optional name to use instead of the function name.
        config: A list of `Config` instances defining config parameters for the model builder.
        language: A list of supported languages. If no list is provided, all languages are supported.
        priority: Functions with higher priority (higher number) will be preferred when scheduling which functions to
            run. The default priority is 0.
        order: If several model builders have the same output, this integer value will help decide which to try to use
            first. A lower number indicates higher priority.
    """  # noqa: DOC201
    return _annotator(
        description=description,
        a_type=Annotator.modelbuilder,
        name=name,
        config=config,
        language=language,
        priority=priority,
        order=order,
    )


def _add_to_registry(annotator: dict, skip_language_check: bool = False) -> None:
    """Add function to annotator registry. Used by annotator.

    Args:
        annotator: Annotator data.
        skip_language_check: Set to True to skip checking of language compatibility.

    Raises:
        SparvErrorMessage: On any expected errors.
    """
    module_name = annotator["module_name"]
    f_name = annotator["name"] or annotator["function"].__name__
    rule_name = f"{module_name}:{f_name}"

    if not skip_language_check and annotator["language"]:
        # Add to set of supported languages...
        for lang in annotator["language"]:
            languages.add_language(lang)
        # ... but skip annotators for other languages than the one specified in the config
        if not check_language(
            sparv_config.get("metadata.language"), annotator["language"], sparv_config.get("metadata.variety")
        ):
            return

    # Add config variables to config
    if annotator["config"]:
        for c in annotator["config"]:
            handle_config(c, module_name, rule_name, annotator["language"])

    # Handle default text annotation for the selected importer if it's not set manually in the config
    if (
        annotator["type"] == Annotator.importer
        and rule_name == sparv_config.get("import.importer")
        and annotator["text_annotation"]
        and not sparv_config.get("classes.text")
    ):
        sparv_config.set_value("import.text_annotation", annotator["text_annotation"])
        sparv_config.handle_text_annotation()

    has_marker = False  # Needed by installers and uninstallers

    # Convert type hints from strings to actual types (needed because of __future__.annotations)
    signature = inspect.signature(annotator["function"], eval_str=True)
    annotator["function"].__annotations__ = {
        **{param.name: param.annotation for param in signature.parameters.values()},
        "return": signature.return_annotation,
    }

    for val in inspect.signature(annotator["function"]).parameters.values():
        if isinstance(val.default, BaseOutput):
            if not has_marker and val.annotation == OutputMarker:
                has_marker = True
            ann = val.default
            cls = val.default.cls
            ann_name, attr = ann.split()

            # Data annotations may not contain ':' in the name
            if ann.data and ":" in ann.name:
                raise SparvErrorMessage(
                    f"Output annotation '{ann}' in module '{module_name}' cannot contain ':' in the name, since it is "
                    "a data annotation."
                )

            # Make sure annotation names include module names as prefix
            if not attr:
                if not ann_name.startswith(f"{module_name}."):
                    raise SparvErrorMessage(
                        f"Output annotation '{ann_name}' in module '{module_name}' doesn't include "
                        "module name as prefix."
                    )
            elif not attr.startswith(f"{module_name}."):
                raise SparvErrorMessage(
                    f"Output annotation '{ann}' in module '{module_name}' doesn't include "
                    "module name as prefix in attribute."
                )

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
                    console.print(f"Malformed class name: '{cls}'")

                if cls_target:
                    if not annotator["language"]:
                        if cls_target not in all_module_classes[None][cls]:
                            all_module_classes[None][cls].append(cls_target)
                    else:
                        for language in annotator["language"]:
                            if cls_target not in all_module_classes[language][cls]:
                                all_module_classes[language][cls].append(cls_target)

                    # Only add classes for relevant languages
                    if (
                        check_language(
                            sparv_config.get("metadata.language"),
                            annotator["language"],
                            sparv_config.get("metadata.variety"),
                        )
                        and cls_target not in annotation_classes["module_classes"][cls]
                    ):
                        annotation_classes["module_classes"][cls].append(cls_target)

        elif isinstance(val.default, ModelOutput):
            modeldir = val.default.name.split("/")[0]
            if not modeldir.startswith(module_name):
                raise SparvErrorMessage(
                    f"Output model '{val.default}' in module '{module_name}' doesn't include module"
                    " name as sub directory."
                )
        elif isinstance(val.default, Config):
            sparv_config.add_config_usage(val.default.name, rule_name)
        elif isinstance(val.default, (ExportAnnotations, ExportAnnotationsAllSourceFiles, SourceAnnotations)):
            sparv_config.add_config_usage(val.default.config_name, rule_name)
            annotation_sources.add(val.default.config_name)
        elif isinstance(val.default, Export):
            if "/" not in val.default:
                raise SparvErrorMessage(
                    f"Illegal export path for export '{val.default}' in module '{module_name}'. "
                    "A subdirectory must be used."
                )
            export_dir = val.default.split("/")[0]
            if not (export_dir.startswith(f"{module_name}.") or export_dir == module_name):
                raise SparvErrorMessage(
                    f"Illegal export path for export '{val.default}' in module '{module_name}'. "
                    "The export subdirectory must include the module name as prefix."
                )

    if annotator["type"] in {Annotator.installer, Annotator.uninstaller} and not has_marker:
        raise SparvErrorMessage(
            f"'{rule_name}' creates no OutputMarker, which is required by all installers and uninstallers."
        )

    if f_name in modules[module_name].functions:
        console.print(
            f"Annotator function '{f_name}' collides with other function with same name in module '{module_name}'."
        )
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
                anns = [anns]  # noqa: PLW2901
            for ann in anns:
                annotation_to_class[ann].add(cls)
                annotation_to_class[expand_variables(ann)[0]].add(cls)

    for annotation in explicit_annotations_raw:
        for cls in annotation_to_class[annotation]:
            if cls not in annotation_classes["config_classes"] and cls not in annotation_classes["implicit_classes"]:
                annotation_classes["implicit_classes"][cls] = annotation


def handle_config(
    cfg: Config, module_name: str, rule_name: str | None = None, language: list[str] | None = None
) -> None:
    """Handle Config instances, either from a module's __config__ attribute or from a processor decorator.

    Args:
        cfg: The Config instance.
        module_name: The name of the module.
        rule_name: The name of the rule using the config variable.
        language: List of supported languages.

    Raises:
        SparvErrorMessage: If the config variable doesn't include the module name as prefix, or if the config variable
            has already been declared, or if the config variable is missing a description.
    """
    if not cfg.name.startswith(f"{module_name}."):
        raise SparvErrorMessage(
            f"Config option '{cfg.name}' in module '{module_name}' doesn't include module name as prefix."
        )
    # Check that config variable hasn't already been declared
    prev = sparv_config.config_structure
    for k in cfg.name.split("."):
        if k not in prev:
            break
        prev = prev[k]
    else:
        raise SparvErrorMessage(
            f"The config variable '{cfg.name}' in '{rule_name or module_name}' has already been declared."
        )
    if cfg.default is not None:
        sparv_config.set_default(cfg.name, cfg.default)
    if language:
        langcodes = []
        suffixes = []
        for lang in language:
            langcode, _, suffix = lang.partition("-")
            langcodes.append(langcode)
            suffixes.append(suffix)
        suffixes = set(suffixes)
        if len(suffixes) == 1 and not next(iter(suffixes)):
            suffixes = []
        cfg.conditions.append(Config("metadata.language", datatype=str, choices=langcodes))
        if suffixes:
            cfg.conditions.append(Config("metadata.variety", datatype=str, choices=suffixes))
    sparv_config.add_to_structure(cfg, annotator=rule_name)
    if not cfg.description:
        raise SparvErrorMessage(f"Missing description for configuration key '{cfg.name}' in module '{module_name}'.")


def _expand_class(cls: str) -> str | None:
    """Convert class name to annotation name.

    Classes from config takes precedence over classes automatically collected from modules.

    Args:
        cls: The class name.

    Returns:
        The annotation name, or None if the class is not found.
    """
    annotation = None
    if cls in annotation_classes["config_classes"]:
        annotation = annotation_classes["config_classes"][cls]
    elif cls in annotation_classes["implicit_classes"]:
        annotation = annotation_classes["implicit_classes"][cls]
    elif cls in annotation_classes["module_classes"]:
        annotation = annotation_classes["module_classes"][cls][0]
    return annotation


def find_config_variables(string: str, match_objects: bool = False) -> list[str] | list[re.Match]:
    """Find all config variables in a string and return a list of strings or match objects.

    Args:
        string: The string to process.
        match_objects: Set to True to return match objects instead of strings.

    Returns:
        A list of strings or match objects.
    """
    pattern = re.finditer(r"\[([^\]=[]+)(?:=([^\][]+))?\]", string)
    return list(pattern) if match_objects else [c.group()[1:-1] for c in pattern]


def find_classes(string: str, match_objects: bool = False) -> list[str] | list[re.Match]:
    """Find all class references in a string and return a list of strings or match objects.

    Args:
        string: The string to process.
        match_objects: Set to True to return match objects instead of strings.

    Returns:
        A list of strings or match objects.
    """
    pattern = re.finditer(r"<([^>]+)>", string)
    return list(pattern) if match_objects else [c.group(1) for c in pattern]


def expand_variables(string: str, rule_name: str | None = None, is_annotation: bool = False) -> tuple[str, list[str]]:
    """Take a string and replace [config] references with config values, and <class> references with real annotations.

    Config references are replaced before classes.

    Args:
        string: The string to process.
        rule_name: Name of rule using the string, for logging config usage.
        is_annotation: Set to True if string refers to an annotation.

    Returns:
        The resulting string and a list of any unresolved config references.
    """
    rest = []

    # Split if list of alternatives
    strings = string.split(", ") if is_annotation else [string]

    for i, s in enumerate(strings):
        # Convert config keys to config values
        while True:
            cfgs = find_config_variables(s, True)
            if not cfgs:
                break
            for cfg in cfgs:
                cfg_value = sparv_config.get(cfg.group(1), cfg.group(2))
                if rule_name:
                    sparv_config.add_config_usage(cfg.group(1), rule_name)
                if cfg_value is not None:
                    s = s.replace(cfg.group(), cfg_value)  # noqa: PLW2901
                else:
                    rest.append(cfg.group()[1:-1])
                    break
            else:
                # No break occurred, continue outer loop
                continue
            break

        strings[i] = s

    if is_annotation:
        # Split if list of alternatives (again, since config variables may have been expanded into lists)
        strings = [s2 for s in strings for s2 in s.split(", ")]

    def expand_classes(s: str, parents: set[str]) -> tuple[str | None, str | None]:
        classes = find_classes(s, True)
        if not classes:
            return s, None
        for cls in classes:
            # Check that cls isn't among its parents
            if cls.group(1) in parents:
                raise SparvErrorMessage(
                    f"The class {cls.group()} refers to itself, either directly or indirectly, leading to an infinite "
                    "loop. Check your class definitions in your config file under the 'classes' section. Also check "
                    "'import.text_annotation', which automatically sets the <text> class."
                )
            real_ann = _expand_class(cls.group(1))
            if real_ann:
                final_ann, rest_ = expand_classes(real_ann, parents.union([cls.group(1)]))
                s = s.replace(cls.group(), final_ann, 1)
                if rest_:
                    return s, rest_
            else:
                return s, cls.group()
        return s, None

    for s in strings:
        # Convert class names to real annotations
        s, unknown = expand_classes(s, set())  # noqa: PLW2901
        if unknown:
            rest.append(unknown)

        # If multiple alternative annotations, return the first one that is explicitly used as an export annotation,
        # or referred to by a class in the config. As a fallback use the last annotation.
        if (
            is_annotation
            and len(s) > 1
            and (s in explicit_annotations or s in annotation_classes["config_classes"].values())
        ):
            break

    return s, rest


def get_type_hint_type(type_hint: Any) -> tuple[type, bool, bool]:
    """Given a type hint, return the type, whether it's contained in a List and whether it's Optional.

    Args:
        type_hint: The type hint.

    Returns:
        A tuple with the type, a boolean indicating whether it's a list and a boolean indicating whether it's optional.
    """
    optional = typing_inspect.is_optional_type(type_hint)
    if optional:
        type_hint = typing_inspect.get_args(type_hint)[0]
    origin = typing_inspect.get_origin(type_hint)

    is_list = False

    if origin in {list, List, tuple, Tuple, Container, Iterable, TypingIterable}:  # noqa: UP006
        is_list = True
        args = typing_inspect.get_args(type_hint)
        type_ = args[0] if args and type(args[0]) is not TypeVar else origin
    else:
        type_ = type_hint

    return type_, is_list, optional


def check_language(corpus_lang: str, langs: list[str], corpus_lang_suffix: str | None = None) -> bool:
    """Check if corpus language is among a list of languages.

    Any suffix on corpus_lang will be ignored.

    If langs is empty, always return True.
    If corpus_lang is "__all__", always return True.

    Args:
        corpus_lang: The language of the corpus.
        langs: A list of languages to check against.
        corpus_lang_suffix: Optional suffix for the corpus language.

    Returns:
        True if the corpus language is among the languages, otherwise False.
    """
    if not langs or corpus_lang == "__all__":
        return True

    if not isinstance(corpus_lang, str):
        return False

    if corpus_lang_suffix:
        corpus_lang = f"{corpus_lang}-{corpus_lang_suffix}"

    return corpus_lang in langs or corpus_lang.split("-")[0] in langs
