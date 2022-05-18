"""Export annotated corpus data to pretty-printed xml."""

import os

from sparv.api import (AllSourceFilenames, Annotation, AnnotationData, Config, Corpus, Export, ExportAnnotations,
                       ExportInput, Namespaces, OutputCommonData, SourceAnnotations, SourceFilename, exporter,
                       get_logger, installer, util)

from . import xml_utils

logger = get_logger(__name__)


@exporter("XML export with one token element per line", config=[
    Config("xml_export.filename", default="{file}_export.xml",
           description="Filename pattern for resulting XML files, with '{file}' representing the source name."),
    Config("xml_export.annotations", description="Sparv annotations to include."),
    Config("xml_export.source_annotations",
           description="List of annotations and attributes from the source data to include. Everything will be "
                       "included by default."),
    Config("xml_export.header_annotations",
           description="List of headers from the source data to include. All headers will be included by default."),
    Config("xml_export.include_empty_attributes", False,
           description="Whether to include attributes even when they are empty.")
])
def pretty(source_file: SourceFilename = SourceFilename(),
           fileid: AnnotationData = AnnotationData("<fileid>"),
           out: Export = Export("xml_export.pretty/[xml_export.filename]"),
           token: Annotation = Annotation("<token>"),
           word: Annotation = Annotation("[export.word]"),
           annotations: ExportAnnotations = ExportAnnotations("xml_export.annotations"),
           source_annotations: SourceAnnotations = SourceAnnotations("xml_export.source_annotations"),
           header_annotations: SourceAnnotations = SourceAnnotations("xml_export.header_annotations"),
           remove_namespaces: bool = Config("export.remove_module_namespaces", False),
           sparv_namespace: str = Config("export.sparv_namespace"),
           source_namespace: str = Config("export.source_namespace"),
           include_empty_attributes: bool = Config("xml_export.include_empty_attributes")):
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
    os.makedirs(os.path.dirname(out), exist_ok=True)

    token_name = token.name

    # Read words, file ID and XML namespaces
    word_annotation = list(word.read())
    fileid_annotation = fileid.read()
    xml_namespaces = Namespaces(source_file).read()

    # Get annotation spans, annotations list etc.
    annotation_list, _, export_names = util.export.get_annotation_names(annotations, source_annotations, source_file=source_file,
                                                                        token_name=token_name,
                                                                        remove_namespaces=remove_namespaces,
                                                                        sparv_namespace=sparv_namespace,
                                                                        source_namespace=source_namespace,
                                                                        xml_mode=True)
    if token not in annotation_list:
        logger.warning("The 'xml_export:pretty' export requires the <token> annotation for the output to include the "
                       "source text. Make sure to add <token> to the list of export annotations.")
    h_annotations, h_export_names = util.export.get_header_names(header_annotations, source_file=source_file)
    export_names.update(h_export_names)
    span_positions, annotation_dict = util.export.gather_annotations(annotation_list, export_names, h_annotations,
                                                                     source_file=source_file, split_overlaps=True)
    xmlstr = xml_utils.make_pretty_xml(span_positions, annotation_dict, export_names, token_name, word_annotation,
                                       fileid_annotation, include_empty_attributes, sparv_namespace, xml_namespaces)

    # Write XML to file
    with open(out, mode="w", encoding="utf-8") as outfile:
        outfile.write(xmlstr)
    logger.info("Exported: %s", out)


@exporter("Combined XML export (all results in one file)", config=[
    Config("xml_export.filename_combined", default="[metadata.id].xml",
           description="Filename of resulting combined XML."),
    Config("xml_export.include_version_info", default=True,
           description="Whether to include annotation version info in the combined XML.")
])
def combined(corpus: Corpus = Corpus(),
             out: Export = Export("xml_export.combined/[xml_export.filename_combined]"),
             source_files: AllSourceFilenames = AllSourceFilenames(),
             xml_input: ExportInput = ExportInput("xml_export.pretty/[xml_export.filename]", all_files=True),
             version_info: ExportInput = ExportInput("version_info/info_[metadata.id].yaml"),
             include_version_info: bool = Config("xml_export.include_version_info")):
    """Combine XML export files into a single XML file."""
    if include_version_info:
        xml_utils.combine(corpus, out, source_files, xml_input, version_info)
    else:
        xml_utils.combine(corpus, out, source_files, xml_input)


@exporter("Compressed combined XML export", config=[
    Config("xml_export.filename_compressed", default="[metadata.id].xml.bz2",
           description="Filename of resulting compressed combined XML.")
])
def compressed(out: Export = Export("xml_export.combined/[xml_export.filename_compressed]"),
               xmlfile: ExportInput = ExportInput("xml_export.combined/[xml_export.filename_combined]")):
    """Compress combined XML export."""
    xml_utils.compress(xmlfile, out)


@installer("Copy compressed XML to remote host", config=[
    Config("xml_export.export_host", "", description="Remote host to copy XML export to."),
    Config("xml_export.export_path", "", description="Path on remote host to copy XML export to.")
])
def install(corpus: Corpus = Corpus(),
            bz2file: ExportInput = ExportInput("xml_export.combined/[xml_export.filename_compressed]"),
            out: OutputCommonData = OutputCommonData("xml_export.install_export_pretty_marker"),
            export_path: str = Config("xml_export.export_path"),
            host: str = Config("xml_export.export_host")):
    """Copy compressed combined XML to remote host."""
    xml_utils.install_compressed_xml(corpus, bz2file, out, export_path, host)
