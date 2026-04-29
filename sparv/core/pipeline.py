"""Util functions for Snakefile."""

from __future__ import annotations

import copy
import enum
import inspect
import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from itertools import combinations
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import snakemake.utils
from snakemake.io import expand

if TYPE_CHECKING:
    import snakemake.iocontainers
    import snakemake.workflow

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

# Regular expression for matching wildcards except for {file}, which is reserved for source files and handled separately
_WILDCARD_NAME_RE = re.compile(r"(?!{file}){([^}]+)}")


class PipelineData:
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

        # All rule catalogs, used in list_rules and autocompletion
        self.annotation_rules = []
        self.export_rules = []
        self.import_rules = []
        self.install_rules = []
        self.uninstall_rules = []
        self.model_rules = []
        self.custom_rules = []

        self.model_outputs = []  # Outputs from model builders, used in build_models
        self.install_outputs = defaultdict(list)  # Outputs from all installers, used in rule install_corpus
        self.uninstall_outputs = defaultdict(list)  # Outputs from all uninstallers, used in rule uninstall_corpus
        self.all_rules: list[RuleInfo] = []  # List containing all rules created
        self.ordered_rules = []  # List of rules containing rule order
        self.preloader_info = {}

        self._source_files = None  # Auxiliary variable for the source_files property

    @property
    def source_files(self) -> list[str]:
        """Return list of all available source files."""
        if self._source_files is None:
            self._source_files = self._discover_source_files()

        return self._source_files

    @staticmethod
    def _discover_source_files() -> list[str]:
        """Discover source files in the source directory based on the active importer.

        Returns:
            A list of source file names without extensions.

        Raises:
            SparvErrorMessage: If the importer setting is empty or if the importer is not found.
        """
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
            return " • " + "\n • ".join(f"{name:<{maxlen}}   {desc}" for name, desc in sorted(importers))

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
        sf = list(snakemake.utils.listfiles(str(Path(source_dir(), "{file}"))))
        result = [f[1][0][: -len(file_extension)] for f in sf if f[1][0].endswith(file_extension)]

        # Collect files that don't match the file extension provided by the corpus config
        wrong_ext = [f[1][0] for f in sf if not f[1][0].endswith(file_extension) and not Path(f[0]).is_dir()]
        if wrong_ext:
            singular = len(wrong_ext) == 1
            verb = "is one" if singular else "are"
            s = "" if singular else "s"
            verb = "es" if singular else ""
            files_str = f"'{wrong_ext[0]}'" if singular else "\n  • " + "\n  • ".join(wrong_ext)
            suffix = ". This file" if singular else "\nThese files"
            console.print(
                f"[yellow]\nThere {verb} file{s} in your source directory that do{verb} not match the file "
                f"extension '{file_extension}' in the corpus config: {files_str}{suffix} will not be "
                "processed.\n[/yellow]",
                highlight=False,
            )
        return result


class RuleInfo:
    """Class to store all relevant information about a rule while it is being built."""

    def __init__(self, module_name: str, f_name: str, annotator_info: dict) -> None:
        """Initialize attributes."""
        self.module_name = module_name
        self.f_name = f_name
        self.annotator_info = annotator_info
        self.name = f"{module_name}:{f_name}"  # Rule name for the all-files aggregate rule, visible to the user
        self.internal_name = f"{module_name}::{f_name}"  # Snakemake-internal rule name (uses :: separator)
        self.inputs: list[Path] = []
        self.outputs: list[Path] = []
        self.parameters = {}
        self.source_file_params = []  # List of parameters referring to SourceFilename
        self.file_wildcard_params = []  # List of parameters containing the {file} wildcard
        self.custom_wildcard_params = []  # List of parameters containing other wildcards
        self.configs = set()  # Set of config variables used
        self.classes = set()  # Set of classes used
        self.missing_config: set[str] = set()
        self.missing_binaries = set()
        self.export_dirs: list[str] | None = None
        self.has_preloader = bool(annotator_info["preloader"])
        self.use_preloader = False
        self.preloader_socket: str | None = None

        self.type: str = annotator_info["type"].name
        self.is_annotator: bool = annotator_info["type"] is registry.Annotator.annotator
        self.is_importer: bool = annotator_info["type"] is registry.Annotator.importer
        self.is_exporter: bool = annotator_info["type"] is registry.Annotator.exporter
        self.is_installer: bool = annotator_info["type"] is registry.Annotator.installer
        self.is_uninstaller: bool = annotator_info["type"] is registry.Annotator.uninstaller
        self.is_modelbuilder: bool = annotator_info["type"] is registry.Annotator.modelbuilder
        self.description: str = annotator_info["description"]
        self.file_extension: str | None = annotator_info["file_extension"]
        self.import_outputs = annotator_info["outputs"]  # Only relevant for importers
        self.priority: int = annotator_info["priority"] or 0
        self.order = annotator_info["order"]
        self.abstract = annotator_info["abstract"]
        self.wildcards = annotator_info["wildcards"]  # Information about the wildcards used


class _ParamResult(enum.Enum):
    """Control flow actions returned by parameter handlers."""

    SKIP = "skip"
    ABORT = "abort"


