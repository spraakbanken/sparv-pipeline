"""Export annotated corpus data to scrambled xml."""

from pathlib import Path

from sparv.api import (
    AllSourceFilenames,
    Annotation,
    AnnotationData,
    Config,
    Corpus,
    Export,
    ExportAnnotations,
    ExportInput,
    MarkerOptional,
    Namespaces,
    OutputMarker,
    SourceAnnotations,
    SourceFilename,
    SparvErrorMessage,
    exporter,
    get_logger,
    installer,
    uninstaller,
    util,
)

from . import xml_utils

logger = get_logger(__name__)


@exporter(
    "Scrambled XML export",
    config=[Config("xml_export.scramble_on", description="Annotation to use for scrambling.", datatype=str)],
)
def scrambled(
    source_file: SourceFilename = SourceFilename(),
    fileid: AnnotationData = AnnotationData("<fileid>"),
    out: Export = Export("xml_export.scrambled/[xml_export.filename]"),
    chunk: Annotation = Annotation("[xml_export.scramble_on]"),
    chunk_order: Annotation = Annotation("[xml_export.scramble_on]:misc.number_random"),
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("[export.word]"),
    annotations: ExportAnnotations = ExportAnnotations("xml_export.annotations"),
    source_annotations: SourceAnnotations = SourceAnnotations("xml_export.source_annotations"),
    remove_namespaces: bool = Config("export.remove_module_namespaces", False),
    sparv_namespace: str = Config("export.sparv_namespace"),
    source_namespace: str = Config("export.source_namespace"),
    include_empty_attributes: bool = Config("xml_export.include_empty_attributes"),
) -> None:
    """Export annotations to scrambled XML.

    Args:
        source_file: The source file to export.
        fileid: The file ID annotation.
        out: The output file path and pattern.
        chunk: The annotation to use for scrambling.
        chunk_order: The annotation to use for the order of the scrambled chunks.
        token: The token annotation.
        word: The word annotation.
        annotations: The annotations to export.
        source_annotations: The source annotations to export.
        remove_namespaces: Whether to remove namespaces from the output XML.
        sparv_namespace: The namespace for Sparv annotations.
        source_namespace: The namespace for source annotations.
        include_empty_attributes: Whether to include empty attributes in the output XML.

    Raises:
        SparvErrorMessage: If the chunk annotation is not included in the output.
    """
    # Read words, file ID and XML namespaces
    word_annotation = list(word.read())
    chunk_order = list(chunk_order.read())
    fileid_annotation = fileid.read()
    xml_namespaces = Namespaces(source_file).read()

    # Get annotation spans, annotations list etc.
    annotation_list, _, export_names = util.export.get_annotation_names(
        annotations,
        source_annotations,
        source_file=source_file,
        token_name=token.name,
        remove_namespaces=remove_namespaces,
        sparv_namespace=sparv_namespace,
        source_namespace=source_namespace,
        xml_mode=True,
    )
    if token not in annotation_list:
        logger.warning(
            "The 'xml_export:scrambled' export requires the <token> annotation for the output to include "
            "the source text. Make sure to add <token> to the list of export annotations."
        )
    if chunk not in annotation_list:
        raise SparvErrorMessage(f"The annotation used for scrambling ({chunk}) needs to be included in the output.")
    xml_utils.replace_invalid_chars_in_names(export_names)
    span_positions, annotation_dict = util.export.gather_annotations(
        annotation_list, export_names, source_file=source_file, split_overlaps=True
    )

    # Reorder chunks
    new_span_positions = util.export.scramble_spans(span_positions, chunk.name, chunk_order)

    # If the scrambled document contains no text, export a document containing just the root node and nothing else (we
    # need to produce a file, and an empty file would be invalid XML).
    # Alternatively, we could export the original (span_positions), but then any text outside the scramble_on chunks
    # would be included, unscrambled, and we don't want to risk that.
    if not new_span_positions:
        logger.warning("%r contains no text after scrambling (using the annotation %r)", source_file, chunk.name)
        new_span_positions = [span_positions[0], span_positions[-1]]

    # Construct XML string
    xmlstr = xml_utils.make_pretty_xml(
        new_span_positions,
        annotation_dict,
        export_names,
        token.name,
        word_annotation,
        fileid_annotation,
        include_empty_attributes,
        sparv_namespace,
        xml_namespaces,
    )

    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write XML to file
    with out_path.open(mode="w", encoding="utf-8") as outfile:
        print(xmlstr, file=outfile)  # Use print() to get a newline at the end of the file
    logger.info("Exported: %s", out)


