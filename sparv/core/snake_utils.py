"""Util functions for Snakefile."""

import copy
import inspect
import re
from collections import OrderedDict, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple

import snakemake
from snakemake.io import expand

from sparv import util
from sparv.core import config as sparv_config
from sparv.core import io, log_handler, paths, registry
from sparv.core.console import console
from sparv.util.classes import (AllDocuments, Annotation, AnnotationAllDocs, AnnotationData, Base, BaseAnnotation,
                                BaseOutput, Binary, BinaryDir, Config, Corpus, Document, Export, ExportAnnotations,
                                ExportAnnotationsAllDocs, ExportInput, Language, Model, ModelOutput, Output, OutputData,
                                Source, SourceAnnotations, Text)


class SnakeStorage:
    """Object to store variables involving all rules."""

    def __init__(self):
        """Init attributes."""
        # All annotators, importers, exporters and installers available, used for CLI listings
        self.all_annotators = {}
        self.all_importers = {}
        self.all_exporters = {}
        self.all_installers = {}
        self.all_custom_annotators = {}

        # All named targets available, used in list_targets
        self.named_targets = []
        self.export_targets = []
        self.install_targets = []
        self.model_targets = []
        self.custom_targets = []

        self.model_outputs = []  # Outputs from modelbuilders, used in build_models
        self.install_outputs = defaultdict(list)  # Outputs from all installers, used in rule install_corpus
        self.source_files = []  # List which will contain all source files
        self.all_rules: List[RuleStorage] = []  # List containing all rules created
        self.ordered_rules = []  # List of rules containing rule order


class RuleStorage:
    """Object to store parameters for a snake rule."""

    def __init__(self, module_name, f_name, annotator_info):
        """Init attributes."""
        self.module_name = module_name
        self.f_name = f_name
        self.annotator_info = annotator_info
        self.target_name = f"{module_name}:{f_name}"  # Rule name for the "all-files-rule" based on this rule
        self.rule_name = f"{module_name}::{f_name}"  # Actual Snakemake rule name for internal use
        self.full_name = f"{module_name}:{f_name}"  # Used in messages to the user
        self.inputs = []
        self.outputs = []
        self.parameters = {}
        self.docs = []  # List of parameters referring to Document
        self.doc_annotations = []  # List of parameters containing the {doc} wildcard
        self.wildcard_annotations = []  # List of parameters containing other wildcards
        self.configs = set()  # Set of config variables used
        self.classes = set()  # Set of classes used
        self.missing_config = set()
        self.missing_binaries = set()
        self.export_dirs = None

        self.type = annotator_info["type"].name
        self.annotator = annotator_info["type"] is registry.Annotator.annotator
        self.importer = annotator_info["type"] is registry.Annotator.importer
        self.exporter = annotator_info["type"] is registry.Annotator.exporter
        self.installer = annotator_info["type"] is registry.Annotator.installer
        self.modelbuilder = annotator_info["type"] is registry.Annotator.modelbuilder
        self.description = annotator_info["description"]
        self.file_extension = annotator_info["file_extension"]
        self.import_outputs = annotator_info["outputs"]
        self.order = annotator_info["order"]
        self.abstract = annotator_info["abstract"]
        self.wildcards = annotator_info["wildcards"]  # Information about the wildcards used


