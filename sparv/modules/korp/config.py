"""Create configuration files for the Korp backend and frontend."""
import itertools
import subprocess
from pathlib import Path
from typing import Optional, Union, List

import yaml

from sparv.api import (
    AllSourceFilenames,
    AnnotationName,
    Config,
    Corpus,
    Export,
    ExportAnnotationNames,
    ExportInput,
    MarkerOptional,
    OutputMarker,
    SourceAnnotationsAllSourceFiles,
    exporter,
    get_logger,
    installer,
    uninstaller,
    util
)
from sparv.core.io import split_annotation
from sparv.modules.cwb.cwb import cwb_escape

logger = get_logger(__name__)

# Annotations that should not be shown in Korp
HIDDEN_ANNOTATIONS = (
    "<text>:dateformat.datefrom",
    "<text>:dateformat.dateto",
    "<text>:dateformat.timefrom",
    "<text>:dateformat.timeto",
    "<sentence>:misc.id",
    "<token>:sensaldo.sentiment_score",
    "<token>:stanza.msd_hunpos_backoff_info"
)

# Annotations needed by reading mode (using export names)
READING_MODE_ANNOTATIONS = (
    "text:_id",
    "sentence:id",
    "_head",
    "_tail"
)

LABELS = {
    "sentence": {
        "swe": ("mening", "meningar"),
        "eng": ("sentence", "sentences")
    },
    "paragraph": {
        "swe": ("stycke", "stycken"),
        "eng": ("paragraph", "paragraphs")
    }
}


