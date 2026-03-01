"""Export annotated corpus data to pretty-printed xml."""

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
    HeaderAnnotations,
    MarkerOptional,
    Namespaces,
    OutputMarker,
    SourceAnnotations,
    SourceFilename,
    exporter,
    get_logger,
    installer,
    uninstaller,
    util,
)

from . import xml_utils

logger = get_logger(__name__)


@exporter("XML export with one token element per line")
def pretty(
    source_file: SourceFilename = SourceFilename(),
    fileid: AnnotationData = AnnotationData("<fileid>"),
    out: Export = Export("xml_export.pretty/[xml_export.filename]"),
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("[export.word]"),
    annotations: ExportAnnotations = ExportAnnotations("xml_export.annotations"),
    source_annotations: SourceAnnotations = SourceAnnotations("xml_export.source_annotations"),
    header_annotations: HeaderAnnotations = HeaderAnnotations("xml_export.header_annotations"),
    remove_namespaces: bool = Config("export.remove_module_namespaces", False),
    sparv_namespace: str = Config("export.sparv_namespace"),
    source_namespace: str = Config("export.source_namespace"),
    include_empty_attributes: bool = Config("xml_export.include_empty_attributes"),
) -> None:
    """Export annotations to pretty XML in export_dir.

    Args:
        source_file: Name of the source file.
        fileid: Annotation with file IDs.
        out: Path and filename pattern for resulting file.
        token: Annotation containing the token strings.
        word: Annotation containing the token strings.
        annotations: List of elements:attributes (annotations) to include.
        source_annotations: List of elements:attributes from the source file
            to be kept. If not specified, everything will be kept.
        header_annotations: List of header elements from the source file to include
            in the export. If not specified, all headers will be kept.
        remove_namespaces: Whether to remove module "namespaces" from element and attribute names.
            Disabled by default.
        sparv_namespace: The namespace to be added to all Sparv annotations.
        source_namespace: The namespace to be added to all annotations present in the source.
        include_empty_attributes: Whether to include attributes even when they are empty. Disabled by default.
    """
    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    token_name = token.name

    # Read words, file ID and XML namespaces
    word_annotation = list(word.read())
    fileid_annotation = fileid.read()
    xml_namespaces = Namespaces(source_file).read()

    # Get annotation spans, annotations list etc.
    annotation_list, _, export_names = util.export.get_annotation_names(
        annotations,
        source_annotations,
        source_file=source_file,
        token_name=token_name,
        remove_namespaces=remove_namespaces,
        sparv_namespace=sparv_namespace,
        source_namespace=source_namespace,
        xml_mode=True,
    )
    if token not in annotation_list:
        logger.warning(
            "The 'xml_export:pretty' export requires the <token> annotation for the output to include the "
            "source text. Make sure to add <token> to the list of export annotations."
        )
    h_annotations, h_export_names = util.export.get_header_names(header_annotations, xml_namespaces)
    export_names.update(h_export_names)
    xml_utils.replace_invalid_chars_in_names(export_names)
    span_positions, annotation_dict = util.export.gather_annotations(
        annotation_list, export_names, h_annotations, source_file=source_file, split_overlaps=True
    )
    xmlstr = xml_utils.make_pretty_xml(
        span_positions,
        annotation_dict,
        export_names,
        token_name,
        word_annotation,
        fileid_annotation,
        include_empty_attributes,
        sparv_namespace,
        xml_namespaces,
    )

    # Write XML to file
    with out_path.open(mode="w", encoding="utf-8") as outfile:
        print(xmlstr, file=outfile)  # Use print() to get a newline at the end of the file
    logger.info("Exported: %s", out)