def rule_helper(rule: RuleStorage, config: dict, storage: SnakeStorage, config_missing: bool = False,
                custom_rule_obj: Optional[dict] = None) -> bool:
    """
    Populate rule with Snakemake input, output and parameter list.

    Return True if a Snakemake rule should be created.

    Args:
        rule: Object containing snakemake rule parameters.
        config: Dictionary containing the corpus configuration.
        storage: Object for saving information for all rules.
        config_missing: True if there is no corpus config file.
        custom_rule_obj: Custom annotation dictionary from corpus config.
    """
    # Only create certain rules when config is missing
    if config_missing and not rule.modelbuilder:
        return False

    # Skip any annotator that is not available for the selected corpus language
    if rule.annotator_info["language"] and sparv_config.get("metadata.language") and \
            sparv_config.get("metadata.language") not in rule.annotator_info["language"]:
        return False

    # Get this function's parameters
    params = OrderedDict(inspect.signature(rule.annotator_info["function"]).parameters)
    param_dict = make_param_dict(params)

    if rule.importer:
        rule.inputs.append(Path(get_source_path(), "{doc}." + rule.file_extension))
        storage.all_importers.setdefault(rule.module_name, {}).setdefault(rule.f_name,
                                                                          {"description": rule.description,
                                                                           "params": param_dict})
        if rule.target_name == sparv_config.get("import.importer"):
            # Exports always generate corpus text file
            rule.outputs.append(paths.work_dir / "{doc}" / io.TEXT_FILE)
            # If importer guarantees other outputs, add them to outputs list
            if rule.import_outputs:
                if isinstance(rule.import_outputs, Config):
                    rule.import_outputs = sparv_config.get(rule.import_outputs, rule.import_outputs.default)
                annotations_ = set()
                renames = {}
                # Annotation list needs to be sorted to handle plain annotations before attributes
                for ann, target in sorted(util.parse_annotation_list(rule.import_outputs)):
                    # Handle annotations renamed during import
                    if target:
                        source_ann, source_attr = BaseAnnotation(ann).split()
                        if not source_attr:
                            renames[ann] = target
                            ann = target
                        else:
                            ann = io.join_annotation(renames.get(source_ann, source_ann), target)
                    annotations_.add(ann)

                for element in annotations_:
                    rule.outputs.append(paths.work_dir / get_annotation_path(element))

            # If import.document_annotation has been specified, add it to outputs if not already there
            if sparv_config.get("import.document_annotation"):
                doc_ann_file = paths.work_dir / get_annotation_path(sparv_config.get("import.document_annotation"))
                if doc_ann_file not in rule.outputs:
                    rule.outputs.append(doc_ann_file)

    if rule.exporter:
        storage.all_exporters.setdefault(rule.module_name, {}).setdefault(rule.f_name,
                                                                          {"description": rule.description,
                                                                           "params": param_dict})
    elif rule.installer:
        storage.all_installers.setdefault(rule.module_name, {}).setdefault(rule.f_name,
                                                                           {"description": rule.description,
                                                                            "params": param_dict})

    output_dirs = set()    # Directories where export files are stored
    custom_params = set()

    if custom_rule_obj:
        if custom_rule_obj.get("params"):
            name_custom_rule(rule, storage)
            custom_params = set(custom_rule_obj.get("params").keys())
        else:
            # This rule has already been populated, so don't process it again
            return False

    # Go though function parameters and handle based on type
    for param_name, param in params.items():
        param_default_empty = param.default == inspect.Parameter.empty
        param_value: Any

        # Get parameter value, either from custom rule object or default value
        if custom_rule_obj:
            if param_name in custom_rule_obj["params"]:
                param_value = custom_rule_obj["params"][param_name]
                custom_params.remove(param_name)
            elif not param_default_empty:
                param_value = copy.deepcopy(param.default)
            else:
                raise util.SparvErrorMessage(
                    f"Parameter '{param_name}' in custom rule '{rule.full_name}' has no value!", "sparv", "config")
        else:
            if param_default_empty:
                # This is probably an unused custom rule, so don't process it any further,
                # but save it in all_custom_annotators and all_annotators
                storage.all_custom_annotators.setdefault(rule.module_name, {}).setdefault(rule.f_name, {
                    "description": rule.description, "params": param_dict})
                storage.custom_targets.append((rule.target_name, rule.description))
                storage.all_annotators.setdefault(rule.module_name, {}).setdefault(rule.f_name, {
                    "description": rule.description, "annotations": [], "params": param_dict})
                return False
            else:
                param_value = copy.deepcopy(param.default)

        param_type, param_list, param_optional = registry.get_type_hint_type(param.annotation)

        # Output
        if issubclass(param_type, BaseOutput):
            if not isinstance(param_value, BaseOutput):
                if not param_value:
                    return False
                param_value = param_type(param_value)
            rule.configs.update(registry.find_config_variables(param_value.name))
            rule.classes.update(registry.find_classes(param_value.name))
            missing_configs = param_value.expand_variables(rule.full_name)
            rule.missing_config.update(missing_configs)
            ann_path = get_annotation_path(param_value, data=param_type.data, common=param_type.common)
            if param_type.all_docs:
                rule.outputs.extend(map(Path, expand(escape_wildcards(paths.work_dir / ann_path),
                                                     doc=get_source_files(storage.source_files))))
            elif param_type.common:
                rule.outputs.append(paths.work_dir / ann_path)
                if rule.installer:
                    storage.install_outputs[rule.target_name].append(paths.work_dir / ann_path)
            else:
                rule.outputs.append(get_annotation_path(param_value, data=param_type.data))
            rule.parameters[param_name] = param_value
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
            if rule.annotator:
                storage.all_annotators.setdefault(rule.module_name, {}).setdefault(rule.f_name,
                                                                                   {"description": rule.description,
                                                                                    "annotations": [],
                                                                                    "params": param_dict})
                storage.all_annotators[rule.module_name][rule.f_name]["annotations"].append((param_value,
                                                                                             param_value.description))
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
        elif issubclass(param_type, BaseAnnotation):
            if not isinstance(param_value, BaseAnnotation):
                if not param_value:
                    return False
                param_value = param_type(param_value)
            rule.configs.update(registry.find_config_variables(param_value.name))
            rule.classes.update(registry.find_classes(param_value.name))
            missing_configs = param_value.expand_variables(rule.full_name)
            if (not param_value or missing_configs) and param_optional:
                rule.parameters[param_name] = None
                continue
            rule.missing_config.update(missing_configs)
            ann_path = get_annotation_path(param_value, data=param_type.data, common=param_type.common)
            if param_type.all_docs:
                rule.inputs.extend(expand(escape_wildcards(paths.work_dir / ann_path),
                                          doc=get_source_files(storage.source_files)))
            elif rule.exporter or rule.installer or param_type.common:
                rule.inputs.append(paths.work_dir / ann_path)
            else:
                rule.inputs.append(ann_path)

            rule.parameters[param_name] = param_value
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
        # ExportAnnotations
        elif param_type in (ExportAnnotations, ExportAnnotationsAllDocs):
            if not isinstance(param_value, param_type):
                param_value = param_type(param_value)
            rule.parameters[param_name] = param_value

            source = param.default.config_name
            annotations = sparv_config.get(f"{source}", [])
            if not annotations:
                rule.missing_config.add(f"{source}")
            export_annotations = util.parse_annotation_list(annotations, add_plain_annotations=False)
            annotation_type = Annotation if param_type == ExportAnnotations else AnnotationAllDocs
            plain_annotations = set()
            possible_plain_annotations = []
            for i, (export_annotation_name, export_name) in enumerate(export_annotations):
                annotation = annotation_type(export_annotation_name)
                rule.configs.update(registry.find_config_variables(annotation.name))
                rule.classes.update(registry.find_classes(annotation.name))
                rule.missing_config.update(annotation.expand_variables(rule.full_name))
                export_annotations[i] = (annotation, export_name)
                plain_name, attr = annotation.split()
                if not attr:
                    plain_annotations.add(plain_name)
                else:
                    if plain_name not in possible_plain_annotations:
                        possible_plain_annotations.append(plain_name)
            # Add plain annotations where needed
            for a in possible_plain_annotations:
                if a not in plain_annotations:
                    export_annotations.append((annotation_type(a), None))

            for annotation, export_name in export_annotations:
                if param.default.is_input:
                    if param_type == ExportAnnotationsAllDocs:
                        rule.inputs.extend(
                            expand(escape_wildcards(paths.work_dir / get_annotation_path(annotation.name)),
                                   doc=get_source_files(storage.source_files)))
                    else:
                        rule.inputs.append(paths.work_dir / get_annotation_path(annotation.name))
                rule.parameters[param_name].append((annotation, export_name))
        # SourceAnnotations
        elif param_type == SourceAnnotations:
            rule.parameters[param_name] = sparv_config.get(f"{param.default.config_name}", None)
        # Corpus
        elif param.annotation == Corpus:
            rule.parameters[param_name] = Corpus(sparv_config.get("metadata.id"))
        # Language
        elif param.annotation == Language:
            rule.parameters[param_name] = Language(sparv_config.get("metadata.language"))
        # Document
        elif param.annotation == Document:
            rule.docs.append(param_name)
        # AllDocuments (all source documents)
        elif param_type == AllDocuments:
            rule.parameters[param_name] = AllDocuments(get_source_files(storage.source_files))
        # Text
        elif param_type == Text:
            text_path = Path("{doc}") / io.TEXT_FILE
            if rule.exporter or rule.installer:
                rule.inputs.append(paths.work_dir / text_path)
            else:
                rule.inputs.append(text_path)
            rule.parameters[param_name] = param_value
        # Model
        elif param_type == Model:
            if param_value is not None:
                if param_list:
                    rule.parameters[param_name] = []
                    for model in param_value:
                        if not isinstance(model, Model):
                            model = Model(param_value)
                        rule.configs.update(registry.find_config_variables(model.name))
                        rule.classes.update(registry.find_classes(model.name))
                        rule.missing_config.update(model.expand_variables(rule.full_name))
                        rule.inputs.append(model.path)
                        rule.parameters[param_name].append(Model(str(model.path)))
                else:
                    if not isinstance(param_value, Model):
                        param_value = Model(param_value)
                    rule.configs.update(registry.find_config_variables(param_value.name))
                    rule.classes.update(registry.find_classes(param_value.name))
                    rule.missing_config.update(param_value.expand_variables(rule.full_name))
                    rule.inputs.append(param_value.path)
                    rule.parameters[param_name] = Model(str(param_value.path))
        # Binary
        elif param.annotation in (Binary, BinaryDir):
            rule.configs.update(registry.find_config_variables(param.default))
            rule.classes.update(registry.find_classes(param.default))
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            binary = util.find_binary(param_value, executable=False, allow_dir=param.annotation == BinaryDir)
            if not binary:
                rule.missing_binaries.add(param_value)
            binary = Path(binary if binary else param_value)
            rule.inputs.append(binary)
            rule.parameters[param_name] = param.annotation(binary)
        # Source
        elif param.annotation == Source:
            rule.parameters[param_name] = Source(get_source_path())
        # Export
        elif param.annotation == Export:
            rule.configs.update(registry.find_config_variables(param.default))
            rule.classes.update(registry.find_classes(param.default))
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            if param.default.absolute_path:
                export_path = Path(param_value)
            else:
                export_path = paths.export_dir / param_value
            output_dirs.add(export_path.parent)
            rule.outputs.append(export_path)
            rule.parameters[param_name] = Export(str(export_path))
            if "{doc}" in rule.parameters[param_name]:
                rule.doc_annotations.append(param_name)
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
        # ExportInput
        elif param.annotation == ExportInput:
            rule.configs.update(registry.find_config_variables(param.default))
            rule.classes.update(registry.find_classes(param.default))
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            if param.default.absolute_path:
                rule.parameters[param_name] = ExportInput(param_value)
            else:
                rule.parameters[param_name] = ExportInput(paths.export_dir / param_value)
            if param.default.all_docs:
                rule.inputs.extend(expand(escape_wildcards(rule.parameters[param_name]),
                                          doc=get_source_files(storage.source_files)))
            else:
                rule.inputs.append(Path(rule.parameters[param_name]))
            if "{" in rule.parameters[param_name]:
                rule.wildcard_annotations.append(param_name)
        # Config
        elif isinstance(param_value, Config):
            rule.configs.add(param_value.name)
            config_value = sparv_config.get(param_value, sparv_config.Unset)
            if config_value is sparv_config.Unset:
                if param_value.default is not None:
                    config_value = param_value.default
                elif param_optional:
                    config_value = None
                else:
                    rule.missing_config.add(param_value)
            rule.parameters[param_name] = config_value
        # Everything else
        else:
            rule.parameters[param_name] = param_value

    # For custom rules, warn the user of any unknown parameters
    if custom_params:
        print_sparv_warning("The parameter{} '{}' used in one of your custom rules "
                            "do{} not exist in {}.".format("s" if len(custom_params) > 1 else "",
                                                           "', '".join(custom_params),
                                                           "es" if len(custom_params) == 1 else "",
                                                           rule.full_name))

    storage.all_rules.append(rule)

    # Add to rule lists in storage
    update_storage(storage, rule)

    # Add exporter dirs (used for informing user)
    if rule.exporter:
        if rule.abstract:
            output_dirs = set([p.parent for p in rule.inputs])
        rule.export_dirs = [str(p / "_")[:-1] for p in output_dirs]

    if rule.missing_config:
        log_handler.messages["missing_configs"][rule.full_name].update(
            [c for c in rule.missing_config if not c.startswith("<")])
        log_handler.messages["missing_classes"][rule.full_name].update(
            [c[1:-1] for c in rule.missing_config if c.startswith("<")])

    if rule.missing_binaries:
        log_handler.messages["missing_binaries"][rule.full_name].update(rule.missing_binaries)

    if config.get("debug"):
        print()
        console.print("[b]{}:[/b] {}".format(rule.module_name.upper(), rule.f_name))
        print()
        console.print("    [b]INPUTS[/b]")
        for i in rule.inputs:
            print("        {}".format(i))
        print()
        console.print("    [b]OUTPUTS[/b]")
        for o in rule.outputs:
            print("        {}".format(o))
        print()
        console.print("    [b]PARAMETERS[/b]")
        for p in rule.parameters:
            print("        {} = {!r}".format(p, rule.parameters[p]))
        print()
        print()

    return True