class RuleBuilder:
    """Encapsulates the logic for populating a RuleInfo with Snakemake inputs, outputs, and parameters."""

    def __init__(
        self,
        rule: RuleInfo,
        config: dict,
        pipeline: PipelineData,
        config_missing: bool = False,
        custom_rule_obj: dict | None = None,
    ) -> None:
        """Initialize attributes.

        Args:
            rule: The RuleInfo object to populate.
            config: The current config dictionary.
            pipeline: The PipelineData object containing global information.
            config_missing: Whether the corpus config is missing, which affects whether most rules should be created.
            custom_rule_obj: If this rule is being created based on a custom rule configuration, the custom rule object
                from the config.
        """
        self.rule = rule
        self.config = config
        self.pipeline = pipeline
        self.config_missing = config_missing
        self.custom_rule_obj = custom_rule_obj

        # Track output directories for processors
        self.output_dirs: set[Path] = set()

        # Keep track of parameters used in custom rules to warn about any that don't actually exist in the function
        self.custom_params: set[str] = set()

        # Custom suffix for regular annotators with alternative configs
        self.custom_suffix: str | None = None
        self.params: dict[str, inspect.Parameter] = {}
        self.param_info: dict = {}  # Used for printable parameter info in CLI listings

    def build(self) -> bool:
        """Build the rule.

        Returns:
            `True` if the rule was successfully built and should be created, `False` if the rule should not be created.
        """
        # Check preconditions, e.g. language and config presence
        if not self._check_preconditions():
            return False

        # Get function parameters
        self.params = dict(inspect.signature(self.rule.annotator_info["function"]).parameters)
        self.param_info = build_param_info(self.params)

        # Register the rule in the appropriate catalog for CLI listings
        self._register_rule_type()

        # If this is the active importer, add its guaranteed outputs to the rule
        if self.rule.is_importer and self.rule.name == sparv_config.get("import.importer"):
            self._setup_importer_outputs()

        # Handle custom rule configuration
        if not self._handle_custom_rule():
            return False

        # Process parameters and populate the rule's inputs, outputs, and parameters
        if not self._process_parameters():
            return False

        self._finalize()
        return True

    # ---- Phase 1: Precondition checks ----

    def _check_preconditions(self) -> bool:
        """Check if this rule should be created at all.

        Returns:
            True if the rule should be created, False otherwise.
        """
        if self.config_missing and not self.rule.is_modelbuilder:
            return False
        return registry.check_language(
            sparv_config.get("metadata.language"),
            self.rule.annotator_info["language"],
            sparv_config.get("metadata.variety"),
        )

    # ---- Phase 2: Rule type registration ----

    def _register_rule_type(self) -> None:
        """Register the rule in the appropriate catalog for CLI listings."""
        rule = self.rule
        pipeline = self.pipeline

        if rule.is_importer:
            rule.inputs.append(Path(source_dir(), f"{{file}}.{rule.file_extension}"))
            pipeline.all_importers.setdefault(rule.module_name, {}).setdefault(
                rule.f_name, {"description": rule.description, "params": self.param_info}
            )
        elif rule.is_exporter:
            pipeline.all_exporters.setdefault(rule.module_name, {}).setdefault(
                rule.f_name, {"description": rule.description, "params": self.param_info}
            )
        elif rule.is_installer:
            pipeline.all_installers.setdefault(rule.module_name, {}).setdefault(
                rule.f_name, {"description": rule.description, "params": self.param_info}
            )
        elif rule.is_uninstaller:
            pipeline.all_uninstallers.setdefault(rule.module_name, {}).setdefault(
                rule.f_name, {"description": rule.description, "params": self.param_info}
            )

        if rule.has_preloader:
            pipeline.all_preloaders.setdefault(rule.module_name, {})[rule.f_name] = rule.annotator_info[
                "preloader_params"
            ]

    def _setup_importer_outputs(self) -> None:
        """Set up outputs for the active importer rule."""
        rule = self.rule
        # Imports always generate corpus text file and structure file
        rule.outputs.append(paths.work_dir / "{file}" / io.TEXT_FILE)
        rule.outputs.append(paths.work_dir / "{file}" / io.STRUCTURE_FILE)

        # If importer guarantees other outputs, add them to outputs list
        if rule.import_outputs:
            # Resolve import_outputs to a list of annotation names
            rule.import_outputs = self._resolve_import_outputs()

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
                rule.outputs.append(paths.work_dir / annotation_path(element))

        # If import.text_annotation has been specified, add it to outputs if not already there
        if sparv_config.get("import.text_annotation"):
            text_ann_file = paths.work_dir / annotation_path(sparv_config.get("import.text_annotation"))
            if text_ann_file not in rule.outputs:
                rule.outputs.append(text_ann_file)

    def _resolve_import_outputs(self) -> list[str]:
        """Resolve import_outputs to a flat list of annotation names.

        Returns:
            A list of annotation names.
        """
        import_outputs = self.rule.import_outputs
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
        return import_outputs

    # ---- Phase 3: Custom rule handling ----

    def _handle_custom_rule(self) -> bool:
        """Handle custom rule configuration.

        Returns:
            `True` if the rule should continue to be created, `False` if the rule should not be created.

        Raises:
            SparvErrorMessage: If the custom rule configuration is invalid.
        """
        if not self.custom_rule_obj:
            return True

        if self.custom_rule_obj.get("params"):
            # This should be either a utility processor or a custom processor supplied by the user
            if not (
                self.rule.module_name == registry.custom_name
                or self.pipeline.all_custom_annotators.get(self.rule.module_name, {}).get(self.rule.f_name)
            ):
                raise SparvErrorMessage(
                    f"The custom annotation for annotator '{self.custom_rule_obj['annotator']}' is using 'params' "
                    "which is not allowed with this type of annotator. Use 'config' instead."
                )
            ensure_unique_rule_name(self.rule, self.pipeline)
            self.custom_params = set(self.custom_rule_obj["params"].keys())
        elif self.custom_rule_obj.get("config"):
            # This is a regular processor but with an alternative config
            ensure_unique_rule_name(self.rule, self.pipeline)
            try:
                self.custom_suffix = self.custom_rule_obj["suffix"]
            except KeyError:
                raise SparvErrorMessage(
                    f"The custom annotation for annotator '{self.custom_rule_obj['annotator']}' is missing the "
                    "required key 'suffix'."
                ) from None
            # Update the config with the custom config values. The original config will be restored after rule creation.
            sparv_config._merge_dicts_replace(sparv_config.config, self.custom_rule_obj["config"])
        else:
            # This is a custom processor which doesn't require any parameters, so it has already been processed during
            # the first rule-building pass
            return False

        return True

    # ---- Phase 4: Parameter processing ----

    def _process_parameters(self) -> bool:
        """Process all function parameters and populate the rule.

        Returns:
            `True` if the rule should continue to be created, `False` if the rule should not be created.
        """
        for param_name, param in self.params.items():
            result = self._resolve_param_value(param_name, param)
            if result is _ParamResult.ABORT:
                return False
            param_value = result

            param_type, param_list, param_optional = registry.get_type_hint_type(param.annotation)

            # Resolve Config objects to their actual values
            if isinstance(param_value, Config):
                param_value = self._resolve_config_value(param_value, param_optional)

            result = self._handle_param_by_type(param_name, param, param_value, param_type, param_list, param_optional)
            if result is _ParamResult.ABORT:
                return False

        self._warn_unknown_custom_params()
        return True

    def _resolve_param_value(self, param_name: str, param: inspect.Parameter) -> Any:
        """Resolve the parameter value from the custom rule object or defaults.

        Args:
            param_name: The name of the parameter to resolve.
            param: The `inspect.Parameter` object representing the parameter.

        Returns:
            The resolved value, or `_ParamResult.ABORT` if the rule should not be created.

        Raises:
            SparvErrorMessage: If the parameter is required but has no value in the custom rule object or defaults.
        """
        param_default_empty = param.default == inspect.Parameter.empty

        if self.custom_rule_obj and "params" in self.custom_rule_obj:
            # This is a custom processor and custom parameters were supplied
            if param_name in self.custom_rule_obj["params"]:
                self.custom_params.discard(param_name)
                return self.custom_rule_obj["params"][param_name]
            if not param_default_empty:
                return copy.deepcopy(param.default)
            raise SparvErrorMessage(
                f"Parameter '{param_name}' in custom processor '{self.rule.name}' has no value!",
                "sparv",
                "config",
            )
        elif param_default_empty:  # noqa: RET506
            # This is a custom processor since it has no default value. Given that no custom parameters were provided,
            # this processor is either unused or it will be handled separately later during the custom rule-building
            # pass. Don't process it any further, but save it in all_custom_annotators and all_annotators.
            self.pipeline.all_custom_annotators.setdefault(self.rule.module_name, {}).setdefault(
                self.rule.f_name, {"description": self.rule.description, "params": self.param_info}
            )
            self.pipeline.custom_rules.append((self.rule.name, self.rule.description))
            self.pipeline.all_annotators.setdefault(self.rule.module_name, {}).setdefault(
                self.rule.f_name,
                {"description": self.rule.description, "annotations": [], "params": self.param_info},
            )
            return _ParamResult.ABORT
        else:
            # This is a regular processor
            return copy.deepcopy(param.default)

    def _resolve_config_value(self, param_value: Config, param_optional: bool) -> Any:
        """Resolve a `Config` parameter to its actual config value.

        Args:
            param_value: The `Config` object to resolve.
            param_optional: Whether this parameter is optional, which affects how missing config values are handled.

        Returns:
            The resolved config value, or `None` if the parameter is optional and the config value is missing.
        """
        self.rule.configs.add(param_value.name)
        config_value = sparv_config.get(param_value.name, sparv_config.Unset)
        if config_value is sparv_config.Unset:
            if param_value.default is not None:
                config_value = param_value.default
            elif param_optional:
                config_value = None
            else:
                self.rule.missing_config.add(param_value.name)
        return config_value

    def _handle_param_by_type(
        self,
        param_name: str,
        param: inspect.Parameter,
        param_value: Any,
        param_type: type,
        param_list: bool,
        param_optional: bool,
    ) -> _ParamResult | None:
        """Dispatch parameter handling to the appropriate type-specific handler.

        Args:
            param_name: The name of the parameter.
            param: The `inspect.Parameter` object representing the parameter.
            param_value: The resolved value of the parameter.
            param_type: The type hint of the parameter.
            param_list: Whether the parameter is a list of the given type.
            param_optional: Whether the parameter is optional.

        Returns:
            The result from the type-specific handler, or `None` if the parameter type is not specially handled.
        """
        rule = self.rule

        if isinstance(param_type, type) and issubclass(param_type, BaseOutput):
            return self._handle_output(param_name, param_value, param_type, param_list, param_optional)
        elif param_type == ModelOutput:  # noqa: RET505
            self._handle_model_output(param_name, param_value)
        elif isinstance(param_type, type) and issubclass(param_type, BaseAnnotation):
            return self._handle_annotation(param_name, param_value, param_type, param_list, param_optional)
        elif param_type in {ExportAnnotations, ExportAnnotationNames, ExportAnnotationsAllSourceFiles}:
            self._handle_export_annotations(param_name, param_value, param_type)
        elif param_type in {SourceAnnotations, SourceAnnotationsAllSourceFiles}:
            self._handle_source_annotations(param_name, param_value, param_type)
        elif param_type in {HeaderAnnotations, HeaderAnnotationsAllSourceFiles}:
            self._handle_header_annotations(param_name, param_value, param_type)
        elif param_type == Corpus:
            self._handle_corpus(param_name, param_optional)
        elif param_type == Language:
            self._handle_language(param_name, param_optional)
        elif param_type == SourceFilename:
            rule.source_file_params.append(param_name)
        elif param_type == AllSourceFilenames:
            param_value.items = self.pipeline.source_files
            rule.parameters[param_name] = param_value
        elif param_type == Text:
            self._handle_text(param_name, param_value)
        elif param_type == Model:
            self._handle_model(param_name, param_value, param_list)
        elif param_type in {Binary, BinaryDir}:
            self._handle_binary(param_name, param, param_type)
        elif param_type == Source:
            rule.parameters[param_name] = Source(source_dir())
        elif param_type == Export:
            self._handle_export(param_name, param)
        elif param_type == ExportInput:
            self._handle_export_input(param_name, param)
        elif param_type == param.empty:
            warn(f"The parameter '{param_name}' in '{rule.name}' is missing a required type hint.")
            rule.parameters[param_name] = param_value
        else:
            rule.parameters[param_name] = param_value

        return None

    def _warn_unknown_custom_params(self) -> None:
        """Warn about parameters in custom rules that don't exist in the function."""
        if self.custom_params:
            s = "s" if len(self.custom_params) > 1 else ""
            verb = "do" if len(self.custom_params) > 1 else "does"
            params_str = "', '".join(self.custom_params)
            warn(
                f"The parameter{s} '{params_str}' used in one of your custom processors {verb} not exist in "
                f"{self.rule.name}."
            )

    # ---- Parameter type handlers ----

    def _handle_output(
        self, param_name: str, param_value: Any, param_type: type, param_list: bool, param_optional: bool
    ) -> _ParamResult | None:
        """Handle Output/OutputData type parameters."""  # noqa: DOC201
        rule = self.rule
        if not isinstance(param_value, (list, tuple)):
            param_value = [param_value]
        outputs_list = []
        for output in param_value:
            if not isinstance(output, BaseOutput):
                if not output:
                    return _ParamResult.ABORT
                output = param_type(output)  # noqa: PLW2901
            elif (
                rule.is_annotator
                and not output.description
                and not rule.module_name.startswith(f"{registry.custom_name}.")
            ):
                console.print(
                    "[red]WARNING:[/] "
                    f"Annotation '{output.name}' created by {rule.type} '{rule.name}' is missing a "
                    "description."
                )
            if self.custom_suffix:
                # Add suffix to output annotation name
                output.name += self.custom_suffix
            self._track_config_and_classes(output.name)
            missing_configs = output.expand_variables(rule.name)
            if (not output or missing_configs) and param_optional:
                rule.parameters[param_name] = None
                return _ParamResult.SKIP
            rule.missing_config.update(missing_configs)
            # Register output tagset so consumers can validate compatibility
            if output.tagset:
                tagset_value, _ = registry.expand_variables(output.tagset, rule.name)
                registry.annotation_tagsets[output.name] = tagset_value
            ann_path = annotation_path(output, data=param_type.data, common=param_type.common)
            if param_type.all_files:
                rule.outputs.extend(self._expand_for_all_files(paths.work_dir / ann_path))
            elif param_type.common:
                rule.outputs.append(paths.work_dir / ann_path)
                if rule.is_installer:
                    self.pipeline.install_outputs[rule.name].append(paths.work_dir / ann_path)
                elif rule.is_uninstaller:
                    self.pipeline.uninstall_outputs[rule.name].append(paths.work_dir / ann_path)
            else:
                rule.outputs.append(annotation_path(output, data=param_type.data))
            if "{" in output:
                rule.custom_wildcard_params.append(param_name)
            outputs_list.append(output)
            if rule.is_annotator:
                self.pipeline.all_annotators.setdefault(rule.module_name, {}).setdefault(
                    rule.f_name, {"description": rule.description, "annotations": [], "params": self.param_info}
                )
                self.pipeline.all_annotators[rule.module_name][rule.f_name]["annotations"].append(
                    (output, output.description)
                )
        rule.parameters[param_name] = outputs_list if param_list else outputs_list[0]
        return None

    def _handle_model_output(self, param_name: str, param_value: Any) -> None:
        """Handle ModelOutput type parameters."""
        self._track_config_and_classes(param_value.name)
        self.rule.missing_config.update(param_value.expand_variables(self.rule.name))
        model_path = param_value.path
        self.rule.outputs.append(model_path)
        self.rule.parameters[param_name] = ModelOutput(str(model_path))
        self.pipeline.model_outputs.append(model_path)
        # Register model output tagset so consumers can validate compatibility
        if param_value.tagset:
            tagset_value, _ = registry.expand_variables(param_value.tagset, self.rule.name)
            registry.model_tagsets[str(model_path)] = tagset_value

    def _handle_annotation(
        self, param_name: str, param_value: Any, param_type: type, param_list: bool, param_optional: bool
    ) -> _ParamResult | None:
        """Handle Annotation/AnnotationData/AnnotationAllSourceFiles type parameters."""  # noqa: DOC201
        rule = self.rule
        if not isinstance(param_value, (list, tuple)):
            param_value = [param_value]
        annotations_list = []
        for annotation in param_value:
            if not isinstance(annotation, BaseAnnotation):
                if not annotation:
                    if param_optional:
                        rule.parameters[param_name] = None
                        return _ParamResult.SKIP
                    return _ParamResult.ABORT
                annotation = param_type(annotation)  # noqa: PLW2901
            self._track_config_and_classes(annotation.name)
            missing_configs = annotation.expand_variables(rule.name)
            if (not annotation or missing_configs) and param_optional:
                rule.parameters[param_name] = None
                return _ParamResult.SKIP
            rule.missing_config.update(missing_configs)
            # Collect tagset requirements for post-build validation
            if annotation.tagset:
                required_tagset, _ = registry.expand_variables(annotation.tagset, rule.name)
                registry.annotation_tagset_requirements.append((annotation.name, required_tagset, rule.name))
            ann_path = annotation_path(annotation, data=param_type.data, common=param_type.common)
            if annotation.is_input:
                if param_type.all_files:
                    rule.inputs.extend(self._expand_for_all_files(paths.work_dir / ann_path))
                elif rule.is_exporter or rule.is_installer or rule.is_uninstaller or param_type.common:
                    rule.inputs.append(paths.work_dir / ann_path)
                else:
                    rule.inputs.append(ann_path)
            if "{" in annotation:
                rule.custom_wildcard_params.append(param_name)
            annotations_list.append(annotation)
        rule.parameters[param_name] = annotations_list if param_list else annotations_list[0]
        return None

    def _handle_export_annotations(self, param_name: str, param_value: Any, param_type: type) -> None:
        """Handle ExportAnnotations/ExportAnnotationNames/ExportAnnotationsAllSourceFiles type parameters."""
        rule = self.rule
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
            self._track_config_and_classes(annotation.name)
            rule.missing_config.update(annotation.expand_variables(rule.name))
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
                        self._expand_for_all_files(paths.work_dir / annotation_path(annotation.name))
                    )
                else:
                    rule.inputs.append(paths.work_dir / annotation_path(annotation.name))
            items.append((annotation, export_name))
        param_value.items = items
        rule.parameters[param_name] = param_value

    def _handle_source_annotations(self, param_name: str, param_value: Any, param_type: type) -> None:
        """Handle SourceAnnotations/SourceAnnotationsAllSourceFiles type parameters."""
        rule = self.rule
        if not isinstance(param_value, param_type):
            param_value = param_type(param_value)
        param_value.raw_list = sparv_config.get(param_value.config_name)
        rule.parameters[param_name] = param_value
        if param_type == SourceAnnotationsAllSourceFiles:
            rule.parameters[param_name].source_files = self.pipeline.source_files
            rule.inputs.extend(
                self._expand_for_all_files(paths.work_dir / annotation_path(io.STRUCTURE_FILE, data=True))
            )
        else:
            rule.inputs.append(paths.work_dir / annotation_path(io.STRUCTURE_FILE, data=True))

    def _handle_header_annotations(self, param_name: str, param_value: Any, param_type: type) -> None:
        """Handle HeaderAnnotations/HeaderAnnotationsAllSourceFiles type parameters."""
        if not isinstance(param_value, param_type):
            param_value = param_type(param_value)
        param_value.raw_list = sparv_config.get(param_value.config_name)
        self.rule.parameters[param_name] = param_value
        if param_type == HeaderAnnotationsAllSourceFiles:
            self.rule.parameters[param_name].source_files = self.pipeline.source_files

    def _handle_corpus(self, param_name: str, param_optional: bool) -> None:
        """Handle Corpus type parameters."""
        if sparv_config.get("metadata.id"):
            self.rule.parameters[param_name] = Corpus(sparv_config.get("metadata.id"))
        elif param_optional:
            self.rule.parameters[param_name] = None
        else:
            self.rule.missing_config.add("metadata.id")

    def _handle_language(self, param_name: str, param_optional: bool) -> None:
        """Handle Language type parameters."""
        if sparv_config.get("metadata.language"):
            self.rule.parameters[param_name] = Language(sparv_config.get("metadata.language"))
        elif param_optional:
            self.rule.parameters[param_name] = None
        else:
            self.rule.missing_config.add("metadata.language")

    def _handle_text(self, param_name: str, param_value: Any) -> None:
        """Handle Text type parameters."""
        text_path = Path("{file}") / io.TEXT_FILE
        if self.rule.is_exporter or self.rule.is_installer or self.rule.is_uninstaller:
            self.rule.inputs.append(paths.work_dir / text_path)
        else:
            self.rule.inputs.append(text_path)
        self.rule.parameters[param_name] = param_value

    def _handle_model(self, param_name: str, param_value: Any, param_list: bool) -> None:
        """Handle Model type parameters."""
        if param_value is None:
            return
        if not isinstance(param_value, (list, tuple)):
            param_value = [param_value]
        model_param = []
        for model in param_value:
            if not isinstance(model, Model):
                model = Model(model)  # noqa: PLW2901
            self._track_config_and_classes(model.name)
            self.rule.missing_config.update(model.expand_variables(self.rule.name))
            self.rule.inputs.append(model.path)
            model_param.append(Model(str(model.path)))
            # Collect tagset requirements for post-build validation
            if model.tagset:
                required_tagset, _ = registry.expand_variables(model.tagset, self.rule.name)
                registry.model_tagset_requirements.append((str(model.path), required_tagset, self.rule.name))
        self.rule.parameters[param_name] = model_param if param_list else model_param[0]

    def _handle_binary(self, param_name: str, param: inspect.Parameter, param_type: type) -> None:
        """Handle Binary/BinaryDir type parameters."""
        rule = self.rule
        self._track_config_and_classes(param.default)
        param_value, missing_configs = registry.expand_variables(param.default, rule.name)
        rule.missing_config.update(missing_configs)
        binary = util.system.find_binary(param_value, executable=False, allow_dir=param_type == BinaryDir)
        if not binary:
            rule.missing_binaries.add(param_value)
        binary = Path(binary or param_value)
        rule.inputs.append(binary)
        rule.parameters[param_name] = param_type(binary)

    def _handle_export(self, param_name: str, param: inspect.Parameter) -> None:
        """Handle Export type parameters."""
        rule = self.rule
        self._track_config_and_classes(param.default)
        param_value, missing_configs = registry.expand_variables(param.default, rule.name)
        rule.missing_config.update(missing_configs)
        export_path = paths.export_dir / param_value
        self.output_dirs.add(export_path.parent)
        rule.outputs.append(export_path)
        rule.parameters[param_name] = Export(str(export_path))
        if "{file}" in rule.parameters[param_name]:
            rule.file_wildcard_params.append(param_name)
        if "{" in param_value:
            rule.custom_wildcard_params.append(param_name)
        if rule.is_exporter:
            self.pipeline.all_exporters[rule.module_name][rule.f_name].setdefault("exports", [])
            self.pipeline.all_exporters[rule.module_name][rule.f_name]["exports"].append(str(export_path))

    def _handle_export_input(self, param_name: str, param: inspect.Parameter) -> None:
        """Handle ExportInput type parameters."""
        rule = self.rule
        self._track_config_and_classes(param.default)
        param_value, missing_configs = registry.expand_variables(param.default, rule.name)
        rule.missing_config.update(missing_configs)
        rule.parameters[param_name] = ExportInput(str(paths.export_dir / param_value))
        if param.default.all_files:
            rule.inputs.extend(self._expand_for_all_files(rule.parameters[param_name]))
        else:
            rule.inputs.append(Path(rule.parameters[param_name]))
        if "{" in rule.parameters[param_name]:
            rule.custom_wildcard_params.append(param_name)

    # ---- Phase 5: Finalization ----

    def _finalize(self) -> None:
        """Post-processing: update pipeline, log warnings, check preloader, and print debug info."""
        rule = self.rule
        pipeline = self.pipeline

        register_rule(pipeline, rule)

        # Add exporter dirs (used for informing user)
        if rule.is_exporter:
            if rule.abstract:
                self.output_dirs = {p.parent for p in rule.inputs}
            rule.export_dirs = [f"{p}/" for p in self.output_dirs]

        if rule.missing_config:
            missing_config = [c for c in rule.missing_config if not c.startswith("<")]
            if missing_config:
                log_handler.messages["missing_configs"][rule.name].update(missing_config)
            missing_classes = [c[1:-1] for c in rule.missing_config if c.startswith("<")]
            if missing_classes:
                log_handler.messages["missing_classes"][rule.name].update(missing_classes)

        if rule.missing_binaries:
            log_handler.messages["missing_binaries"][rule.name].update(rule.missing_binaries)

        # Check if currently running preloader can be used for this rule, by comparing the preloader's parameters with
        # the rule's parameters. We don't want to use a preloader that has been set up using different parameters.
        if pipeline.preloader_info and rule.name in pipeline.preloader_info:
            preloader_info = pipeline.preloader_info[rule.name]
            preloader_params = preloader_info["params"]
            rule.preloader_socket = preloader_info["socket"]

            rule.use_preloader = preloader_params == {k: rule.parameters[k] for k in preloader_params}

        if self.config.get("debug"):
            self._print_debug_info()

    def _print_debug_info(self) -> None:
        """Print debug information about the rule's inputs, outputs, and parameters."""
        rule = self.rule
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

    # ---- Helpers ----

    def _expand_for_all_files(self, path: Path | str) -> list[Path]:
        """Expand a path containing {file} wildcard for all source files.

        Args:
            path: The path to expand.

        Returns:
            A list of expanded paths.
        """
        return list(
            map(
                Path,
                cast(
                    Iterable[str],
                    expand(escape_non_file_wildcards(path), file=self.pipeline.source_files),
                ),
            )
        )

    def _track_config_and_classes(self, name: str) -> None:
        """Track config variables and classes referenced in a parameter value."""
        self.rule.configs.update(registry.find_config_variables(name))
        self.rule.classes.update(registry.find_classes(name))


