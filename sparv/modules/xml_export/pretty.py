"""Export annotated corpus data to pretty-printed xml."""

import logging
import os

import sparv.util as util
from sparv import (AllDocuments, Annotation, AnnotationData, Config, Corpus, Document, Export, ExportAnnotations,
                   ExportInput, OutputCommonData, SourceAnnotations, exporter, installer)
from . import xml_utils

log = logging.getLogger(__name__)


@exporter("XML export with one token element per line", config=[
    Config("xml_export.filename", default="{doc}_export.xml",
           description="Filename pattern for resulting XML files, with '{doc}' representing the source name."),
    Config("xml_export.annotations", description="Sparv annotations to include."),
    Config("xml_export.source_annotations",
           description="List of annotations and attributes from the source data to include. Everything will be "
                       "included by default."),
    Config("xml_export.header_annotations",
           description="List of headers from the source data to include. All headers will be included by default."),
    Config("xml_export.include_empty_attributes", False,
           description="Whether to include attributes even when they are empty.")
])
def pretty(doc: Document = Document(),
           docid: AnnotationData = AnnotationData("<docid>"),
           out: Export = Export("xml_pretty/[xml_export.filename]"),
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
        doc: Name of the original document.
        docid: Annotation with document IDs.
        out: Path and filename pattern for resulting file.
        token: Annotation containing the token strings.
        word: Annotation containing the token strings.
        annotations: List of elements:attributes (annotations) to include.
        source_annotations: List of elements:attributes from the original document
            to be kept. If not specified, everything will be kept.
        header_annotations: List of header elements from the original document to include
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

    # Read words and document ID
    word_annotation = list(word.read())
    docid_annotation = docid.read()

    # Get annotation spans, annotations list etc.
    annotation_list, _, export_names = util.get_annotation_names(annotations, source_annotations, doc=doc,
                                                                 token_name=token_name,
                                                                 remove_namespaces=remove_namespaces,
                                                                 sparv_namespace=sparv_namespace,
                                                                 source_namespace=source_namespace)
    h_annotations, h_export_names = util.get_header_names(header_annotations, doc=doc)
    export_names.update(h_export_names)
    span_positions, annotation_dict = util.gather_annotations(annotation_list, export_names, h_annotations,
                                                              doc=doc, split_overlaps=True)
    xmlstr = xml_utils.make_pretty_xml(span_positions, annotation_dict, export_names, token_name, word_annotation,
                                       docid_annotation, include_empty_attributes, sparv_namespace)

    # Write XML to file
    with open(out, mode="w") as outfile:
        outfile.write(xmlstr)
    log.info("Exported: %s", out)


@exporter("Combined XML export (all results in one file)", config=[
    Config("xml_export.filename_combined", default="[metadata.id].xml",
           description="Filename of resulting combined XML.")
])
def combined(corpus: Corpus = Corpus(),
             out: Export = Export("[xml_export.filename_combined]"),
             docs: AllDocuments = AllDocuments(),
             xml_input: ExportInput = ExportInput("xml_pretty/[xml_export.filename]", all_docs=True)):
    """Combine XML export files into a single XML file."""
    xml_utils.combine(corpus, out, docs, xml_input)


@exporter("Compressed combined XML export", config=[
    Config("xml_export.filename_compressed", default="[metadata.id].xml.bz2",
           description="Filename of resulting compressed combined XML.")
])
def compressed(out: Export = Export("[xml_export.filename_compressed]"),
               xmlfile: ExportInput = ExportInput("[xml_export.filename_combined]")):
    """Compress combined XML export."""
    xml_utils.compress(xmlfile, out)


@installer("Copy compressed unscrambled XML to remote host", config=[
    Config("xml_export.export_original_host", "", description="Remote host to copy XML export to."),
    Config("xml_export.export_original_path", "", description="Path on remote host to copy XML export to.")
])
def install_original(corpus: Corpus = Corpus(),
                     xmlfile: ExportInput = ExportInput("[xml_export.filename_compressed]"),
                     out: OutputCommonData = OutputCommonData("xml_export.install_export_pretty_marker"),
                     export_path: str = Config("xml_export.export_original_path"),
                     host: str = Config("xml_export.export_original_host")):
    """Copy compressed combined unscrambled XML to remote host."""
    xml_utils.install_compressed_xml(corpus, xmlfile, out, export_path, host)
