"""Export annotated corpus data to scrambled xml."""

import logging
import os
from typing import Optional

from . import xml_utils
import sparv.util as util
from sparv import (AllDocuments, Annotation, Config, Corpus, Document, Export, ExportAnnotations, ExportInput, Output,
                   exporter, installer)

log = logging.getLogger(__name__)


@exporter("Scrambled XML export")
def scrambled(doc: str = Document,
              docid: str = Annotation("<docid>", data=True),
              out: str = Export("xml_scrambled/[xml_export.filename]"),
              chunk: str = Annotation("[export.scramble_on]"),
              chunk_order: str = Annotation("[export.scramble_on]:misc.number_random"),
              token: str = Annotation("<token>"),
              word: str = Annotation("<token:word>"),
              annotations: list = ExportAnnotations(export_type="xml_export"),
              original_annotations: Optional[list] = Config("xml_export.original_annotations"),
              remove_namespaces: bool = Config("export.remove_export_namespaces", False),
              include_empty_attributes: bool = Config("xml_export.include_empty_attributes")):
    """Export annotations to scrambled XML."""
    if chunk not in annotations:
        raise util.SparvErrorMessage(
            "The annotation used for scrambling ({}) needs to be included in the output.".format(chunk))

    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Read words and document ID
    word_annotation = list(util.read_annotation(doc, word))
    chunk_order = list(util.read_annotation(doc, chunk_order))
    docid = util.read_data(doc, docid)

    # Get annotation spans, annotations list etc.
    annotations, _, export_names = util.get_annotation_names(doc, token, annotations, original_annotations,
                                                             remove_namespaces)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names, split_overlaps=True)

    # Reorder chunks
    new_span_positions = util.scramble_spans(span_positions, chunk, chunk_order)

    # Construct XML string
    xmlstr = xml_utils.make_pretty_xml(new_span_positions, annotation_dict, export_names, token, word_annotation, docid,
                                       include_empty_attributes)

    # Write XML to file
    with open(out, mode="w") as outfile:
        outfile.write(xmlstr)
    log.info("Exported: %s", out)


@exporter("Combined scrambled XML export")
def combined_scrambled(corpus: str = Corpus,
                       out: str = Export("[metadata.id]_scrambled.xml"),
                       docs: list = AllDocuments,
                       xml_input: str = ExportInput("xml_scrambled/[xml_export.filename]", all_docs=True)):
    """Combine XML export files into a single XML file."""
    xml_utils.combine(corpus, out, docs, xml_input)


@exporter("Compressed combined scrambled XML export")
def compressed_scrambled(out: str = Export("[metadata.id]_scrambled.xml.bz2"),
                         xmlfile: str = ExportInput("[metadata.id]_scrambled.xml")):
    """Compress combined XML export."""
    xml_utils.compress(xmlfile, out)


@installer("Copy compressed scrambled XML to remote host")
def install_scrambled(corpus: Corpus,
                      xmlfile: str = ExportInput("[metadata.id]_scrambled.xml"),
                      out: str = Output("xml_export.time_install_export_scrambled", data=True, common=True),
                      export_path: str = Config("xml_export.export_path", ""),
                      host: str = Config("xml_export.export_host", "")):
    """Copy compressed combined scrambled XML to remote host."""
    xml_utils.install_compressed_xml(corpus, xmlfile, out, export_path, host)