@exporter("Create Korp config file for the corpus.", config=[
    Config("korp.annotations", description="Sparv annotations to include. Leave blank to use cwb.annotations."),
    Config("korp.source_annotations",
           description="List of annotations and attributes from the source data to include. Leave blank to use "
                       "cwb.source_annotations."),
    Config("korp.annotation_definitions", description="Frontend definitions of annotations in 'annotations' and "
                                                      "'source_annotations'. Classes and config keys are currently "
                                                      "not supported."),
    Config("korp.context", description="Contexts to use in Korp, from smaller to bigger. "
                                       "Leave blank to detect automatically."),
    Config("korp.within", description="Search boundaries to use in Korp, from smaller to bigger. "
                                      "Leave blank to detect automatically."),
    Config("korp.custom_annotations", description="Custom Korp-annotations."),
    Config("korp.morphology", description="Morphologies"),
    Config("korp.reading_mode", description="Reading mode configuration"),
    Config("korp.filters", description="List of annotations to use for filtering in Korp"),
    Config("korp.hidden_annotations", description="List of annotations not to include in corpus config",
           default=HIDDEN_ANNOTATIONS)
])
def config(id: Corpus = Corpus(),
           name: dict = Config("metadata.name"),
           description: Optional[dict] = Config("metadata.description"),
           short_description: Optional[dict] = Config("metadata.short_description"),
           language: str = Config("metadata.language"),
           modes: list = Config("korp.modes"),
           protected: bool = Config("korp.protected"),
           annotations: ExportAnnotationNames = ExportAnnotationNames("korp.annotations"),
           source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles(
               "korp.source_annotations"),
           cwb_annotations: ExportAnnotationNames = ExportAnnotationNames("cwb.annotations"),
           cwb_source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles(
               "cwb.source_annotations"),
           annotation_definitions: Optional[dict] = Config("korp.annotation_definitions"),
           custom_annotations: Optional[list] = Config("korp.custom_annotations"),
           morphology: Optional[list] = Config("korp.morphology"),
           reading_mode: Optional[dict] = Config("korp.reading_mode"),
           hidden_annotations: List[AnnotationName] = Config("korp.hidden_annotations"),
           filters: Optional[list] = Config("korp.filters"),
           sentence: Optional[AnnotationName] = AnnotationName("<sentence>"),
           paragraph: Optional[AnnotationName] = AnnotationName("<paragraph>"),
           installations: Optional[list] = Config("install"),
           exports: Optional[list] = Config("export.default"),
           scramble_on: Optional[AnnotationName] = AnnotationName("[cwb.scramble_on]"),
           context: Optional[list] = Config("korp.context"),
           within: Optional[list] = Config("korp.within"),
           source_files: AllSourceFilenames = AllSourceFilenames(),
           token: AnnotationName = AnnotationName("<token>"),
           remove_namespaces: bool = Config("export.remove_module_namespaces", False),
           sparv_namespace: str = Config("export.sparv_namespace"),
           source_namespace: str = Config("export.source_namespace"),
           remote_host: Optional[str] = Config("korp.remote_host"),
           config_dir: str = Config("korp.config_dir"),
           out: Export = Export("korp.config/[metadata.id].yaml")):
    """Create Korp config file for the corpus, to be served by the Korp backend and used by the frontend.

    Args:
        id: Corpus ID.
        name: Corpus name.
        description: Corpus description.
        short_description: Short corpus description.
        language: Corpus language.
        modes: List of modes and folders where the corpus will be available in Korp.
        protected: Whether the corpus is password protected.
        annotations: List of Sparv annotations to include in the config.
        source_annotations: List of source annotations to include in the config.
        cwb_annotations: Sparv annotations in CWB encoded corpus, used unless 'annotations' is set.
        cwb_source_annotations: Source annotations in CWB encoded corpus, used unless 'source_annotations' is set.
        annotation_definitions: Korp frontend definitions of annotations in 'annotations' and 'source_annotations'.
        custom_annotations: Korp frontend 'custom annotations' definitions.
        morphology: List of morphologies used by the corpus.
        reading_mode: Reading mode configuration.
        hidden_annotations: List of annotations to exclude.
        filters: List of annotations to use for filtering in Korp.
        sentence: The sentence annotation.
        paragraph: The paragraph annotation.
        installations: List of installations.
        exports: List of exports.
        scramble_on: Annotation to scramble on.
        context: List of annotations to use for context in the Korp frontend.
        within: List of annotations to use as search boundaries in the Korp frontend.
        source_files: List of source files.
        token: The token annotation.
        remove_namespaces: Remove all namespaces in export_names unless names are ambiguous.
        sparv_namespace: The namespace to be added to all Sparv annotations.
        source_namespace: The namespace to be added to all annotations present in the source.
        remote_host: Host where Korp configuration files are installed.
        config_dir: Path on remote host where Korp configuration files are located.
        out: YAML file to create.
    """
    config_dict = {
        "id": str(id),
        "lang": language,
        "mode": modes
    }
    optional = {
        "description": build_description(description, short_description),
        "title": name,
        "limited_access": protected,
        "custom_attributes": custom_annotations,
        "morphology": morphology,
        "reading_mode": reading_mode
    }

    config_dict.update({k: v for k, v in optional.items() if v})

    # Use CWB annotations if no specific Korp annotations are specified
    # TODO: Doesn't currently work, as annotations/source_annotations already inherits from export.[source_]annotations
    if not annotations:
        annotations = cwb_annotations
    if not source_annotations:
        source_annotations = cwb_source_annotations

    if not annotation_definitions:
        annotation_definitions = {}

    # Get annotation names
    annotation_list, token_attributes, export_names = util.export.get_annotation_names(
        annotations, source_annotations, source_files=source_files, token_name=token.name,
        remove_namespaces=remove_namespaces, sparv_namespace=sparv_namespace, source_namespace=source_namespace,
        keep_struct_names=True)

    # Context and within
    if not within and not context:
        # Figure out based on available annotations and scrambling
        within = []

        anns = set([split_annotation(a[0])[0] for a in itertools.chain(annotations, source_annotations or [])])
        if sentence and sentence.name in anns:
            within.append(export_names[sentence.name])

        if paragraph and paragraph.name in anns:
            # Check installation list or default export to figure out if corpus is scrambled
            scrambled = True
            if installations:
                if "cwb:install_corpus_scrambled" in installations:
                    scrambled = True
                elif "cwb:install_corpus" in installations:
                    scrambled = False
                elif exports:
                    if "cwb:encode_scrambled" in exports:
                        scrambled = True
                    elif "cwb:encode" in exports:
                        scrambled = False
                    else:
                        logger.warning("Couldn't determine if corpus is scrambled. Assuming it is scrambled.")
            if not (scrambled and sentence and scramble_on == sentence):
                within.append(export_names[paragraph.name])

    if within and not context:
        context = [v if isinstance(v, str) else v["value"] for v in within]
    elif context and not within:
        within = [v.split(" ", 1)[1] if isinstance(v, str) else v["value"].split(" ", 1)[1] for v in context]
    elif not within and not context:
        logger.warning("Couldn't figure out 'context' and 'within' automatically. Set at least one of them manually in "
                       "the config.")

    if within:
        config_dict["within"] = []
        for v in within:
            if isinstance(v, str):
                n = 0
                if " " in v:
                    n, _, v = v.partition(" ")
                if v in LABELS:
                    i = 1 if int(n) > 1 else 0
                    label = {lang: f"{n} {val[i]}" if n else val[i] for lang, val in LABELS[v].items()}
                else:
                    label = {"swe": f"{n} {v}" if n else v, "eng": f"{n} {v}" if n else v}
                w = {
                    "value": f"{n} {v}" if n else v,
                    "label": label
                }
            else:
                w = v
            config_dict["within"].append(w)
    if context:
        config_dict["context"] = []
        for v in context:
            if isinstance(v, str):
                n = 1
                if " " in v:
                    n, _, v = v.partition(" ")
                if v in LABELS:
                    i = 1 if int(n) > 1 else 0
                    label = {lang: f"{n} {val[i]}" for lang, val in LABELS[v].items()}
                else:
                    label = {"swe": f"{n} {v}", "eng": f"{n} {v}"}
                c = {
                    "value": f"{n} {v}",
                    "label": label
                }
            else:
                c = v
            config_dict["context"].append(c)

    # Annotations
    presets = get_presets(remote_host, config_dir)
    token_annotations, struct_annotations, _ = build_annotations(annotation_definitions, annotation_list, export_names,
                                                                 hidden_annotations, presets, reading_mode, token)

    config_dict["struct_attributes"] = struct_annotations
    config_dict["pos_attributes"] = token_annotations

    if filters:
        config_dict["attribute_filters"] = []
        for a in filters:
            config_dict["attribute_filters"].append(cwb_escape(export_names[a].replace(":", "_")))

    with open(out, "w", encoding="utf-8") as out_yaml:
        out_yaml.write("# This file was automatically generated by Sparv. Do not make changes directly to this file as "
                       "they will get overwritten.\n")
        out_yaml.write(dict_to_yaml(config_dict))


