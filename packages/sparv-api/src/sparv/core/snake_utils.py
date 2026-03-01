"""Util functions for Snakefile."""

from __future__ import annotations

import copy
import inspect
import re
from collections import OrderedDict, defaultdict
from collections.abc import Callable
from itertools import combinations
from pathlib import Path
from typing import Any

import snakemake
from snakemake.io import expand

from sparv.api import SparvErrorMessage, util
from sparv.api.classes import (
    AllSourceFilenames,
    Annotation,
    AnnotationAllSourceFiles,
    AnnotationData,
    Base,
    BaseAnnotation,
    BaseOutput,
    Binary,
    BinaryDir,
    Config,
    Corpus,
    Export,
    ExportAnnotationNames,
    ExportAnnotations,
    ExportAnnotationsAllSourceFiles,
    ExportInput,
    HeaderAnnotations,
    HeaderAnnotationsAllSourceFiles,
    Language,
    Model,
    ModelOutput,
    Output,
    OutputData,
    Source,
    SourceAnnotations,
    SourceAnnotationsAllSourceFiles,
    SourceFilename,
    Text,
)
from sparv.core import config as sparv_config
from sparv.core import io, log_handler, registry
from sparv.core.console import console
from sparv.core.paths import paths


class SnakeStorage:
    """Object to store variables involving all rules."""

    def __init__(self) -> None:
        """Initialize attributes."""
        # All annotators, importers, exporters and installers available, used for CLI listings
        self.all_annotators = {}
        self.all_importers = {}
        self.all_exporters = {}
        self.all_installers = {}
        self.all_uninstallers = {}
        self.all_custom_annotators = {}
        self.all_preloaders = {}

        # All named targets available, used in list_targets
        self.named_targets = []
        self.export_targets = []
        self.import_targets = []
        self.install_targets = []
        self.uninstall_targets = []
        self.model_targets = []
        self.custom_targets = []

        self.model_outputs = []  # Outputs from modelbuilders, used in build_models
        self.install_outputs = defaultdict(list)  # Outputs from all installers, used in rule install_corpus
        self.uninstall_outputs = defaultdict(list)  # Outputs from all uninstallers, used in rule uninstall_corpus
        self.all_rules: list[RuleStorage] = []  # List containing all rules created
        self.ordered_rules = []  # List of rules containing rule order
        self.preloader_info = {}

        self._source_files = None  # Auxiliary variable for the source_files property

    @property
    def source_files(self) -> list[str]:
        """Return list of all available source files.

        Raises:
            SparvErrorMessage: If the importer setting is empty or if the importer is not found.
        """
        if self._source_files is None:
            # Helper function to get available importers
            def get_available_importers() -> str:
                """Return a formatted list of all available importers."""
                importers = []
                maxlen = 0
                for mod_name, mod in registry.modules.items():
                    for func_name, func_info in mod.functions.items():
                        if func_info["type"] is registry.Annotator.importer:
                            name = f"{mod_name}:{func_name}"
                            maxlen = max(maxlen, len(name))
                            importers.append((name, func_info["description"]))
                return " • " + "\n • ".join(
                    f"{name:<{maxlen}}   {desc}" for name, desc in sorted(importers)
                )

            if not sparv_config.get("import.importer"):
                msg = "The config variable 'import.importer' is not set."
                if available_importers := get_available_importers():
                    msg += f"\n\nAvailable importers:\n\n{available_importers}"
                msg += "\n\nPlease edit your corpus configuration file to set this value."
                raise SparvErrorMessage(msg, "sparv")

            try:
                importer_module, _, importer_function = sparv_config.get("import.importer").partition(":")
                file_extension = "." + registry.modules[importer_module].functions[importer_function]["file_extension"]
            except KeyError:
                importer_name = sparv_config.get("import.importer")
                msg = (
                    f"Could not find the importer '{importer_name}'. Make sure the "
                    "'import.importer' config value refers to an existing importer."
                )
                if available_importers := get_available_importers():
                    msg += f"\n\nAvailable importers:\n\n{available_importers}"
                raise SparvErrorMessage(msg, "sparv") from None

            # Collect files in source dir
            sf = list(snakemake.utils.listfiles(str(Path(get_source_path(), "{file}"))))
            self._source_files = [f[1][0][: -len(file_extension)] for f in sf if f[1][0].endswith(file_extension)]
            # Collect files that don't match the file extension provided by the corpus config
            wrong_ext = [f[1][0] for f in sf if not f[1][0].endswith(file_extension) and not Path(f[0]).is_dir()]
            if wrong_ext:
                console.print(
                    "[yellow]\nThere {} file{} in your source directory that do{} not match the file "
                    "extension '{}' in the corpus config: {}{} will not be processed.\n[/yellow]".format(
                        "is one" if len(wrong_ext) == 1 else "are",
                        "" if len(wrong_ext) == 1 else "s",
                        "es" if len(wrong_ext) == 1 else "",
                        file_extension,
                        f"'{wrong_ext[0]}'" if len(wrong_ext) == 1 else "\n  • " + "\n  • ".join(wrong_ext),
                        ". This file" if len(wrong_ext) == 1 else "\nThese files",
                    ),
                    highlight=False,
                )
        return self._source_files