@exporter("Combined scrambled XML export")
def combined_scrambled(
    corpus: Corpus = Corpus(),
    out: Export = Export("xml_export.combined_scrambled/[metadata.id]_scrambled.xml"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    xml_input: ExportInput = ExportInput("xml_export.scrambled/[xml_export.filename]", all_files=True),
    version_info: ExportInput = ExportInput("version_info/info_[metadata.id].yaml"),
    include_version_info: bool = Config("xml_export.include_version_info"),
) -> None:
    """Combine XML export files into a single XML file.

    Args:
        corpus: The corpus to export.
        out: The output file path and pattern.
        source_files: The source files to include in the export.
        xml_input: The input XML files to combine.
        version_info: The version info file to include in the export.
        include_version_info: Whether to include version info in the output XML.
    """
    xml_utils.combine(corpus, out, source_files, xml_input, version_info if include_version_info else None)


@exporter("Compressed combined scrambled XML export")
def compressed_scrambled(
    corpus: Corpus = Corpus(),
    out: Export = Export("xml_export.combined_scrambled/[metadata.id]_scrambled.xml.bz2"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    xml_input: ExportInput = ExportInput("xml_export.scrambled/[xml_export.filename]", all_files=True),
    version_info: ExportInput = ExportInput("version_info/info_[metadata.id].yaml"),
    include_version_info: bool = Config("xml_export.include_version_info"),
) -> None:
    """Compress combined XML export.

    Args:
        corpus: The corpus to export.
        out: The output file path and pattern.
        source_files: The source files to include in the export.
        xml_input: The input XML files to combine.
        version_info: The version info file to include in the export.
        include_version_info: Whether to include version info in the output XML.
    """
    xml_utils.combine(corpus, out, source_files, xml_input, version_info if include_version_info else None, True)


@installer(
    "Copy compressed scrambled XML to a target path, optionally on a remote host",
    config=[
        Config(
            "xml_export.export_scrambled_host", description="Remote host to copy scrambled XML export to", datatype=str
        ),
        Config(
            "xml_export.export_scrambled_path", description="Target path to copy scrambled XML export to", datatype=str
        ),
    ],
    uninstaller="xml_export:uninstall_scrambled",
)
def install_scrambled(
    corpus: Corpus = Corpus(),
    bz2file: ExportInput = ExportInput("xml_export.combined_scrambled/[metadata.id]_scrambled.xml.bz2"),
    marker: OutputMarker = OutputMarker("xml_export.install_export_scrambled_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("xml_export.uninstall_export_scrambled_marker"),
    export_path: str = Config("xml_export.export_scrambled_path"),
    host: str | None = Config("xml_export.export_scrambled_host"),
) -> None:
    """Copy compressed combined scrambled XML to a target path, optionally on a remote host.

    Args:
        corpus: The corpus name.
        bz2file: The input XML file to copy.
        marker: The output marker for the installation.
        uninstall_marker: The output marker for the uninstallation to be removed.
        export_path: The target path to copy the XML export to.
        host: The optional remote host to copy the XML export to.
    """
    xml_utils.install_compressed_xml(corpus, bz2file, marker, export_path, host)
    uninstall_marker.remove()


@uninstaller("Remove compressed scrambled XML from remote location")
def uninstall_scrambled(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("xml_export.uninstall_export_scrambled_marker"),
    install_marker: MarkerOptional = MarkerOptional("xml_export.install_export_scrambled_marker"),
    export_path: str = Config("xml_export.export_scrambled_path"),
    host: str | None = Config("xml_export.export_scrambled_host"),
) -> None:
    """Remove compressed XML from remote location.

    Args:
        corpus: The corpus name.
        marker: The output marker for the uninstallation.
        install_marker: The output marker for the installation to be removed.
        export_path: The path to the XML export to remove.
        host: The optional remote host to remove the XML export from.
    """
    xml_utils.uninstall_compressed_xml(corpus, marker, export_path, host)
    install_marker.remove()
