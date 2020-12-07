"""Export annotated corpus data to scrambled xml."""

import logging
import os

import sparv.util as util
from sparv import (AllDocuments, Annotation, AnnotationData, Config, Corpus, Document, Export, ExportAnnotations,
                   ExportInput, OutputCommonData, SourceAnnotations, exporter, installer)
from . import xml_utils

log = logging.getLogger(__name__)


@exporter("Scrambled XML export", config=[
    Config("xml_export.scramble_on", description="Annotation to use for scrambling.")
])
def scrambled(doc: Document = Document(),
              docid: AnnotationData = AnnotationData("<docid>"),
              out: Export = Export("xml_scrambled/[xml_export.filename]"),
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
    # Get annotation spans, annotations list etc.
    annotation_list, _, export_names = util.get_annotation_names(annotations, source_annotations, doc=doc,
                                                                 token_name=token.name,
                                                                 remove_namespaces=remove_namespaces,
                                                                 sparv_namespace=sparv_namespace,
                                                                 source_namespace=source_namespace)
    if chunk not in annotation_list:
        raise util.SparvErrorMessage(
            "The annotation used for scrambling ({}) needs to be included in the output.".format(chunk))
    span_positions, annotation_dict = util.gather_annotations(annotation_list, export_names, doc=doc,
                                                              split_overlaps=True)

    # Read words and document ID
    word_annotation = list(word.read())
    chunk_order = list(chunk_order.read())
    docid_annotation = docid.read()

    # Reorder chunks
    new_span_positions = util.scramble_spans(span_positions, chunk.name, chunk_order)

    # Construct XML string
    xmlstr = xml_utils.make_pretty_xml(new_span_positions, annotation_dict, export_names, token.name, word_annotation,
                                       docid_annotation, include_empty_attributes, sparv_namespace)

    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Write XML to file
    with open(out, mode="w") as outfile:
        outfile.write(xmlstr)
    log.info("Exported: %s", out)


@exporter("Combined scrambled XML export")
def combined_scrambled(corpus: Corpus = Corpus(),
                       out: Export = Export("[metadata.id]_scrambled.xml"),
                       docs: AllDocuments = AllDocuments(),
                       xml_input: ExportInput = ExportInput("xml_scrambled/[xml_export.filename]", all_docs=True)):
    """Combine XML export files into a single XML file."""
    xml_utils.combine(corpus, out, docs, xml_input)


@exporter("Compressed combined scrambled XML export")
def compressed_scrambled(out: Export = Export("[metadata.id]_scrambled.xml.bz2"),
                         xmlfile: ExportInput = ExportInput("[metadata.id]_scrambled.xml")):
    """Compress combined XML export."""
    xml_utils.compress(xmlfile, out)


@installer("Copy compressed scrambled XML to remote host", config=[
    Config("xml_export.export_host", "", description="Remote host to copy scrambled XML export to"),
    Config("xml_export.export_path", "", description="Path on remote host to copy scrambled XML export to")
])
def install_scrambled(corpus: Corpus = Corpus(),
                      xmlfile: ExportInput = ExportInput("[metadata.id]_scrambled.xml"),
                      out: OutputCommonData = OutputCommonData("xml_export.install_export_scrambled_marker"),
                      export_path: str = Config("xml_export.export_path"),
                      host: str = Config("xml_export.export_host")):
    """Copy compressed combined scrambled XML to remote host."""
    xml_utils.install_compressed_xml(corpus, xmlfile, out, export_path, host)
