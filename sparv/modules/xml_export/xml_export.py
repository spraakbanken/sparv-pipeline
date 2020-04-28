"""Export annotated corpus data to xml."""

import bz2
import logging
import os
import xml.dom.minidom
import xml.etree.ElementTree as etree
from collections import defaultdict
from typing import Optional

import sparv.util as util
from sparv import (AllDocuments, Annotation, Config, Corpus, Document, Export, ExportAnnotations, ExportInput, Output,
                   exporter, installer)

log = logging.getLogger(__name__)


@exporter("XML export with one token element per line", config=[
    Config("xml_export.dir", default="xml_pretty"),
    Config("xml_export.filename", default="{doc}_export.xml")
])
def pretty(doc: str = Document,
           docid: str = Annotation("<docid>", data=True),
           out: str = Export("[xml_export.dir]/[xml_export.filename]"),
           token: str = Annotation("<token>"),
           word: str = Annotation("<token:word>"),
           annotations: list = ExportAnnotations,
           original_annotations: Optional[list] = Config("original_annotations"),
           remove_namespaces: bool = Config("remove_export_namespaces", False)):
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

    # Root tag sanity check
    assert valid_root(span_positions[0], span_positions[-1]), "Root tag is missing!"

    # Create root node
    root_span = span_positions[0][2]
    root_span.set_node()
    add_attrs(root_span.node, root_span.name, annotation_dict, export_names, 0)
    node_stack = [root_span]
    overlap_ids = defaultdict(int)  # Keeps track of which overlapping spans belong together
    total_overlaps = 0

    # Go through span_positions and build xml tree
    for _pos, instruction, span in span_positions[1:]:

        # Create child node under the top stack node
        if instruction == "open":
            span.set_node(parent_node=node_stack[-1].node)
            node_stack.append(span)
            add_attrs(span.node, span.name, annotation_dict, export_names, span.index)
            # Add text if this node is a token
            if span.name == token:
                span.node.text = word_annotation[span.index]

        # Close node
        else:
            # Closing node == top stack node: pop stack and move on to next span
            if span == node_stack[-1]:
                node_stack.pop()

            # Handle overlapping spans
            else:
                total_overlaps = handle_overlaps(span, node_stack, docid, overlap_ids, total_overlaps, annotation_dict,
                                                 export_names)

    # Pretty formatting through minidom
    xmlstr = xml.dom.minidom.parseString(
        etree.tostring(root_span.node, method="xml", encoding=util.UTF8)).toprettyxml(
        indent="  ", encoding=util.UTF8).decode()

    # Write XML to file
    with open(out, mode="w") as outfile:
        outfile.write(xmlstr)
    log.info("Exported: %s", out)


@exporter("XML export preserving whitespaces from source file", config=[
    Config("xml_export.filename_formatted", default="{doc}_export.xml")
])
def preserve_formatting(doc: str = Document,
                        docid: str = Annotation("<docid>", data=True),
                        out: str = Export("xml_preserve_formatting/[xml_export.filename_formatted]"),
                        token: str = Annotation("<token>"),
                        annotations: list = ExportAnnotations,
                        original_annotations: Optional[list] = Config("original_annotations"),
                        remove_namespaces: bool = Config("remove_export_namespaces", False)):
    """Export annotations to xml in export_dir and keep whitespaces and indentation from original file.

    - doc: name of the original document
    - annotations: list of elements:attributes (annotations) to include.
    - original_annotations: list of elements:attributes from the original document
      to be kept. If not specified, everything will be kept.
    """
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Read corpus text and document ID
    corpus_text = util.read_corpus_text(doc)
    docid = util.read_data(doc, docid)

    # Get annotation spans, annotations list etc.
    annotations, _, export_names = util.get_annotation_names(doc, token, annotations, original_annotations,
                                                             remove_namespaces)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names, flatten=False)
    sorted_positions = [(pos, span[0], span[1]) for pos, spans in sorted(span_positions.items()) for span in spans]

    # Root tag sanity check
    assert valid_root(sorted_positions[0], sorted_positions[-1]), "Root tag is missing!"

    # Create root node
    root_span = sorted_positions[0][2]
    root_span.set_node()
    node_stack = []
    last_pos = 0  # Keeps track of the position of the processed text
    overlap_ids = defaultdict(int)  # Keeps track of which overlapping spans belong together
    total_overlaps = 0

    for x, (_pos, instruction, span) in enumerate(sorted_positions):

        # Open node: Create child node under the top stack node
        if instruction == "open":

            if node_stack:  # Don't create root node, it already exists
                span.set_node(parent_node=node_stack[-1].node)

            add_attrs(span.node, span.name, annotation_dict, export_names, span.index)
            node_stack.append(span)

            # Set text if there should be any between this node and the next one
            next_item = sorted_positions[x + 1]
            if next_item[1] == "open" and next_item[2].start > span.start:
                span.node.text = corpus_text[last_pos:next_item[2].start]
                last_pos = next_item[2].start

            # Set tail for previous node if necessary
            if last_pos < span.start:
                # Get last closing node in this position
                _, tail_span = [i for i in span_positions[last_pos] if i[0] == "close"][-1]
                tail_span.node.tail = corpus_text[last_pos:span.start]
                last_pos = span.start

        # Close node
        else:
            if last_pos < span.end:
                # Set node text if necessary
                if span.start == last_pos:
                    span.node.text = corpus_text[last_pos:span.end]
                # Set tail for previous node if necessary
                else:
                    # Get last closing node in this position
                    _, tail_span = [i for i in span_positions[last_pos] if i[0] == "close"][-1]
                    tail_span.node.tail = corpus_text[last_pos:span.end]
                last_pos = span.end

            # Closing node == top stack node: pop stack and move on to next span
            if span == node_stack[-1]:
                node_stack.pop()
            # Handle overlapping spans
            else:
                total_overlaps = handle_overlaps(span, node_stack, docid, overlap_ids, total_overlaps, annotation_dict,
                                                 export_names)

    # Write xml to file
    etree.ElementTree(root_span.node).write(out, xml_declaration=False, method="xml", encoding=util.UTF8)
    log.info("Exported: %s", out)