class RuleStorage:
    """Object to store parameters for a Snakemake rule."""

    def __init__(self, module_name: str, f_name: str, annotator_info: dict) -> None:
        """Initialize attributes."""
        self.module_name = module_name
        self.f_name = f_name
        self.annotator_info = annotator_info
        self.target_name = f"{module_name}:{f_name}"  # Rule name for the "all-files-rule" based on this rule
        self.rule_name = f"{module_name}::{f_name}"  # Actual Snakemake rule name for internal use
        self.full_name = f"{module_name}:{f_name}"  # Used in messages to the user
        self.inputs: list[Path] = []
        self.outputs: list[Path] = []
        self.parameters = {}
        self.file_parameters = []  # List of parameters referring to SourceFilename
        self.file_annotations = []  # List of parameters containing the {file} wildcard
        self.wildcard_annotations = []  # List of parameters containing other wildcards
        self.configs = set()  # Set of config variables used
        self.classes = set()  # Set of classes used
        self.missing_config: set[str] = set()
        self.missing_binaries = set()
        self.export_dirs: list[str] | None = None
        self.has_preloader = bool(annotator_info["preloader"])
        self.use_preloader = False

        self.type: str = annotator_info["type"].name
        self.annotator: bool = annotator_info["type"] is registry.Annotator.annotator
        self.importer: bool = annotator_info["type"] is registry.Annotator.importer
        self.exporter: bool = annotator_info["type"] is registry.Annotator.exporter
        self.installer: bool = annotator_info["type"] is registry.Annotator.installer
        self.uninstaller: bool = annotator_info["type"] is registry.Annotator.uninstaller
        self.modelbuilder: bool = annotator_info["type"] is registry.Annotator.modelbuilder
        self.description: str = annotator_info["description"]
        self.file_extension: str | None = annotator_info["file_extension"]
        self.import_outputs = annotator_info["outputs"]
        self.priority: int = annotator_info["priority"] or 0
        self.order = annotator_info["order"]
        self.abstract = annotator_info["abstract"]
        self.wildcards = annotator_info["wildcards"]  # Information about the wildcards used