def ensure_unique_rule_name(rule: RuleInfo, pipeline: PipelineData) -> None:
    """Ensure that a custom rule has a unique name.

    Mutates the rule name fields in place by appending a numeric suffix when needed.

    Args:
        rule: RuleInfo object.
        pipeline: PipelineData object.
    """
    base_name = rule.internal_name
    existing_rules = {r.internal_name for r in pipeline.all_rules}

    if base_name not in existing_rules:
        return

    suffix_num = 2
    while f"{base_name}{suffix_num}" in existing_rules:
        suffix_num += 1

    suffix = str(suffix_num)
    rule.internal_name += suffix
    rule.name += suffix


def resolve_rule_ordering(pipeline: PipelineData) -> set[tuple[RuleInfo, RuleInfo]]:
    """Order rules where necessary and print a warning if rule order is missing.

    Args:
        pipeline: PipelineData object.

    Returns:
        A set of tuples with ordered rules.
    """
    ruleorder_pairs = set()
    ordered_rules = set()
    output_sets = {id(rule): set(rule.outputs) for rule in pipeline.all_rules}
    # Find rules that have common outputs and therefore need to be ordered
    rule: RuleInfo
    other_rule: RuleInfo
    for rule, other_rule in combinations(pipeline.all_rules, 2):
        common_outputs = tuple(sorted(output_sets[id(rule)] & output_sets[id(other_rule)]))
        if common_outputs:
            # Check if a rule is lacking ruleorder or if two rules have the same order attribute
            if any(i is None for i in [rule.order, other_rule.order]) or rule.order == other_rule.order:
                ruleorder_pairs.add(((rule, other_rule), common_outputs))
            # Sort ordered rules
            else:
                ordered_rules.add(tuple(sorted([rule, other_rule], key=lambda i: i.order)))

    # Print warning if rule order is lacking somewhere
    for rules, common_outputs in ruleorder_pairs:
        rule1 = rules[0].name
        rule2 = rules[1].name
        warn(
            f"The annotators {rule1} and {rule2} have common outputs ({', '.join(map(str, common_outputs))}). "
            "Please make sure to set their 'order' arguments to different values."
        )

    return ordered_rules