@exporter("Combined XML export (all results in one file)", config=[
    Config("xml_export.filename_combined", default="[id]_export.xml")
])
def combined(corpus: str = Corpus,
             out: str = Export("[xml_export.filename_combined]"),
             docs: list = AllDocuments,
             xml_input: str = ExportInput("[xml_export.dir]/[xml_export.filename]", all_docs=True)):
    """Combine XML export files into a single XML file."""
    xml_files = [xml_input.replace("{doc}", doc) for doc in docs]
    xml_files.sort()

    with open(out, "w") as outf:
        print('<corpus id="%s">' % corpus.replace("&", "&amp;").replace('"', "&quot;"), file=outf)
        for infile in xml_files:
            log.info("Read: %s", infile)
            with open(infile) as inf:
                print(inf.read(), file=outf)
        print("</corpus>", file=outf)
        log.info("Exported: %s" % out)


@exporter("Compress combined XML export", config=[
    Config("xml_export.filename_compressed", default="[id].xml.bz2")
])
def compressed(out: str = Export("[xml_export.filename_compressed]"),
               xmlfile: str = ExportInput("[xml_export.filename_combined]")):
    """Compress combined XML export."""
    with open(xmlfile) as f:
        file_data = f.read()
        compressed_data = bz2.compress(file_data.encode(util.UTF8))
    with open(out, "wb") as f:
        f.write(compressed_data)


@installer("Copy compressed combined unscrabled XML to remote host")
def install_original(xmlfile: str = ExportInput("[xml_export.filename_compressed]"),
                     out: str = Output("xml_export.time_install_export", data=True, common=True),
                     export_path: str = Config("export_path", ""),
                     host: str = Config("export_host", "")):
    """Copy compressed combined unscrabled XML to remote host."""
    if not host:
        raise(Exception("No host provided! Export not installed."))
    filename = os.path.basename(xmlfile)
    remote_file_path = os.path.join(export_path, filename)
    util.install_file(host, xmlfile, remote_file_path)
    util.write_common_data(out, "")


# TODO: add exporter, compressed exporter and installer for sentence and paragraph scrambled xml

########################################################################################################
# HELPERS
########################################################################################################


def valid_root(first_item, last_item):
    """Check the validity of the root tag."""
    return (first_item[1] == "open"
            and last_item[1] == "close"
            and first_item[2].name == last_item[2].name
            and first_item[2].index == last_item[2].index)


def add_attrs(node, annotation, annotation_dict, export_names, index):
    """Add attributes from annotation_dict to node."""
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(":".join([annotation, name]), name)
        node.set(export_name, annot[index])


def handle_overlaps(span, node_stack, docid, overlap_ids, total_overlaps, annotation_dict, export_names):
    """Close and open overlapping spans in correct order and add IDs to them."""
    overlap_stack = []
    # Close all overlapping spans and add and _overlap attribute to them
    while node_stack[-1] != span:
        overlap_elem = node_stack.pop()
        total_overlaps += 1
        overlap_ids[overlap_elem.name] += total_overlaps
        overlap_attr = "{}-{}".format(docid, overlap_ids[overlap_elem.name])
        overlap_elem.node.set("_overlap", overlap_attr)
        overlap_stack.append(overlap_elem)
    node_stack.pop()  # Close current span

    # Re-open overlapping spans and add and _overlap attribute to them
    while overlap_stack:
        overlap_elem = overlap_stack.pop()
        overlap_elem.set_node(parent_node=node_stack[-1].node)
        overlap_attr = "{}-{}".format(docid, overlap_ids[overlap_elem.name])
        overlap_elem.node.set("_overlap", overlap_attr)
        node_stack.append(overlap_elem)
        add_attrs(overlap_elem.node, overlap_elem.name, annotation_dict, export_names, overlap_elem.index)

    return total_overlaps
