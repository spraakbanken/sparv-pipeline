"""Util functions for Snakefile."""

import inspect
import re
from collections import defaultdict
from pathlib import Path
from typing import List

import snakemake
from snakemake.io import expand

from sparv import util
from sparv.core import config as sparv_config
from sparv.core import paths, registry
from sparv.util.classes import (AllDocuments, Annotation, Binary, Config, Corpus, Document, Export, ExportAnnotations,
                                ExportInput, Language, Model, ModelOutput, Output, Source)


class SnakeStorage(object):
    """Object to store..."""

    def __init__(self):
        """Init attributes."""
        # All output annotations available, used for printing a list
        self.all_annotations = {}

        # All named targets available, used in list_targets
        self.named_targets = []
        self.export_targets = []
        self.install_targets = []
        self.model_targets = []

        # Outputs from modelbuilders, used in build_models
        self.model_outputs = []
        # Outputs from all installers, used in install_annotated_corpus
        self.install_outputs = defaultdict(list)
        # List which will contain all source files
        self.source_files = []


class RuleStorage(object):
    """Object to store parameters for a snake rule."""

    def __init__(self, module_name, f_name, annotator_info):
        """Init attributes."""
        self.target_name = module_name + ":" + f_name
        self.inputs = []
        self.outputs = []
        self.parameters = {}
        self.docs = []  # List of parameters referring to Document
        self.doc_annotations = []  # List of parameters containing the {doc} wildcard
        self.wildcard_annotations = []  # List of parameters containing other wildcards

        self.annotator = annotator_info["type"] is registry.Annotator.annotator
        self.importer = annotator_info["type"] is registry.Annotator.importer
        self.exporter = annotator_info["type"] is registry.Annotator.exporter
        self.installer = annotator_info["type"] is registry.Annotator.installer
        self.modelbuilder = annotator_info["type"] is registry.Annotator.modelbuilder
        self.description = annotator_info["description"]
        self.source_type = annotator_info["source_type"]
        self.import_outputs = annotator_info["outputs"]