def build_annotations(annotation_definitions, annotation_list, export_names, hidden_annotations, presets, reading_mode,
                      token, text_annotation=None, cwb_annotations: bool = True):
    token_annotations = []
    struct_annotations = []
    text_annotations = []
    hidden_annotation_names = [a.name for a in hidden_annotations]

    for annotation in annotation_list:
        export_name = export_names.get(annotation.name, annotation.name)
        # Skip certain annotations unless explicitly listed in annotation_definitions
        if (annotation.name in hidden_annotation_names or annotation.attribute_name is None or export_name.split(":", 1)[
                -1].startswith("_")) and annotation.name not in annotation_definitions and not (
            reading_mode and export_name in READING_MODE_ANNOTATIONS
        ):
            logger.debug(f"Skipping annotation {annotation.name!r}")
            continue
        export_name_cwb = cwb_escape(export_name.replace(":", "_"))
        is_token = annotation.annotation_name == token.name
        is_text = text_annotation and annotation.annotation_name == text_annotation
        definition: Union[str, dict] = annotation_definitions.get(annotation.name, export_name_cwb)

        if isinstance(definition, str):  # Referring to a preset
            # Check that preset exists
            if definition not in presets:
                logger.warning(
                    f"{annotation.name!r} is missing a definition, and {definition!r} is not available as a "
                    "preset. Annotation will not be included.")
                continue
            if not is_token and presets[definition] == "positional":
                # Non-token annotation used as a token-annotation in Korp
                is_token = True
        elif "preset" in definition:  # Extending a preset
            if definition["preset"] not in presets:
                logger.warning(f"{annotation.name!r} refers to a non-existent preset. Annotation will not be included.")
                continue
            if not is_token:
                # Check if non-token annotation should be used as a token-annotation in Korp
                if definition.get("use_as_positional") or presets[definition["preset"]] == "positional":
                    is_token = True
                    definition["is_struct_attr"] = True
                    definition.pop("use_as_positional", None)
        elif not is_token:
            # Check if non-token annotation should be used as a token-annotation in Korp
            if definition.get("use_as_positional"):
                is_token = True
                definition["is_struct_attr"] = True
                definition.pop("use_as_positional", None)

        if is_token:
            token_annotations.append({export_name_cwb if cwb_annotations else export_name: definition})
        elif is_text:
            text_annotations.append({export_name_cwb if cwb_annotations else export_name: definition})
        else:
            struct_annotations.append({export_name_cwb if cwb_annotations else export_name: definition})
    return token_annotations, struct_annotations, text_annotations