def make_file_getter(rule: RuleInfo) -> Callable:
    """Create a closure that extracts the source filename from Snakemake wildcards.

    Args:
        rule: RuleInfo object.

    Returns:
        Function that returns the source filename.
    """

    def _get_file(wildcards: snakemake.iocontainers.Wildcards) -> str | None:
        return extract_file_wildcard(wildcards, rule.is_annotator)

    return _get_file


def make_parameter_resolver(rule: RuleInfo) -> Callable:
    """Create a closure that resolves function parameters with source filenames and wildcard values.

    Args:
        rule: RuleInfo object.

    Returns:
        Function that returns the parameters for the rule.
    """

    def _resolve(wildcards: snakemake.iocontainers.Wildcards) -> dict:
        file = extract_file_wildcard(wildcards, rule.is_annotator)
        # We need to make a copy of the parameters, since the rule might be used for multiple source files
        parameters = copy.deepcopy(rule.parameters)
        parameters.update({name: SourceFilename(file) for name in rule.source_file_params})

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
        for name in rule.file_wildcard_params:
            if isinstance(parameters[name], Base):
                parameters[name].name = parameters[name].name.replace("{file}", file)
            else:
                parameters[name] = parameters[name].replace("{file}", file)

        # Replace wildcards (other than {file}) in parameters
        for name in rule.custom_wildcard_params:
            wcs = _WILDCARD_NAME_RE.finditer(str(parameters[name]))
            for wc in wcs:
                if isinstance(parameters[name], Base):
                    parameters[name].name = parameters[name].name.replace(wc.group(), wildcards.get(wc.group(1)))
                else:
                    parameters[name] = parameters[name].replace(wc.group(), wildcards.get(wc.group(1)))
        return parameters

    return _resolve