def rule_helper(module_name: str, f_name: str, annotator_info: dict, config: dict, storage: SnakeStorage,
                config_missing: bool = False) -> RuleStorage:
    """Build Snakemake rules."""
    # Build input, output and parameter list
    if config.get("debug"):
        print()
        print("{}{}:{} {}".format(util.Color.BOLD, module_name.upper(), util.Color.RESET, f_name))
        print()

    rule = RuleStorage(module_name, f_name, annotator_info)

    full_module_name = f"{module_name}.{f_name}"

    # Only create certain rules when config is missing
    if config_missing and not rule.modelbuilder:
        return

    # Skip any annotator that is not available for the selected corpus language
    if annotator_info["language"] and sparv_config.get("metadata.language") not in annotator_info["language"]:
        return

    if rule.importer:
        rule.inputs.append(Path(get_source_path(), "{doc}." + rule.source_type))
        if rule.source_type == sparv_config.get("source_type", "xml"):
            # Exports always generate corpus text file
            rule.outputs.append(paths.annotation_dir / "{doc}" / util.TEXT_FILE)
            # If importer guarantees other outputs, add them to outputs list
            if rule.import_outputs:
                if isinstance(rule.import_outputs, Config):
                    import_outputs = sparv_config.get(rule.import_outputs, rule.import_outputs.default)
                annotations_ = set()
                for annotation in import_outputs:
                    annotations_.add(annotation)
                    annotations_.add(util.split_annotation(annotation)[0])
                for element in annotations_:
                    rule.outputs.append(paths.annotation_dir / get_annotation_path(element))

    params = inspect.signature(annotator_info["function"]).parameters

    # Go though function parameters and handle based on type
    for param_name, param in params.items():
        # Output
        if isinstance(param.default, Output):
            param_value = registry.expand_variables(param.default, full_module_name)
            ann_path = get_annotation_path(param_value, data=param.default.data, common=param.default.common)
            if param.default.all_docs:
                rule.outputs.extend(map(Path, expand(escape_wildcards(paths.annotation_dir / ann_path),
                                                     doc=get_source_files(storage.source_files))))
            elif param.default.common:
                rule.outputs.append(paths.annotation_dir / ann_path)
                if rule.installer:
                    storage.install_outputs[rule.target_name].append(paths.annotation_dir / ann_path)
            else:
                rule.outputs.append(get_annotation_path(param_value, data=param.default.data))
            rule.parameters[param_name] = param_value
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
            storage.all_annotations.setdefault(module_name, {}).setdefault(f_name, {"description": rule.description,
                                                                                    "annotations": []})
            storage.all_annotations[module_name][f_name]["annotations"].append((param.default,
                                                                                param.default.description))
        # ModelOutput
        elif isinstance(param.default, ModelOutput):
            model = util.get_model_path(registry.expand_variables(param.default, full_module_name))
            rule.outputs.append(model)
            rule.parameters[param_name] = str(model)
            storage.model_outputs.append(model)
        # Annotation
        elif registry.dig(Annotation, param.default):
            param_value = registry.expand_variables(param.default, full_module_name)
            ann_path = get_annotation_path(param_value, data=param.default.data, common=param.default.common)
            if rule.exporter or rule.installer or param.default.all_docs:
                if param.default.all_docs:
                    rule.inputs.extend(expand(escape_wildcards(paths.annotation_dir / ann_path),
                                              doc=get_source_files(storage.source_files)))
                else:
                    rule.inputs.append(paths.annotation_dir / ann_path)
            elif param.default.common:
                rule.inputs.append(paths.annotation_dir / ann_path)
            else:
                rule.inputs.append(ann_path)

            rule.parameters[param_name] = param_value
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
        # ExportAnnotations
        elif param.default == ExportAnnotations or isinstance(param.default, ExportAnnotations):
            export_type = param.default.export_type
            rule.parameters[param_name] = []
            export_annotations = sparv_config.get(f"{export_type}.annotations", [])
            for annotation in export_annotations:
                annotation, _, new_name = annotation.partition(" as ")
                param_value = registry.expand_variables(annotation, full_module_name)
                if param.default.is_input:
                    rule.inputs.append(paths.annotation_dir / get_annotation_path(param_value))
                if new_name:
                    param_value = " as ".join((param_value, new_name))
                rule.parameters[param_name].append(param_value)
        # Corpus
        elif param.default == Corpus or isinstance(param.default, Corpus):
            rule.parameters[param_name] = sparv_config.get("metadata.id")
        # Language
        elif param.default == Language or isinstance(param.default, Language):
            rule.parameters[param_name] = sparv_config.get("metadata.language")
        # Document
        elif param.default == Document or isinstance(param.default, Document):
            rule.docs.append(param_name)
        # AllDocuments (all source documents)
        elif registry.dig(AllDocuments, param.default):
            rule.parameters[param_name] = get_source_files(storage.source_files)
        # Model
        elif registry.dig(Model, param.default):
            if param.default is not None:
                if isinstance(param.default, Model):
                    model = util.get_model_path(registry.expand_variables(param.default, full_module_name))
                    rule.inputs.append(model)
                    rule.parameters[param_name] = str(model)
                elif isinstance(param.default, (list, tuple)):
                    rule.parameters[param_name] = []
                    for model in param.default:
                        model = util.get_model_path(registry.expand_variables(model, full_module_name))
                        rule.inputs.append(model)
                        rule.parameters[param_name].append(str(model))
        # Binary
        elif isinstance(param.default, Binary):
            binary = paths.get_bin_path(registry.expand_variables(param.default, full_module_name))
            rule.inputs.append(binary)
            rule.parameters[param_name] = str(binary)
        # Source
        elif param.default == Source or isinstance(param.default, Source):
            rule.parameters[param_name] = get_source_path()
        # Export
        elif param.default == Export or isinstance(param.default, Export):
            param_value = registry.expand_variables(param.default, full_module_name)
            if param.default.absolute_path:
                export_path = Path(param_value)
            else:
                export_path = paths.export_dir / param_value
            rule.outputs.append(export_path)
            rule.parameters[param_name] = str(export_path)
            if "{doc}" in rule.parameters[param_name]:
                rule.doc_annotations.append(param_name)
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
        # ExportInput
        elif isinstance(param.default, ExportInput):
            if param.default.absolute_path:
                rule.parameters[param_name] = registry.expand_variables(param.default, full_module_name)
            else:
                rule.parameters[param_name] = str(paths.export_dir / registry.expand_variables(param.default,
                                                                                               full_module_name))
            if param.default.all_docs:
                rule.inputs.extend(expand(escape_wildcards(rule.parameters[param_name]),
                                          doc=get_source_files(storage.source_files)))
            else:
                rule.inputs.append(rule.parameters[param_name])
            if "{" in rule.parameters[param_name]:
                rule.wildcard_annotations.append(param_name)
        # Config
        elif isinstance(param.default, Config):
            rule.parameters[param_name] = sparv_config.get(param.default, param.default.default)
        # Everything else with a default value
        elif param.default is not None:
            rule.parameters[param_name] = param.default

    if config.get("debug"):
        print("    " + util.Color.BOLD + "INPUTS" + util.Color.RESET)
        for i in rule.inputs:
            print("        {}".format(i))
        print()
        print("    " + util.Color.BOLD + "OUTPUTS" + util.Color.RESET)
        for o in rule.outputs:
            print("        {}".format(o))
        print()
        print("    " + util.Color.BOLD + "PARAMETERS" + util.Color.RESET)
        for p in rule.parameters:
            print("        {} = {!r}".format(p, rule.parameters[p]))
        print()
        print()

    return rule