def rule_helper(
    rule: RuleStorage,
    config: dict,
    storage: SnakeStorage,
    config_missing: bool = False,
    custom_rule_obj: dict | None = None,
) -> bool:
    """Populate rule with Snakemake input, output, and parameter lists.

    Returns True if a Snakemake rule should be created.

    Args:
        rule: Object containing Snakemake rule parameters.
        config: Dictionary containing the corpus configuration.
        storage: Object for saving information for all rules.
        config_missing: True if there is no corpus config file.
        custom_rule_obj: Custom annotation dictionary from the corpus config.

    Returns:
        True if a Snakemake rule should be created, otherwise False.

    Raises:
        SparvErrorMessage: On various errors.
    """
    # Only create certain rules when config is missing
    if config_missing and not rule.modelbuilder:
        return False

    # Skip any annotator that is not available for the selected corpus language
    if not registry.check_language(
        sparv_config.get("metadata.language"), rule.annotator_info["language"], sparv_config.get("metadata.variety")
    ):
        return False

    # Get this function's parameters
    params = OrderedDict(inspect.signature(rule.annotator_info["function"]).parameters)
    param_dict = make_param_dict(params)

    if rule.importer:
        rule.inputs.append(Path(get_source_path(), "{file}." + rule.file_extension))
        storage.all_importers.setdefault(rule.module_name, {}).setdefault(
            rule.f_name, {"description": rule.description, "params": param_dict}
        )
        if rule.target_name == sparv_config.get("import.importer"):
            # Imports always generate corpus text file and structure file
            rule.outputs.append(paths.work_dir / "{file}" / io.TEXT_FILE)
            rule.outputs.append(paths.work_dir / "{file}" / io.STRUCTURE_FILE)
            # If importer guarantees other outputs, add them to outputs list
            if rule.import_outputs:
                # import_outputs is either a list of annotations and/or Config objects, or a single Config object
                import_outputs = rule.import_outputs
                if isinstance(import_outputs, Config):
                    import_outputs = sparv_config.get(import_outputs.name, import_outputs.default)
                    if isinstance(import_outputs, str):
                        import_outputs = [import_outputs]
                elif isinstance(import_outputs, str):
                    import_outputs = [import_outputs]
                elif isinstance(import_outputs, list):
                    expanded: list[str] = []
                    for item in import_outputs:
                        if isinstance(item, Config):
                            expanded_item = sparv_config.get(item.name, item.default)
                            if isinstance(expanded_item, list):
                                expanded.extend(expanded_item)
                            elif isinstance(expanded_item, str):
                                expanded.append(expanded_item)
                        elif isinstance(item, str):
                            expanded.append(item)
                    import_outputs = expanded
                rule.import_outputs = import_outputs
                annotations_ = set()
                renames = {}
                # Annotation list needs to be sorted to handle plain annotations before attributes
                for ann, target in sorted(util.misc.parse_annotation_list(rule.import_outputs)):
                    # Handle annotations renamed during import
                    if target:
                        source_ann, source_attr = BaseAnnotation(ann).split()
                        if BaseAnnotation(target).has_attribute():  # E.g. header annotations
                            ann = target  # noqa: PLW2901
                        elif not source_attr:
                            renames[ann] = target
                            ann = target  # noqa: PLW2901
                        else:
                            ann = io.join_annotation(renames.get(source_ann, source_ann), target)  # noqa: PLW2901
                    annotations_.add(ann)

                for element in annotations_:
                    rule.outputs.append(paths.work_dir / get_annotation_path(element))

            # If import.text_annotation has been specified, add it to outputs if not already there
            if sparv_config.get("import.text_annotation"):
                text_ann_file = paths.work_dir / get_annotation_path(sparv_config.get("import.text_annotation"))
                if text_ann_file not in rule.outputs:
                    rule.outputs.append(text_ann_file)

    if rule.exporter:
        storage.all_exporters.setdefault(rule.module_name, {}).setdefault(
            rule.f_name, {"description": rule.description, "params": param_dict}
        )
    elif rule.installer:
        storage.all_installers.setdefault(rule.module_name, {}).setdefault(
            rule.f_name, {"description": rule.description, "params": param_dict}
        )
    elif rule.uninstaller:
        storage.all_uninstallers.setdefault(rule.module_name, {}).setdefault(
            rule.f_name, {"description": rule.description, "params": param_dict}
        )

    if rule.has_preloader:
        storage.all_preloaders.setdefault(rule.module_name, {})[rule.f_name] = rule.annotator_info["preloader_params"]

    output_dirs = set()  # Directories where export files are stored
    custom_params = set()
    custom_suffix = None

    if custom_rule_obj:
        if custom_rule_obj.get("params"):
            # This should be either a utility annotator or a custom annotator supplied by the user
            if not (
                rule.module_name == registry.custom_name
                or storage.all_custom_annotators.get(rule.module_name, {}).get(rule.f_name)
            ):
                raise SparvErrorMessage(
                    "The custom annotation for annotator '{}' is using 'params' which is not allowed with this type of "
                    "annotator. Use 'config' instead.".format(custom_rule_obj["annotator"])
                )
            name_custom_rule(rule, storage)
            custom_params = set(custom_rule_obj.get("params").keys())
        elif custom_rule_obj.get("config"):
            # This is a regular annotator but with an alternative config
            name_custom_rule(rule, storage)
            try:
                custom_suffix = custom_rule_obj["suffix"]
            except KeyError:
                raise SparvErrorMessage(
                    f"The custom annotation for annotator '{custom_rule_obj['annotator']}' is missing the required "
                    "key 'suffix'."
                ) from None
            sparv_config._merge_dicts_replace(sparv_config.config, custom_rule_obj["config"])
        else:
            # This is a custom rule which doesn't require any parameters, so it has already been processed
            return False

    # Go through function parameters and handle based on type
    for param_name, param in params.items():
        param_default_empty = param.default == inspect.Parameter.empty
        param_value: Any

        # Get parameter value, either from custom rule object or default value
        if custom_rule_obj and "params" in custom_rule_obj:
            if param_name in custom_rule_obj["params"]:
                param_value = custom_rule_obj["params"][param_name]
                custom_params.remove(param_name)
            elif not param_default_empty:
                param_value = copy.deepcopy(param.default)
            else:
                raise SparvErrorMessage(
                    f"Parameter '{param_name}' in custom rule '{rule.full_name}' has no value!", "sparv", "config"
                )
        elif param_default_empty:
            # This is a custom annotator, either unused or it will be handled separately later.
            # Don't process it any further, but save it in all_custom_annotators and all_annotators.
            storage.all_custom_annotators.setdefault(rule.module_name, {}).setdefault(
                rule.f_name, {"description": rule.description, "params": param_dict}
            )
            storage.custom_targets.append((rule.target_name, rule.description))
            storage.all_annotators.setdefault(rule.module_name, {}).setdefault(
                rule.f_name, {"description": rule.description, "annotations": [], "params": param_dict}
            )
            return False
        else:
            param_value = copy.deepcopy(param.default)

        param_type, param_list, param_optional = registry.get_type_hint_type(param.annotation)

        # Config
        if isinstance(param_value, Config):
            rule.configs.add(param_value.name)
            config_value = sparv_config.get(param_value.name, sparv_config.Unset)
            if config_value is sparv_config.Unset:
                if param_value.default is not None:
                    config_value = param_value.default
                elif param_optional:
                    config_value = None
                else:
                    rule.missing_config.add(param_value.name)
            param_value = config_value

        # Output
        if isinstance(param_type, type) and issubclass(param_type, BaseOutput):
            if not isinstance(param_value, (list, tuple)):
                param_value = [param_value]
            skip = False
            outputs_list = []
            for output in param_value:
                if not isinstance(output, BaseOutput):
                    if not output:
                        return False
                    output = param_type(output)  # noqa: PLW2901
                elif (
                    rule.annotator
                    and not output.description
                    and not rule.module_name.startswith(f"{registry.custom_name}.")
                ):
                    console.print(
                        "[red]WARNING:[/] "
                        f"Annotation '{output.name}' created by {rule.type} '{rule.full_name}' is missing a "
                        "description."
                    )
                if custom_suffix:
                    # Add suffix to output annotation name
                    output.name += custom_suffix
                rule.configs.update(registry.find_config_variables(output.name))
                rule.classes.update(registry.find_classes(output.name))
                missing_configs = output.expand_variables(rule.full_name)
                if (not output or missing_configs) and param_optional:
                    rule.parameters[param_name] = None
                    skip = True
                    break
                rule.missing_config.update(missing_configs)
                ann_path = get_annotation_path(output, data=param_type.data, common=param_type.common)
                if param_type.all_files:
                    rule.outputs.extend(
                        map(Path, expand(escape_wildcards(paths.work_dir / ann_path), file=storage.source_files))
                    )
                elif param_type.common:
                    rule.outputs.append(paths.work_dir / ann_path)
                    if rule.installer:
                        storage.install_outputs[rule.target_name].append(paths.work_dir / ann_path)
                    elif rule.uninstaller:
                        storage.uninstall_outputs[rule.target_name].append(paths.work_dir / ann_path)
                else:
                    rule.outputs.append(get_annotation_path(output, data=param_type.data))
                if "{" in output:
                    rule.wildcard_annotations.append(param_name)
                outputs_list.append(output)
                if rule.annotator:
                    storage.all_annotators.setdefault(rule.module_name, {}).setdefault(
                        rule.f_name, {"description": rule.description, "annotations": [], "params": param_dict}
                    )
                    storage.all_annotators[rule.module_name][rule.f_name]["annotations"].append(
                        (output, output.description)
                    )
            if skip:
                continue
            rule.parameters[param_name] = outputs_list if param_list else outputs_list[0]
        # ModelOutput
        elif param_type == ModelOutput:
            rule.configs.update(registry.find_config_variables(param_value.name))
            rule.classes.update(registry.find_classes(param_value.name))
            rule.missing_config.update(param_value.expand_variables(rule.full_name))
            model_path = param_value.path
            rule.outputs.append(model_path)
            rule.parameters[param_name] = ModelOutput(str(model_path))
            storage.model_outputs.append(model_path)
        # Annotation
        elif isinstance(param_type, type) and issubclass(param_type, BaseAnnotation):
            if not isinstance(param_value, (list, tuple)):
                param_value = [param_value]
            skip = False
            annotations_list = []
            for annotation in param_value:
                if not isinstance(annotation, BaseAnnotation):
                    if not annotation:
                        if param_optional:
                            rule.parameters[param_name] = None
                            skip = True
                            break
                        return False
                    annotation = param_type(annotation)  # noqa: PLW2901
                rule.configs.update(registry.find_config_variables(annotation.name))
                rule.classes.update(registry.find_classes(annotation.name))
                missing_configs = annotation.expand_variables(rule.full_name)
                if (not annotation or missing_configs) and param_optional:
                    rule.parameters[param_name] = None
                    skip = True
                    break
                rule.missing_config.update(missing_configs)
                ann_path = get_annotation_path(annotation, data=param_type.data, common=param_type.common)
                if annotation.is_input:
                    if param_type.all_files:
                        rule.inputs.extend(
                            expand(escape_wildcards(paths.work_dir / ann_path), file=storage.source_files)
                        )
                    elif rule.exporter or rule.installer or rule.uninstaller or param_type.common:
                        rule.inputs.append(paths.work_dir / ann_path)
                    else:
                        rule.inputs.append(ann_path)
                if "{" in annotation:
                    rule.wildcard_annotations.append(param_name)
                annotations_list.append(annotation)
            if skip:
                continue
            rule.parameters[param_name] = annotations_list if param_list else annotations_list[0]
        # ExportAnnotations
        elif param_type in {ExportAnnotations, ExportAnnotationNames, ExportAnnotationsAllSourceFiles}:
            if not isinstance(param_value, param_type):
                param_value = param_type(param_value)

            source = param_value.config_name
            annotations = sparv_config.get(source, [])
            if not annotations:
                rule.missing_config.add(source)
            export_annotations = util.misc.parse_annotation_list(annotations, add_plain_annotations=False)
            annotation_type = (
                Annotation if param_type in {ExportAnnotations, ExportAnnotationNames} else AnnotationAllSourceFiles
            )
            plain_annotations = set()
            possible_plain_annotations = {}
            full_annotations = {}  # Using a dict for deduplication (parse_annotation_list's deduping isn't enough)
            for export_annotation_name, export_name in export_annotations:
                annotation = annotation_type(export_annotation_name)
                rule.configs.update(registry.find_config_variables(annotation.name))
                rule.classes.update(registry.find_classes(annotation.name))
                rule.missing_config.update(annotation.expand_variables(rule.full_name))
                full_annotations[annotation] = export_name
                plain_name, attr = annotation.split()
                if not attr:
                    plain_annotations.add(plain_name)
                else:
                    possible_plain_annotations[plain_name] = None
            # Add plain annotations where needed
            for a in possible_plain_annotations:
                if a not in plain_annotations:
                    full_annotations[annotation_type(a)] = None

            items = []

            for annotation, export_name in full_annotations.items():
                if param_value.is_input:
                    if param_type == ExportAnnotationsAllSourceFiles:
                        rule.inputs.extend(
                            expand(
                                escape_wildcards(paths.work_dir / get_annotation_path(annotation.name)),
                                file=storage.source_files,
                            )
                        )
                    else:
                        rule.inputs.append(paths.work_dir / get_annotation_path(annotation.name))
                items.append((annotation, export_name))
            param_value.items = items
            rule.parameters[param_name] = param_value
        # SourceAnnotations
        elif param_type in {SourceAnnotations, SourceAnnotationsAllSourceFiles}:
            if not isinstance(param_value, param_type):
                param_value = param_type(param_value)
            param_value: SourceAnnotations | SourceAnnotationsAllSourceFiles
            param_value.raw_list = sparv_config.get(param_value.config_name)
            rule.parameters[param_name] = param_value
            if param_type == SourceAnnotationsAllSourceFiles:
                rule.parameters[param_name].source_files = storage.source_files
                rule.inputs.extend(
                    expand(
                        escape_wildcards(paths.work_dir / get_annotation_path(io.STRUCTURE_FILE, data=True)),
                        file=storage.source_files,
                    )
                )
            else:
                rule.inputs.append(paths.work_dir / get_annotation_path(io.STRUCTURE_FILE, data=True))
        # HeaderAnnotations
        elif param_type in {HeaderAnnotations, HeaderAnnotationsAllSourceFiles}:
            if not isinstance(param_value, param_type):
                param_value = param_type(param_value)
            param_value.raw_list = sparv_config.get(param_value.config_name)
            rule.parameters[param_name] = param_value
            if param_type == HeaderAnnotationsAllSourceFiles:
                rule.parameters[param_name].source_files = storage.source_files
        # Corpus
        elif param_type == Corpus:
            rule.parameters[param_name] = Corpus(sparv_config.get("metadata.id"))
        # Language
        elif param_type == Language:
            rule.parameters[param_name] = Language(sparv_config.get("metadata.language"))
        # SourceFilename
        elif param_type == SourceFilename:
            rule.file_parameters.append(param_name)
        # AllSourceFilenames (all source filenames)
        elif param_type == AllSourceFilenames:
            param_value.items = storage.source_files
            rule.parameters[param_name] = param_value
        # Text
        elif param_type == Text:
            text_path = Path("{file}") / io.TEXT_FILE
            if rule.exporter or rule.installer or rule.uninstaller:
                rule.inputs.append(paths.work_dir / text_path)
            else:
                rule.inputs.append(text_path)
            rule.parameters[param_name] = param_value
        # Model
        elif param_type == Model:
            if param_value is not None:
                if not isinstance(param_value, (list, tuple)):
                    param_value = [param_value]
                model_param = []
                for model in param_value:
                    if not isinstance(model, Model):
                        model = Model(model)  # noqa: PLW2901
                    rule.configs.update(registry.find_config_variables(model.name))
                    rule.classes.update(registry.find_classes(model.name))
                    rule.missing_config.update(model.expand_variables(rule.full_name))
                    rule.inputs.append(model.path)
                    model_param.append(Model(str(model.path)))
                if param_list:
                    rule.parameters[param_name] = model_param
                else:
                    rule.parameters[param_name] = model_param[0]
        # Binary
        elif param_type in {Binary, BinaryDir}:
            rule.configs.update(registry.find_config_variables(param.default))
            rule.classes.update(registry.find_classes(param.default))
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            binary = util.system.find_binary(param_value, executable=False, allow_dir=param_type == BinaryDir)
            if not binary:
                rule.missing_binaries.add(param_value)
            binary = Path(binary or param_value)
            rule.inputs.append(binary)
            rule.parameters[param_name] = param_type(binary)
        # Source
        elif param_type == Source:
            rule.parameters[param_name] = Source(get_source_path())
        # Export
        elif param_type == Export:
            rule.configs.update(registry.find_config_variables(param.default))
            rule.classes.update(registry.find_classes(param.default))
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            export_path = paths.export_dir / param_value
            output_dirs.add(export_path.parent)
            rule.outputs.append(export_path)
            rule.parameters[param_name] = Export(str(export_path))
            if "{file}" in rule.parameters[param_name]:
                rule.file_annotations.append(param_name)
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
            if rule.exporter:
                storage.all_exporters[rule.module_name][rule.f_name].setdefault("exports", [])
                storage.all_exporters[rule.module_name][rule.f_name]["exports"].append(str(export_path))
        # ExportInput
        elif param_type == ExportInput:
            rule.configs.update(registry.find_config_variables(param.default))
            rule.classes.update(registry.find_classes(param.default))
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            rule.parameters[param_name] = ExportInput(paths.export_dir / param_value)
            if param.default.all_files:
                rule.inputs.extend(expand(escape_wildcards(rule.parameters[param_name]), file=storage.source_files))
            else:
                rule.inputs.append(Path(rule.parameters[param_name]))
            if "{" in rule.parameters[param_name]:
                rule.wildcard_annotations.append(param_name)
        # Everything else
        elif param_type == param.empty:
            print_sparv_warning(f"The parameter '{param_name}' in '{rule.full_name}' is missing a required type hint.")
            rule.parameters[param_name] = param_value
        else:
            rule.parameters[param_name] = param_value

    # For custom rules, warn the user of any unknown parameters
    if custom_params:
        print_sparv_warning(
            "The parameter{} '{}' used in one of your custom rules do{} not exist in {}.".format(
                "s" if len(custom_params) > 1 else "",
                "', '".join(custom_params),
                "es" if len(custom_params) == 1 else "",
                rule.full_name,
            )
        )

    storage.all_rules.append(rule)

    # Add to rule lists in storage
    update_storage(storage, rule)

    # Add exporter dirs (used for informing user)
    if rule.exporter:
        if rule.abstract:
            output_dirs = {p.parent for p in rule.inputs}
        rule.export_dirs = [str(p / "_")[:-1] for p in output_dirs]

    if rule.missing_config:
        missing_config = [c for c in rule.missing_config if not c.startswith("<")]
        if missing_config:
            log_handler.messages["missing_configs"][rule.full_name].update(missing_config)
        missing_classes = [c[1:-1] for c in rule.missing_config if c.startswith("<")]
        if missing_classes:
            log_handler.messages["missing_classes"][rule.full_name].update(missing_classes)

    if rule.missing_binaries:
        log_handler.messages["missing_binaries"][rule.full_name].update(rule.missing_binaries)

    # Check if preloader can be used for this rule
    if storage.preloader_info and rule.target_name in storage.preloader_info:
        rule.use_preloader = storage.preloader_info[rule.target_name] == {
            k: rule.parameters[k] for k in storage.preloader_info[rule.target_name]
        }

    if config.get("debug"):
        console.print()
        console.print(f"[b]{rule.module_name.upper()}:[/b] {rule.f_name}")
        console.print()
        console.print("    [b]INPUTS[/b]")
        for i in rule.inputs:
            console.print(f"        {i}")
        console.print()
        console.print("    [b]OUTPUTS[/b]")
        for o in rule.outputs:
            console.print(f"        {o}")
        console.print()
        console.print("    [b]PARAMETERS[/b]")
        for p in rule.parameters:
            console.print(f"        {p} = {rule.parameters[p]!r}")
        console.print()
        console.print()

    return True