def register_rule(pipeline: PipelineData, rule: RuleInfo) -> None:
    """Update information in pipeline based on the rule type and add the rule to the appropriate lists.

    Args:
        pipeline: PipelineData object.
        rule: RuleInfo object.
    """
    pipeline.all_rules.append(rule)

    if rule.is_exporter:
        pipeline.export_rules.append((rule.name, rule.description, rule.annotator_info["language"]))
    elif rule.is_importer:
        pipeline.import_rules.append((rule.name, rule.description))
    elif rule.is_installer:
        pipeline.install_rules.append((rule.name, rule.description, rule.annotator_info["uninstaller"]))
    elif rule.is_uninstaller:
        pipeline.uninstall_rules.append((rule.name, rule.description))
    elif rule.is_modelbuilder:
        pipeline.model_rules.append((rule.name, rule.description, rule.annotator_info["language"]))
    elif rule.is_annotator:
        pipeline.annotation_rules.append((rule.name, rule.description))

    if rule.annotator_info.get("order") is not None:
        pipeline.ordered_rules.append((rule.internal_name, rule.annotator_info))


def source_dir() -> str:
    """Get the path to source files.

    Returns:
        Path to source files.
    """
    return sparv_config.get("import.source_dir")


def annotation_path(annotation: str | BaseAnnotation, data: bool = False, common: bool = False) -> Path:
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


