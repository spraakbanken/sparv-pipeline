"""Export annotated corpus data to pretty-printed xml."""

import logging
import os
from typing import Optional

from . import xml_utils
import sparv.util as util
from sparv import (AllDocuments, Annotation, Config, Corpus, Document, Export, ExportAnnotations, ExportInput, Output,
                   exporter, installer)

log = logging.getLogger(__name__)


@exporter("XML export with one token element per line", config=[
    Config("xml_export.filename", default="{doc}_export.xml")
])
def pretty(doc: str = Document,
           docid: str = Annotation("<docid>", data=True),
           out: str = Export("xml_original/[xml_export.filename]"),
           token: str = Annotation("<token>"),
           word: str = Annotation("<token:word>"),
           annotations: list = ExportAnnotations(export_type="xml_export"),
           original_annotations: Optional[list] = Config("xml_export.original_annotations"),
           remove_namespaces: bool = Config("export.remove_export_namespaces", False)):
    """Export annotations to xml in export_dir.

    - doc: name of the original document
    - word: annotation containing the token strings.
    - annotations: list of elements:attributes (annotations) to include.
    - original_annotations: list of elements:attributes from the original document
      to be kept. If not specified, everything will be kept.
    """
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Read words and document ID
    word_annotation = list(util.read_annotation(doc, word))
    docid = util.read_data(doc, docid)

    # Get annotation spans, annotations list etc.
    annotations, _, export_names = util.get_annotation_names(doc, token, annotations, original_annotations,
                                                             remove_namespaces)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names)
    xmlstr = xml_utils.make_pretty_xml(span_positions, annotation_dict, export_names, token, word_annotation, docid)

    # Write XML to file
    with open(out, mode="w") as outfile:
        outfile.write(xmlstr)
    log.info("Exported: %s", out)


@exporter("Combined XML export (all results in one file)", config=[
    Config("xml_export.filename_combined", default="[meta_data.id].xml")
])
def combined(corpus: str = Corpus,
             out: str = Export("[xml_export.filename_combined]"),
             docs: list = AllDocuments,
             xml_input: str = ExportInput("xml_original/[xml_export.filename]", all_docs=True)):
    """Combine XML export files into a single XML file."""
    xml_utils.combine(corpus, out, docs, xml_input)


@exporter("Compressed combined XML export", config=[
    Config("xml_export.filename_compressed", default="[meta_data.id].xml.bz2")
])
def compressed(out: str = Export("[xml_export.filename_compressed]"),
               xmlfile: str = ExportInput("[xml_export.filename_combined]")):
    """Compress combined XML export."""
    xml_utils.compress(xmlfile, out)


@installer("Copy compressed unscrambled XML to remote host")
def install_original(corpus: str = Corpus,
                     xmlfile: str = ExportInput("[xml_export.filename_compressed]"),
                     out: str = Output("xml_export.time_install_export", data=True, common=True),
                     export_path: str = Config("xml_export.export_original_path", ""),
                     host: str = Config("xml_export.export_original_host", "")):
    """Copy compressed combined unscrambled XML to remote host."""
    xml_utils.install_compressed_xml(corpus, xmlfile, out, export_path, host)