def name_custom_rule(rule: RuleStorage, storage: SnakeStorage) -> None:
    """Create a unique name for a custom rule.

    If the rule name already exists, a numerical suffix is added to the name.

    Args:
        rule: RuleStorage object.
        storage: SnakeStorage object.
    """

    def get_new_suffix(name: str, existing_names: list[str]) -> str:
        """Find a numerical suffix that leads to a unique rule name.

        Args:
            name: Base name for the rule.
            existing_names: List of existing rule names.

        Returns:
            A numerical suffix that leads to a unique rule name.
        """
        i = 2
        new_name = name + str(i)
        while new_name in existing_names:
            i += 1
            new_name = name + str(i)
        return str(i)

    # If rule name already exists, create a new name
    existing_rules = [r.rule_name for r in storage.all_rules]
    if rule.rule_name in existing_rules:
        suffix = get_new_suffix(rule.rule_name, existing_rules)
        rule.rule_name += suffix
        rule.target_name += suffix
        rule.full_name += suffix


def check_ruleorder(storage: SnakeStorage) -> set[tuple[RuleStorage, RuleStorage]]:
    """Order rules where necessary and print a warning if rule order is missing.

    Args:
        storage: SnakeStorage object.

    Returns:
        A set of tuples with ordered rules.
    """
    ruleorder_pairs = set()
    ordered_rules = set()
    # Find rules that have common outputs and therefore need to be ordered
    rule: RuleStorage
    other_rule: RuleStorage
    for rule, other_rule in combinations(storage.all_rules, 2):
        common_outputs = tuple(sorted(set(rule.outputs).intersection(set(other_rule.outputs))))
        if common_outputs:
            # Check if a rule is lacking ruleorder or if two rules have the same order attribute
            if any(i is None for i in [rule.order, other_rule.order]) or rule.order == other_rule.order:
                ruleorder_pairs.add(((rule, other_rule), common_outputs))
            # Sort ordered rules
            else:
                ordered_rules.add(tuple(sorted([rule, other_rule], key=lambda i: i.order)))

    # Print warning if rule order is lacking somewhere
    for rules, common_outputs in ruleorder_pairs:
        rule1 = rules[0].full_name
        rule2 = rules[1].full_name
        print_sparv_warning(
            f"The annotators {rule1} and {rule2} have common outputs ({', '.join(map(str, common_outputs))}). "
            "Please make sure to set their 'order' arguments to different values."
        )

    return ordered_rules