def resolve_source_files(config: dict, pipeline: PipelineData) -> list[str]:
    """Get a list of files represented by the {file} wildcard.

    Args:
        config: Dictionary containing the corpus configuration.
        pipeline: PipelineData object.

    Returns:
        List of files represented by the {file} wildcard.
    """
    return config.get("file") or pipeline.source_files


def get_wildcard_values(config: dict) -> dict:
    """Get user-supplied wildcard values.

    Args:
        config: Dictionary containing the corpus configuration.

    Returns:
        Dictionary with wildcard values.
    """
    return dict(wc.split("=") for wc in config.get("wildcards", []))


def escape_non_file_wildcards(s: Path | str) -> str:
    """Escape all wildcards other than {file}.

    Args:
        s: Path or string to escape.

    Returns:
        Escaped string.
    """
    return _WILDCARD_NAME_RE.sub(r"{{\1}}", str(s))


def extract_file_wildcard(wildcards: snakemake.iocontainers.Wildcards, annotator: bool) -> str | None:
    """Extract the {file} part from the full annotation path.

    Args:
        wildcards: Wildcards object.
        annotator: True if the rule is an annotator.

    Returns:
        The value of {file}.
    """
    file = None
    if hasattr(wildcards, "file"):
        file = str(Path(wildcards.file).relative_to(paths.work_dir)) if annotator else wildcards.file  # pyright: ignore[reportAttributeAccessIssue]
    return file


