"""Export annotated corpus data to scrambled xml."""

import os

from sparv.api import (AllSourceFilenames, Annotation, AnnotationData, Config, Corpus, Export, ExportAnnotations,
                       ExportInput, Namespaces, OutputCommonData, SourceAnnotations, SourceFilename, SparvErrorMessage,
                       exporter, get_logger, installer, util)
from . import xml_utils

logger = get_logger(__name__)


@exporter("Scrambled XML export", config=[
    Config("xml_export.scramble_on", description="Annotation to use for scrambling.")
])
def scrambled(source_file: SourceFilename = SourceFilename(),
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
              include_empty_attributes: bool = Config("xml_export.include_empty_attributes")):
    """Export annotations to scrambled XML."""
    # Read words, file ID and XML namespaces
    word_annotation = list(word.read())
    chunk_order = list(chunk_order.read())
    fileid_annotation = fileid.read()
    xml_namespaces = Namespaces(source_file).read()

    # Get annotation spans, annotations list etc.
    annotation_list, _, export_names = util.export.get_annotation_names(annotations, source_annotations,
                                                                        source_file=source_file,
                                                                        token_name=token.name,
                                                                        remove_namespaces=remove_namespaces,
                                                                        sparv_namespace=sparv_namespace,
                                                                        source_namespace=source_namespace,
                                                                        xml_mode=True)
    if token not in annotation_list:
        logger.warning("The 'xml_export:scrambled' export requires the <token> annotation for the output to include "
                       "the source text. Make sure to add <token> to the list of export annotations.")
    if chunk not in annotation_list:
        raise SparvErrorMessage(
            "The annotation used for scrambling ({}) needs to be included in the output.".format(chunk))
    span_positions, annotation_dict = util.export.gather_annotations(annotation_list, export_names,
                                                                     source_file=source_file, split_overlaps=True)

    # Reorder chunks
    new_span_positions = util.export.scramble_spans(span_positions, chunk.name, chunk_order)

    # Construct XML string
    xmlstr = xml_utils.make_pretty_xml(new_span_positions, annotation_dict, export_names, token.name, word_annotation,
                                       fileid_annotation, include_empty_attributes, sparv_namespace, xml_namespaces)

    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Write XML to file
    with open(out, mode="w", encoding="utf-8") as outfile:
        outfile.write(xmlstr)
    logger.info("Exported: %s", out)


@exporter("Combined scrambled XML export")
def combined_scrambled(corpus: Corpus = Corpus(),
                       out: Export = Export("xml_export.combined_scrambled/[metadata.id]_scrambled.xml"),
                       source_files: AllSourceFilenames = AllSourceFilenames(),
                       xml_input: ExportInput = ExportInput("xml_export.scrambled/[xml_export.filename]",
                                                            all_files=True),
                       version_info: ExportInput = ExportInput("version_info/info_[metadata.id].yaml"),
                       include_version_info: bool = Config("xml_export.include_version_info")):
    """Combine XML export files into a single XML file."""
    if include_version_info:
        xml_utils.combine(corpus, out, source_files, xml_input, version_info)
    else:
        xml_utils.combine(corpus, out, source_files, xml_input)


@exporter("Compressed combined scrambled XML export")
def compressed_scrambled(out: Export = Export("xml_export.combined_scrambled/[metadata.id]_scrambled.xml.bz2"),
                         xmlfile: ExportInput = ExportInput(
                             "xml_export.combined_scrambled/[metadata.id]_scrambled.xml")):
    """Compress combined XML export."""
    xml_utils.compress(xmlfile, out)


@installer("Copy compressed scrambled XML to remote host", config=[
    Config("xml_export.export_scrambled_host", "", description="Remote host to copy scrambled XML export to"),
    Config("xml_export.export_scrambled_path", "", description="Path on remote host to copy scrambled XML export to")
])
def install_scrambled(corpus: Corpus = Corpus(),
                      bz2file: ExportInput = ExportInput(
                          "xml_export.combined_scrambled/[metadata.id]_scrambled.xml.bz2"),
                      out: OutputCommonData = OutputCommonData("xml_export.install_export_scrambled_marker"),
                      export_path: str = Config("xml_export.export_scrambled_path"),
                      host: str = Config("xml_export.export_scrambled_host")):
    """Copy compressed combined scrambled XML to remote host."""
    xml_utils.install_compressed_xml(corpus, bz2file, out, export_path, host)