def file_value(rule_params: RuleStorage) -> Callable:
    """Get the source filename for use as a parameter to a rule.

    Args:
        rule_params: RuleStorage object.

    Returns:
        Function that returns the source filename.
    """

    def _file_value(wildcards: snakemake.io.Wildcards) -> str | None:
        return get_file_value(wildcards, rule_params.annotator)

    return _file_value


def get_parameters(rule_params: RuleStorage) -> Callable:
    """Extend function parameters with source filenames and replace wildcards.

    Args:
        rule_params: RuleStorage object.

    Returns:
        Function that returns the parameters for the rule.
    """

    def get_params(wildcards: snakemake.io.Wildcards) -> dict:
        file = get_file_value(wildcards, rule_params.annotator)
        # We need to make a copy of the parameters, since the rule might be used for multiple source files
        parameters = copy.deepcopy(rule_params.parameters)
        parameters.update({name: SourceFilename(file) for name in rule_params.file_parameters})

        # Add source filename to annotation and output parameters
        for param in parameters.values():
            if isinstance(param, (ExportAnnotations, ExportAnnotationNames)):
                for p in param:
                    p[0].source_file = file
            elif isinstance(param, (SourceAnnotations, HeaderAnnotations)):
                param.source_file = file
            else:
                if not isinstance(param, (list, tuple)):
                    param = [param]  # noqa: PLW2901
                for p in param:
                    if isinstance(p, (Annotation, AnnotationData, Output, OutputData, Text)):
                        p.source_file = file

        # Replace {file} wildcard in parameters
        for name in rule_params.file_annotations:
            if isinstance(parameters[name], Base):
                parameters[name].name = parameters[name].name.replace("{file}", file)
            else:
                parameters[name] = parameters[name].replace("{file}", file)

        # Replace wildcards (other than {file}) in parameters
        for name in rule_params.wildcard_annotations:
            wcs = re.finditer(r"(?!{file}){([^}]+)}", str(parameters[name]))
            for wc in wcs:
                if isinstance(parameters[name], Base):
                    parameters[name].name = parameters[name].name.replace(wc.group(), wildcards.get(wc.group(1)))
                else:
                    parameters[name] = parameters[name].replace(wc.group(), wildcards.get(wc.group(1)))
        return parameters

    return get_params


