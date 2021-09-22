"""Build word frequency list (SBX format)."""

import csv
from collections import defaultdict

from sparv.api import (AllSourceFilenames, Annotation, AnnotationAllSourceFiles, Config, Export,
                       ExportAnnotationsAllSourceFiles, ExportInput, OutputCommonData, SourceAnnotations,
                       SparvErrorMessage, exporter, get_logger, installer, util)

logger = get_logger(__name__)


@exporter("Corpus word frequency list")
def freq_list(source_files: AllSourceFilenames = AllSourceFilenames(),
              word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[export.word]"),
              token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
              annotations: ExportAnnotationsAllSourceFiles =
                  ExportAnnotationsAllSourceFiles("stats_export.annotations"),
              source_annotations: SourceAnnotations = SourceAnnotations("stats_export.source_annotations"),
              column_names: list = Config("stats_export.column_names"),
              remove_namespaces: bool = Config("export.remove_module_namespaces", True),
              sparv_namespace: str = Config("export.sparv_namespace"),
              source_namespace: str = Config("export.source_namespace"),
              out: Export = Export("frequency_list/stats_[metadata.id].csv"),
              delimiter: str = Config("stats_export.delimiter"),
              cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for the entire corpus.

    Args:
        source_files (list, optional): The source files belonging to this corpus. Defaults to AllSourceFilenames.
        word (str, optional): Word annotations. Defaults to AnnotationAllSourceFiles("<token:word>").
        token (str, optional): Token span annotations. Defaults to AnnotationAllSourceFiles("<token>").
        annotations (str, optional): All automatic annotations to include in the export. Defaults to
            ExportAnnotationsAllSourceFiles("stats_export.annotations").
        source_annotations (str, optional): All source annotations to include in the export. If left empty, none will be
            included. Defaults to SourceAnnotations("stats_export.source_annotations").
        column_names (list, optional): Optional custom column names that will be printed in the header. First element is
            the token, followed by all token attributes, followed by all structural attributes.
            Defaults to Config("stats_export.column_names").
        remove_namespaces: Whether to remove module "namespaces" from element and attribute names.
            Disabled by default.
        sparv_namespace: The namespace to be added to all Sparv annotations.
        source_namespace: The namespace to be added to all annotations present in the source.
        out (str, optional): The output word frequency file. Defaults to Export("frequency_list/[metadata.id].csv").
        delimiter (str, optional): Column delimiter to use in the csv. Defaults to Config("stats_export.delimiter").
        cutoff (int, optional): The minimum frequency a word must have in order to be included in the result.
            Defaults to Config("stats_export.cutoff").
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

    # Create header
    struct_header_names = [export_names[a.annotation_name] + ":" + export_names[a.name] for a in struct_annotations]
    auto_column_names = [export_names[a.name] for a in token_annotations] + struct_header_names
    if column_names:
        # Check if list of supplied column names has the correct length
        if len(column_names) != len(auto_column_names):
            raise SparvErrorMessage(
                f"The amount of column_names provided ({len(column_names)}) does not match the amount of annotations "
                f"in the stats export ({len(token_annotations) + len(struct_annotations)}). "
                f"The following annotations will be included: {', '.join(auto_column_names)}")
    else:
        column_names = auto_column_names
    column_names.append("count")

    # Calculate token frequencies
    freq_dict = defaultdict(int)
    for source_file in source_files:
        # Get values for struct annotations (per token)
        struct_values = []
        for struct_annotation in struct_annotations:
            struct_annot = Annotation(struct_annotation.name, source_file=source_file)
            token_parents = Annotation(token.name, source_file=source_file).get_parents(struct_annot)
            struct_annot_list = list(struct_annot.read())
            struct_values.append([struct_annot_list[p] if p is not None else "" for p in token_parents])

        # Create tuples with annotations for each token and count frequencies
        tokens = word.read_attributes(source_file, token_annotations)
        for n, token_annotations_tuple in enumerate(tokens):
            structs_tuple = tuple([struct[n] for struct in struct_values])
            freq_dict[token_annotations_tuple + structs_tuple] += 1

    write_csv(out, column_names, freq_dict, delimiter, cutoff)


@installer("Install word frequency list on remote host")
def install_freq_list(freq_list: ExportInput = ExportInput("frequency_list/stats_[metadata.id].csv"),
                      out: OutputCommonData = OutputCommonData("stats_export.install_freq_list_marker"),
                      host: str = Config("stats_export.remote_host"),
                      target_dir: str = Config("stats_export.remote_dir")):
    """Install frequency list on server by rsyncing."""
    util.install.install_file(freq_list, host, target_dir)
    out.write("")


################################################################################
# Auxiliaries
################################################################################

def write_csv(out, column_names, freq_dict, delimiter, cutoff):
    """Write csv file."""
    with open(out, "w") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=delimiter)
        csv_writer.writerow(column_names)
        for annotations, freq in sorted(freq_dict.items(), key=lambda x: -x[1]):
            if cutoff and cutoff > freq:
                break
            csv_writer.writerow(list(annotations) + [freq])
    logger.info("Exported: %s", out)