def load_corpus_config(snakemake_config: dict) -> bool:
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


def collect_install_files(
    pipeline: PipelineData, install_types: list | None = None, uninstall: bool = False
) -> list[Path]:
    """Collect files to be created for all (un)installations given as arguments or listed in config.(un)install.

    Args:
        pipeline: PipelineData object.
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
        outputs = pipeline.uninstall_outputs
        config_list = sparv_config.get("uninstall")
        if config_list is None:
            config_install = sparv_config.get("install", [])
            config_list = [u for t, _, u in pipeline.install_rules if t in config_install and u]
    else:
        prefix = ""
        outputs = pipeline.install_outputs
        config_list = sparv_config.get("install", [])

    for installation in install_types or config_list:
        if installation not in outputs:
            unknown.append(installation)
        else:
            install_outputs.extend(outputs[installation])

    if unknown:
        s = "s" if len(unknown) > 1 else ""
        items = "\n • ".join(unknown)
        raise SparvErrorMessage(f"Unknown {prefix}installation{s} selected:\n • {items}")

    return install_outputs


def resolve_export_rules(
    pipeline: PipelineData, workflow: snakemake.workflow.Workflow, file: list[str], wildcards: dict
) -> list:
    """Get export rules from sparv_config.

    Args:
        pipeline: PipelineData object.
        workflow: Snakemake workflow object.
        file: List of files represented by the {file} wildcard.
        wildcards: Dictionary with wildcard values.

    Returns:
        List of export rules.

    Raises:
        SparvErrorMessage: If unknown output formats are specified in export.default.
    """
    all_outputs = []
    config_exports = set(sparv_config.get("export.default", []))

    for rule in pipeline.all_rules:
        if rule.type == "exporter" and rule.name in config_exports:
            config_exports.remove(rule.name)
            # Get all output files for all source files
            rule_outputs = expand(rule.outputs if not rule.abstract else rule.inputs, file=file, **wildcards)
            # Get Snakemake rule object
            sm_rule = workflow.get_rule(rule.internal_name)
            all_outputs.append((sm_rule if not rule.abstract else None, rule_outputs))

    if config_exports:
        s = "s" if len(config_exports) > 1 else ""
        items = "\n • ".join(config_exports)
        raise SparvErrorMessage(f"Unknown output format{s} specified in export.default:\n • {items}")

    return all_outputs


def build_param_info(params: dict[str, inspect.Parameter]) -> dict:
    """Make a dictionary storing info about a function's parameters.

    Args:
        params: OrderedDict of function parameters.

    Returns:
        Dictionary with parameter names as keys and tuples with default value, type, whether it is a list, and whether
            it is optional as values.
    """
    return {
        p: (
            v.default if v.default != inspect.Parameter.empty else None,
            *registry.get_type_hint_type(v.annotation),
        )
        for p, v in params.items()
    }


def config_usage_by_annotator() -> defaultdict[str, list]:
    """Get a dictionary with annotators as keys, and lists of the config variables they use as values.

    Returns:
        Dictionary with annotators as keys, and lists of the config variables they use as values.
    """
    reverse_config_usage = defaultdict(list)
    for config_key in sparv_config.config_usage:
        for annotator in sparv_config.config_usage[config_key]:
            reverse_config_usage[annotator].append(config_key)
    return reverse_config_usage


def warn(msg: str) -> None:
    """Format a message into a Sparv warning message.

    Args:
        msg: Warning message.
    """
    console.print(f"[red]WARNING:[/] {msg}")


def validate_annotation_tagsets() -> None:
    """Check tagset compatibility between annotator outputs and inputs after all rules are built.

    Mismatches are stored in `log_handler.messages["tagset_mismatches"]` keyed by consumer rule name. The log handler
    will abort the pipeline run if any mismatches are found among the rules selected for execution.

    The same check is applied to Model/ModelOutput pairs.
    """
    for ann_name, required_tagset, consumer_rule in registry.annotation_tagset_requirements:
        provider_tagset = registry.annotation_tagsets.get(ann_name)
        if provider_tagset is None:
            # Provider did not declare a tagset, so nothing to validate
            continue
        if provider_tagset != required_tagset:
            log_handler.messages["tagset_mismatches"][consumer_rule].append(
                f"annotation '{ann_name}': consumer requires '{required_tagset}', "
                f"provider declares '{provider_tagset}'"
            )

    for model_path, required_tagset, consumer_rule in registry.model_tagset_requirements:
        provider_tagset = registry.model_tagsets.get(model_path)
        if provider_tagset is None:
            # Model builder did not declare a tagset, so nothing to validate
            continue
        if provider_tagset != required_tagset:
            log_handler.messages["tagset_mismatches"][consumer_rule].append(
                f"model '{model_path}': consumer requires '{required_tagset}', "
                f"model builder declares '{provider_tagset}'"
            )


def info(msg: str) -> None:
    """Format a message into a Sparv info message.

    Args:
        msg: Info message.
    """
    console.print(f"[green]{msg}[/green]", highlight=False)