def update_storage(storage: SnakeStorage, rule: RuleStorage) -> None:
    """Update information in snake storage with different targets.

    Args:
        storage: SnakeStorage object.
        rule: RuleStorage object.
    """
    if rule.exporter:
        storage.export_targets.append((rule.target_name, rule.description, rule.annotator_info["language"]))
    elif rule.importer:
        storage.import_targets.append((rule.target_name, rule.description))
    elif rule.installer:
        storage.install_targets.append((rule.target_name, rule.description, rule.annotator_info["uninstaller"]))
    elif rule.uninstaller:
        storage.uninstall_targets.append((rule.target_name, rule.description))
    elif rule.modelbuilder:
        storage.model_targets.append((rule.target_name, rule.description, rule.annotator_info["language"]))
    else:
        storage.named_targets.append((rule.target_name, rule.description))

    if rule.annotator_info.get("order") is not None:
        storage.ordered_rules.append((rule.rule_name, rule.annotator_info))


def get_source_path() -> str:
    """Get the path to source files.

    Returns:
        Path to source files.
    """
    return sparv_config.get("import.source_dir")


def get_annotation_path(annotation: str | BaseAnnotation, data: bool = False, common: bool = False) -> Path:
    """Construct a path to an annotation file given an annotation name.

    Args:
        annotation: Annotation name or BaseAnnotation object.
        data: Set to True if the annotation is of the data type.
        common: Set to True if the annotation is a common annotation for the whole corpus.

    Returns:
        Path to the annotation file.
    """
    if not isinstance(annotation, BaseAnnotation):
        annotation = BaseAnnotation(annotation)
    elem, attr = annotation.split()
    path = Path(elem)

    if not (data or common):
        if not attr:
            attr = io.SPAN_ANNOTATION
        path /= attr

    if not common:
        path = "{file}" / path
    return path