def name_custom_rule(rule, storage):
    """Create unique name for custom rule."""
    def create_new_rulename(name, existing_names):
        """Create a new rule name by appending a number to it."""
        i = 2
        new_name = name + str(i)
        while new_name in existing_names:
            i += 1
            new_name = name + str(i)
        return new_name

    # If rule name already exists, create a new name
    existing_rules = [r.rule_name for r in storage.all_rules]
    if rule.rule_name in existing_rules:
        rule.rule_name = create_new_rulename(rule.rule_name, existing_rules)
        rule.target_name = create_new_rulename(rule.target_name, [r.target_name for r in storage.all_rules])


def check_ruleorder(storage: SnakeStorage) -> Set[Tuple[RuleStorage, RuleStorage]]:
    """Order rules where necessary and print warning if rule order is missing."""
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
        common_outputs = ", ".join(map(str, common_outputs))
        print_sparv_warning(f"The annotators {rule1} and {rule2} have common outputs ({common_outputs}). "
                            "Please make sure to set their 'order' arguments to different values.")

    return ordered_rules


def get_parameters(rule_params):
    """Extend function parameters with doc names and replace wildcards."""
    def get_params(wildcards):
        doc = get_doc_value(wildcards, rule_params.annotator)
        # We need to make a copy of the parameters, since the rule might be used for multiple documents
        _parameters = copy.deepcopy(rule_params.parameters)
        _parameters.update({name: Document(doc) for name in rule_params.docs})

        # Add document name to annotation and output parameters
        for param in _parameters:
            if isinstance(_parameters[param], (Annotation, AnnotationData, Output, OutputData, Text)):
                _parameters[param].doc = doc
            if isinstance(_parameters[param], ExportAnnotations):
                for a in _parameters[param]:
                    a[0].doc = doc

        # Replace {doc} wildcard in parameters
        for name in rule_params.doc_annotations:
            if isinstance(_parameters[name], Base):
                _parameters[name].name = _parameters[name].name.replace("{doc}", doc)
            else:
                _parameters[name] = _parameters[name].replace("{doc}", doc)

        # Replace wildcards (other than {doc}) in parameters
        for name in rule_params.wildcard_annotations:
            wcs = re.finditer(r"(?!{doc}){([^}]+)}", str(_parameters[name]))
            for wc in wcs:
                if isinstance(_parameters[name], Base):
                    _parameters[name].name = _parameters[name].name.replace(wc.group(), wildcards.get(wc.group(1)))
                else:
                    _parameters[name] = _parameters[name].replace(wc.group(), wildcards.get(wc.group(1)))
        return _parameters
    return get_params


