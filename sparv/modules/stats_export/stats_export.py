"""Build word frequency list."""

import csv
import os.path
from collections import defaultdict
from typing import Optional

from sparv.api import (
    AllSourceFilenames,
    Annotation,
    AnnotationAllSourceFiles,
    Config,
    Corpus,
    Export,
    ExportAnnotationsAllSourceFiles,
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

logger = get_logger(__name__)


@exporter("Corpus word frequency list")
def freq_list(source_files: AllSourceFilenames = AllSourceFilenames(),
              word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[export.word]"),
              token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
              annotations: ExportAnnotationsAllSourceFiles =
                  ExportAnnotationsAllSourceFiles("stats_export.annotations"),
              source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles(
                  "stats_export.source_annotations"),
              remove_namespaces: bool = Config("export.remove_module_namespaces", True),
              sparv_namespace: str = Config("export.sparv_namespace"),
              source_namespace: str = Config("export.source_namespace"),
              out: Export = Export("stats_export.frequency_list/stats_[metadata.id].csv"),
              delimiter: str = Config("stats_export.delimiter"),
              cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for the entire corpus.

    Args:
        source_files: The source files belonging to this corpus.
        word: Word annotations.
        token: Token span annotations.
        annotations: All automatic annotations to include in the export.
        source_annotations: All source annotations to include in the export. If left empty, none will be included.
        remove_namespaces: Whether to remove module "namespaces" from element and attribute names.
        sparv_namespace: The namespace to be added to all Sparv annotations.
        source_namespace: The namespace to be added to all annotations present in the source.
        out: The output word frequency file.
        delimiter: Column delimiter to use in the csv.
        cutoff: The minimum frequency a word must have in order to be included in the result.
    """
    # Add "word" to annotations
    annotations = [(word, None)] + annotations

    # Get annotations list and export names
    annotation_list, token_attributes, export_names = util.export.get_annotation_names(
        annotations, source_annotations or [], source_files=source_files, token_name=token.name,
        remove_namespaces=remove_namespaces, sparv_namespace=sparv_namespace, source_namespace=source_namespace)

    # Get all token and struct annotations (except the span annotations)
    token_annotations = [a for a in annotation_list if a.attribute_name in token_attributes]
    struct_annotations = [a for a in annotation_list if ":" in a.name and a.attribute_name not in token_attributes]

    # Calculate token frequencies
    freq_dict = defaultdict(int)
    for source_file in source_files:
        # Get values for struct annotations (per token)
        struct_values = []
        for struct_annotation in struct_annotations:
            struct_annot = Annotation(struct_annotation.name, source_file=source_file)
            token_parents = Annotation(token.name, source_file=source_file).get_parents(struct_annot)
            try:
                struct_annot_list = list(struct_annot.read())
                struct_values.append([struct_annot_list[p] if p is not None else "" for p in token_parents])
            # Handle cases where some source files are missing structural source annotations
            except FileNotFoundError:
                struct_values.append(["" for _ in token_parents])

        # Create tuples with annotations for each token and count frequencies
        tokens = word.read_attributes(source_file, token_annotations)
        for n, token_annotations_tuple in enumerate(tokens):
            structs_tuple = tuple([struct[n] for struct in struct_values])
            freq_dict[token_annotations_tuple + structs_tuple] += 1

    # Create header
    struct_header_names = [export_names.get(a.annotation_name, a.annotation_name) + ":" + export_names[a.name]
                           for a in struct_annotations]
    column_names = [export_names[a.name] for a in token_annotations] + struct_header_names
    column_names.append("count")

    write_csv(out, column_names, freq_dict, delimiter, cutoff)


@installer("Install word frequency list on remote host", uninstaller="stats_export:uninstall_freq_list")
def install_freq_list(
    freq_list: ExportInput = ExportInput("stats_export.frequency_list/stats_[metadata.id].csv"),
    marker: OutputMarker = OutputMarker("stats_export.install_freq_list_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("stats_export.uninstall_freq_list_marker"),
    host: Optional[str] = Config("stats_export.remote_host"),
    target_dir: str = Config("stats_export.remote_dir")
):
    """Install frequency list on server by rsyncing."""
    util.install.install_path(freq_list, host, target_dir)
    uninstall_marker.remove()
    marker.write()


@uninstaller("Uninstall word frequency list")
def uninstall_freq_list(
    corpus_id: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("stats_export.uninstall_freq_list_marker"),
    install_marker: MarkerOptional = MarkerOptional("stats_export.install_freq_list_marker"),
    host: Optional[str] = Config("stats_export.remote_host"),
    remote_dir: str = Config("stats_export.remote_dir")
):
    """Uninstall word frequency list."""
    remote_file = os.path.join(remote_dir, f"stats_{corpus_id}.csv")
    logger.info(f"Removing word frequency file {host + ':' if host else ''}{remote_file}")
    util.install.uninstall_path(remote_file, host)
    install_marker.remove()
    marker.write()


################################################################################
# Auxiliaries
################################################################################

def write_csv(out, column_names, freq_dict, delimiter, cutoff):
    """Write csv file."""
    with open(out, "w", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=delimiter)
        csv_writer.writerow(column_names)
        for annotations, freq in sorted(freq_dict.items(), key=lambda x: -x[1]):
            if cutoff and cutoff > freq:
                break
            csv_writer.writerow(list(annotations) + [freq])
    logger.info("Exported: %s", out)