def get_file_values(config: dict, snake_storage: SnakeStorage) -> list[str]:
    """Get a list of files represented by the {file} wildcard.

    Args:
        config: Dictionary containing the corpus configuration.
        snake_storage: SnakeStorage object.

    Returns:
        List of files represented by the {file} wildcard.
    """
    return config.get("file") or snake_storage.source_files


def get_wildcard_values(config: dict) -> dict:
    """Get user-supplied wildcard values.

    Args:
        config: Dictionary containing the corpus configuration.

    Returns:
        Dictionary with wildcard values.
    """
    return dict(wc.split("=") for wc in config.get("wildcards", []))


def escape_wildcards(s: Path | str) -> str:
    """Escape all wildcards other than {file}.

    Args:
        s: Path or string to escape.

    Returns:
        Escaped string.
    """
    return re.sub(r"(?!{file})({[^}]+})", r"{\1}", str(s))


def get_file_value(wildcards: snakemake.io.Wildcards, annotator: bool) -> str | None:
    """Extract the {file} part from the full annotation path.

    Args:
        wildcards: Wildcards object.
        annotator: True if the rule is an annotator.

    Returns:
        The value of {file}.
    """
    file = None
    if hasattr(wildcards, "file"):
        file = str(Path(wildcards.file).relative_to(paths.work_dir)) if annotator else wildcards.file
    return file