def update_storage(storage, rule):
    """Update info to snake storage with different targets."""
    if rule.exporter:
        storage.export_targets.append((rule.target_name, rule.description,
                                       rule.annotator_info["language"]))
    elif rule.installer:
        storage.install_targets.append((rule.target_name, rule.description))
    elif rule.modelbuilder:
        storage.model_targets.append((rule.target_name, rule.description, rule.annotator_info["language"]))
    else:
        storage.named_targets.append((rule.target_name, rule.description))

    if rule.annotator_info.get("order") is not None:
        storage.ordered_rules.append((rule.rule_name, rule.annotator_info))


def get_source_path() -> str:
    """Get path to source files."""
    return sparv_config.get("import.source_dir")


def get_annotation_path(annotation, data=False, common=False):
    """Construct a path to an annotation file given a doc and annotation."""
    if not isinstance(annotation, BaseAnnotation):
        annotation = BaseAnnotation(annotation)
    elem, attr = annotation.split()
    path = Path(elem)

    if not (data or common):
        if not attr:
            attr = io.SPAN_ANNOTATION
        path = path / attr

    if not common:
        path = "{doc}" / path
    return path


def get_source_files(source_files) -> List[str]:
    """Get list of all available source files."""
    if not source_files:
        if not sparv_config.get("import.importer"):
            raise util.SparvErrorMessage("The config variable 'import.importer' must not be empty.", "sparv")
        try:
            importer_module, _, importer_function = sparv_config.get("import.importer").partition(":")
            file_extension = registry.modules[importer_module].functions[importer_function]["file_extension"]
        except KeyError:
            raise util.SparvErrorMessage(
                "Could not find the importer '{}'. Make sure the 'import.importer' config value refers to an "
                "existing importer.".format(sparv_config.get("import.importer")), "sparv")
        source_files = [f[1][0] for f in snakemake.utils.listfiles(
            Path(get_source_path(), "{file}." + file_extension))]
    return source_files