def get_presets(remote_host, config_dir):
    """Get list of presets from file system."""
    presets = {}
    if remote_host and remote_host != "localhost":
        cmd = ["ssh", remote_host, f"find '{config_dir}/attributes/'"]
    else:
        cmd = ["find", f"{config_dir}/attributes/"]
    logger.debug(f"Getting Korp annotation presets from {remote_host}:{config_dir}")
    s = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,  # TODO: Use capture_output=True when requiring Python 3.7
        stderr=subprocess.PIPE,
        encoding="utf-8"
    )
    if s.returncode == 0:
        for p in s.stdout.splitlines():
            if not p.endswith(".yaml"):
                continue
            atype, name = Path(p).parts[-2:]
            presets[name[:-5]] = atype
    else:
        logger.error(f"Could not fetch list of Korp annotation presets: {s.stderr}")
    return presets


def build_description(description, short_description):
    """Combine description and short_description if they exist."""
    lang_dict = {}
    description = description or {}
    short_description = short_description or {}
    langs = set(list(description.keys()) + list(short_description.keys()))
    for lang in langs:
        descr = None
        if short_description.get(lang) and description.get(lang):
            descr = f"<b>{short_description.get(lang)}</b><br><br>{description.get(lang)}"
        elif description.get(lang):
            descr = description.get(lang)
        elif short_description.get(lang):
            descr = short_description.get(lang)
        if descr:
            lang_dict[lang] = descr
    return lang_dict


@installer("Install Korp corpus configuration file.", uninstaller="korp:uninstall_config")
def install_config(
    remote_host: Optional[str] = Config("korp.remote_host"),
    config_dir: str = Config("korp.config_dir"),
    config_file: ExportInput = ExportInput("korp.config/[metadata.id].yaml"),
    marker: OutputMarker = OutputMarker("korp.install_config_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("korp.uninstall_config_marker")
):
    """Install Korp corpus configuration file."""
    corpus_dir = Path(config_dir) / "corpora"
    logger.info(f"Installing Korp corpus configuration file to {remote_host}:{corpus_dir}")
    util.install.install_path(config_file, remote_host, corpus_dir)
    uninstall_marker.remove()
    marker.write()


@uninstaller("Uninstall Korp corpus configuration file.")
def uninstall_config(
    remote_host: Optional[str] = Config("korp.remote_host"),
    config_dir: str = Config("korp.config_dir"),
    corpus_id: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("korp.uninstall_config_marker"),
    install_marker: MarkerOptional = MarkerOptional("korp.install_config_marker")
):
    """Uninstall Korp corpus configuration file."""
    corpus_file = Path(config_dir) / "corpora" / f"{corpus_id}.yaml"
    logger.info(f"Uninstalling Korp corpus configuration file from {remote_host + ':' if remote_host else ''}"
                f"{corpus_file}")
    util.install.uninstall_path(corpus_file, host=remote_host)
    install_marker.remove()
    marker.write()


def dict_to_yaml(data):
    """Convert dict to YAML string.

    Args:
        data: The dict to be converted.
    """
    class IndentDumper(yaml.Dumper):
        """Customized YAML dumper that indents lists."""

        def increase_indent(self, flow=False, indentless=False):
            """Force indentation."""
            return super(IndentDumper, self).increase_indent(flow)

    # Add custom string representer for prettier multiline strings
    def str_representer(dumper, data):
        if len(data.splitlines()) > 1:  # Check for multiline string
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)
    yaml.add_representer(str, str_representer)

    return yaml.dump(data, sort_keys=False, allow_unicode=True, Dumper=IndentDumper, indent=4,
                     default_flow_style=False)