def load_config(snakemake_config: dict) -> bool:
    """Load the corpus config and override the corpus language (if needed).

    Args:
        snakemake_config: Snakemake config dictionary.

    Returns:
        True if the corpus config is missing.
    """
    # Find corpus config
    corpus_config_file = Path.cwd() / paths.config_file
    if corpus_config_file.is_file():
        config_missing = False
        # Read config
        sparv_config.load_config(corpus_config_file)
    else:
        config_missing = True

    # Some commands may override the corpus language
    if snakemake_config.get("language"):
        language = snakemake_config["language"]
        if "-" in language:
            language, _, lang_variety = language.partition("-")
            sparv_config.set_value("metadata.variety", lang_variety)
        sparv_config.set_value("metadata.language", language)

    return config_missing


def get_install_outputs(
    snake_storage: SnakeStorage, install_types: list | None = None, uninstall: bool = False
) -> list[Path]:
    """Collect files to be created for all (un)installations given as arguments or listed in config.(un)install.

    Args:
        snake_storage: SnakeStorage object.
        install_types: List of (un)installation types.
        uninstall: True if uninstallation files should be collected instead of installation files.

    Returns:
        List of files to be created by the selected (un)installations.

    Raises:
        SparvErrorMessage: If unknown (un)installation types are given.
    """
    unknown = []
    install_outputs = []

    if uninstall:
        prefix = "un"
        outputs = snake_storage.uninstall_outputs
        config_list = sparv_config.get("uninstall")
        if config_list is None:
            config_install = sparv_config.get("install", [])
            config_list = [u for t, _, u in snake_storage.install_targets if t in config_install and u]
    else:
        prefix = ""
        outputs = snake_storage.install_outputs
        config_list = sparv_config.get("install", [])

    for installation in install_types or config_list:
        if installation not in outputs:
            unknown.append(installation)
        else:
            install_outputs.extend(outputs[installation])

    if unknown:
        raise SparvErrorMessage(
            "Unknown {}installation{} selected:\n • {}".format(
                prefix, "s" if len(unknown) > 1 else "", "\n • ".join(unknown)
            )
        )

    return install_outputs


def get_export_targets(
    snake_storage: SnakeStorage, workflow: snakemake.Workflow, file: list[str], wildcards: dict
) -> list:
    """Get export targets from sparv_config.

    Args:
        snake_storage: SnakeStorage object.
        workflow: Snakemake workflow object.
        file: List of files represented by the {file} wildcard.
        wildcards: Dictionary with wildcard values.

    Returns:
        List of export targets.

    Raises:
        SparvErrorMessage: If unknown output formats are specified in export.default.
    """
    all_outputs = []
    config_exports = set(sparv_config.get("export.default", []))

    for rule in snake_storage.all_rules:
        if rule.type == "exporter" and rule.target_name in config_exports:
            config_exports.remove(rule.target_name)
            # Get all output files for all source files
            rule_outputs = expand(rule.outputs if not rule.abstract else rule.inputs, file=file, **wildcards)
            # Get Snakemake rule object
            sm_rule = workflow.get_rule(rule.rule_name)
            all_outputs.append((sm_rule if not rule.abstract else None, rule_outputs))

    if config_exports:
        raise SparvErrorMessage(
            "Unknown output format{} specified in export.default:\n • {}".format(
                "s" if len(config_exports) > 1 else "", "\n • ".join(config_exports)
            )
        )

    return all_outputs


def make_param_dict(params: OrderedDict[str, inspect.Parameter]) -> dict:
    """Make a dictionary storing info about a function's parameters.

    Args:
        params: OrderedDict of function parameters.

    Returns:
        Dictionary with parameter names as keys and tuples with default value, type, whether it is a list, and whether
            it is optional as values.
    """
    param_dict = {}
    for p, v in params.items():
        default = v.default if v.default != inspect.Parameter.empty else None
        typ, li, optional = registry.get_type_hint_type(v.annotation)
        param_dict[p] = (default, typ, li, optional)
    return param_dict


def get_reverse_config_usage() -> defaultdict[str, list]:
    """Get a dictionary with annotators as keys, and lists of the config variables they use as values.

    Returns:
        Dictionary with annotators as keys, and lists of the config variables they use as values.
    """
    reverse_config_usage = defaultdict(list)
    for config_key in sparv_config.config_usage:
        for annotator in sparv_config.config_usage[config_key]:
            reverse_config_usage[annotator].append(config_key)
    return reverse_config_usage


def print_sparv_warning(msg: str) -> None:
    """Format a message into a Sparv warning message.

    Args:
        msg: Warning message.
    """
    console.print(f"[red]WARNING:[/] {msg}")


def print_sparv_info(msg: str) -> None:
    """Format a message into a Sparv info message.

    Args:
        msg: Info message.
    """
    console.print(f"[green]{msg}[/green]", highlight=False)