def get_doc_values(config, snake_storage):
    """Get a list of files represented by the doc wildcard."""
    return config.get("doc") or get_source_files(snake_storage.source_files)


def get_wildcard_values(config):
    """Get user-supplied wildcard values."""
    return dict(wc.split("=") for wc in config.get("wildcards", []))


def escape_wildcards(s):
    """Escape all wildcards other than {doc}."""
    return re.sub(r"(?!{doc})({[^}]+})", r"{\1}", str(s))


def get_doc_value(wildcards, annotator):
    """Extract the {doc} part from full annotation path."""
    doc = None
    if hasattr(wildcards, "doc"):
        if annotator:
            doc = wildcards.doc[len(str(paths.work_dir)) + 1:]
        else:
            doc = wildcards.doc
    return doc


def load_config(snakemake_config):
    """Load corpus config and override the corpus language (if needed)."""
    # Find corpus config
    corpus_config_file = Path.cwd() / paths.config_file
    if corpus_config_file.is_file():
        config_missing = False
        # Read config
        sparv_config.load_config(corpus_config_file)

        # Add classes from config to registry
        registry.annotation_classes["config_classes"] = sparv_config.config.get("classes", {})
    else:
        config_missing = True

    # Some commands may override the corpus language
    if snakemake_config.get("language"):
        sparv_config.set_value("metadata.language", snakemake_config["language"])

    return config_missing