@exporter(
    "Combined XML export (all results in one file)",
    config=[
        Config(
            "xml_export.filename_combined",
            default="[metadata.id].xml",
            description="Filename of resulting combined XML.",
            datatype=str,
        ),
        Config(
            "xml_export.include_version_info",
            default=True,
            description="Whether to include annotation version info in the combined XML.",
            datatype=bool,
        ),
    ],
)
def combined(
    corpus: Corpus = Corpus(),
    out: Export = Export("xml_export.combined/[xml_export.filename_combined]"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    xml_input: ExportInput = ExportInput("xml_export.pretty/[xml_export.filename]", all_files=True),
    version_info: ExportInput = ExportInput("version_info/info_[metadata.id].yaml"),
    include_version_info: bool = Config("xml_export.include_version_info"),
) -> None:
    """Combine XML export files into a single XML file.

    Args:
        corpus: The corpus name.
        out: Path and filename pattern for resulting file.
        source_files: Names of all source files to be included in the export.
        xml_input: Input XML filename pattern.
        version_info: Version info input file.
        include_version_info: Whether to include annotation version info in the combined XML.
    """
    xml_utils.combine(corpus, out, source_files, xml_input, version_info if include_version_info else None)


@exporter(
    "Compressed combined XML export",
    config=[
        Config(
            "xml_export.filename_compressed",
            default="[metadata.id].xml.bz2",
            description="Filename of resulting compressed combined XML.",
            datatype=str,
        )
    ],
)
def compressed(
    corpus: Corpus = Corpus(),
    out: Export = Export("xml_export.combined/[xml_export.filename_compressed]"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    xml_input: ExportInput = ExportInput("xml_export.pretty/[xml_export.filename]", all_files=True),
    version_info: ExportInput = ExportInput("version_info/info_[metadata.id].yaml"),
    include_version_info: bool = Config("xml_export.include_version_info"),
) -> None:
    """Compress combined XML export.

    Args:
        corpus: The corpus name.
        out: Path and filename pattern for resulting file.
        source_files: Names of all source files to be included in the export.
        xml_input: Input XML filename pattern.
        version_info: Version info input file.
        include_version_info: Whether to include annotation version info in the combined XML.
    """
    xml_utils.combine(corpus, out, source_files, xml_input, version_info if include_version_info else None, True)


@installer(
    "Copy compressed XML to a target path, optionally on a remote host",
    config=[
        Config("xml_export.export_host", description="Remote host to copy XML export to", datatype=str),
        Config("xml_export.export_path", description="Target path to copy XML export to", datatype=str),
    ],
    uninstaller="xml_export:uninstall",
)
def install(
    corpus: Corpus = Corpus(),
    bz2file: ExportInput = ExportInput("xml_export.combined/[xml_export.filename_compressed]"),
    marker: OutputMarker = OutputMarker("xml_export.install_export_pretty_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("xml_export.uninstall_export_pretty_marker"),
    export_path: str = Config("xml_export.export_path"),
    host: str | None = Config("xml_export.export_host"),
) -> None:
    """Copy compressed XML to a target path, optionally on a remote host.

    Args:
        corpus: The corpus name.
        bz2file: The compressed XML file to copy.
        marker: Marker for the installation process.
        uninstall_marker: Marker for the uninstallation process to remove.
        export_path: The target path to copy the XML export to.
        host: The optional remote host to copy the XML export to.
    """
    xml_utils.install_compressed_xml(corpus, bz2file, marker, export_path, host)
    uninstall_marker.remove()


@uninstaller("Remove compressed XML from remote location")
def uninstall(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("xml_export.uninstall_export_pretty_marker"),
    install_marker: MarkerOptional = MarkerOptional("xml_export.install_export_pretty_marker"),
    export_path: str = Config("xml_export.export_path"),
    host: str | None = Config("xml_export.export_host"),
) -> None:
    """Remove compressed XML from remote location.

    Args:
        corpus: The corpus name.
        marker: Marker for the installation process to remove.
        install_marker: Marker for the uninstallation process.
        export_path: The remote path from which to remove the XML export.
        host: The optional remote host from which to remove the XML export.
    """
    xml_utils.uninstall_compressed_xml(corpus, marker, export_path, host)
    install_marker.remove()