def add_to_storage(storage, rule_params, annotator_info):
    """Add info to snake storage."""
    if rule_params.exporter:
        storage.export_targets.append((rule_params.target_name, rule_params.description,
                                       annotator_info["language"]))
    elif rule_params.installer:
        storage.install_targets.append((rule_params.target_name, rule_params.description))
    elif rule_params.modelbuilder:
        storage.model_targets.append((rule_params.target_name, rule_params.description, annotator_info["language"]))
    else:
        storage.named_targets.append((rule_params.target_name, rule_params.description))


def get_source_path() -> str:
    """Get path to source files."""
    return sparv_config.get("source_dir", paths.source_dir)


def get_annotation_path(annotation, data=False, common=False):
    """Construct a path to an annotation file given a doc and annotation."""
    elem, attr = util.split_annotation(annotation)
    path = Path(elem)

    if not (data or common):
        if not attr:
            attr = util.SPAN_ANNOTATION
        path = path / attr

    if not common:
        path = "{doc}" / path
    return path


def get_source_files(source_files) -> List[str]:
    """Get list of all available source files."""
    if not source_files:
        source_files = [f[1][0] for f in snakemake.utils.listfiles(
            Path(get_source_path(), "{file}." + sparv_config.get("source_type", "xml")))]
    return source_files


def prettify_config(in_config):
    """Prettify a yaml config string."""
    import yaml

    class MyDumper(yaml.Dumper):
        """Customized YAML dumper that indents lists."""

        def increase_indent(self, flow=False, indentless=False):
            """Force indentation."""
            return super(MyDumper, self).increase_indent(flow, False)

    yaml_str = yaml.dump(in_config, default_flow_style=False, Dumper=MyDumper, indent=4)
    # Colorize keys for easier reading
    yaml_str = re.sub(r"^(\s*[\S]+):", util.Color.BLUE + r"\1" + util.Color.RESET + ":", yaml_str,
                      flags=re.MULTILINE)
    return yaml_str


def escape_wildcards(s):
    """Escape all wildcards other than {doc}."""
    return re.sub(r"(?!{doc})({[^}]+})", r"{\1}", str(s))


def get_doc_value(wildcards, annotator):
    """Extract the {doc} part from full annotation path."""
    doc = None
    if hasattr(wildcards, "doc"):
        if annotator:
            doc = wildcards.doc[len(str(paths.annotation_dir)) + 1:]
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
        sparv_config.config["metadata"]["language"] = snakemake_config["language"]

    return config_missing


def get_install_targets(install_outputs):
    """Collect files to be created for all installations listed in config.install."""
    install_inputs = []
    for installation in sparv_config.get("korp.install", []):
        install_inputs.extend(install_outputs[installation])
    return install_inputs