def get_install_outputs(snake_storage: SnakeStorage, install_types: Optional[List] = None):
    """Collect files to be created for all installations given as argument or listed in config.install."""
    install_inputs = []
    for installation in install_types or sparv_config.get("install", []):
        install_inputs.extend(snake_storage.install_outputs[installation])

    return install_inputs


def get_export_targets(snake_storage, rules, doc, wildcards):
    """Get export targets from sparv_config."""
    all_outputs = []

    for rule in snake_storage.all_rules:
        if rule.type == "exporter" and rule.target_name in sparv_config.get("export.default", []):
            # Get Snakemake rule object
            sm_rule = getattr(rules, rule.rule_name).rule
            # Get all output files for all documents
            rule_outputs = expand(rule.outputs if not rule.abstract else rule.inputs, doc=doc, **wildcards)
            # Convert paths to IOFile objects so Snakemake knows which rule they come from (in case of ambiguity)
            all_outputs.extend([snakemake.io.IOFile(f, rule=sm_rule) for f in rule_outputs])

    return all_outputs


def make_param_dict(params):
    """Make dictionary storing info about a function's parameters."""
    param_dict = {}
    for p, v in params.items():
        default = v.default if v.default != inspect.Parameter.empty else None
        typ, li, optional = registry.get_type_hint_type(v.annotation)
        param_dict[p] = (default, typ, li, optional)
    return param_dict


def get_reverse_config_usage():
    """Get config variables used by each annotator."""
    reverse_config_usage = defaultdict(list)
    for config_key in sparv_config.config_usage:
        for annotator in sparv_config.config_usage[config_key]:
            reverse_config_usage[annotator].append((config_key, sparv_config.get_config_description(config_key)))
    return reverse_config_usage


def print_sparv_warning(msg):
    """Format msg into a Sparv warning message."""
    console.print(f"[yellow]WARNING: {msg}[/yellow]", highlight=False)


def print_sparv_info(msg):
    """Format msg into a Sparv info message."""
    console.print(f"[green]{msg}[/green]", highlight=False)
