"""Export annotated corpus data to xml."""

import os
import xml.etree.ElementTree as etree
from collections import defaultdict
from typing import Optional

import sparv.util as util
from sparv import annotator, Document, Annotation, Export, ExportAnnotations, Config


@annotator("XML export", exporter=True)
def export(doc: str = Document,
           docid: str = Annotation("<docid>", data=True),
           out: str = Export("xml/[xml_export.filename={doc}_export.xml]"),
           token: str = Annotation("<token>"),
           word: str = Annotation("<token:word>"),
           annotations: list = ExportAnnotations,
           original_annotations: Optional[list] = None):
    """Export annotations to xml in export_dir.

    - doc: name of the original document
    - token: name of the token level annotation span
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
    annotations, _, export_names = util.get_annotation_names(doc, token, annotations, original_annotations)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names)

    # Root tag sanity check
    assert valid_root(span_positions[0], span_positions[-1]), "Root tag is missing!"

    # Create root node
    root_span = span_positions[0][2]
    root_span.set_node()
    root_span.node.text = "\n"
    add_attrs(root_span.node, root_span.name, annotation_dict, export_names, 0)
    node_stack = [root_span]
    overlap_ids = defaultdict(int)  # Keeps track of which overlapping spans belong together

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
            # Some formatting: add line breaks between elements
            else:
                span.node.text = "\n"
            span.node.tail = "\n"

        # Close node
        else:
            # Closing node == top stack node: pop stack and move on to next span
            if span == node_stack[-1]:
                node_stack.pop()

            # Handle overlapping spans
            else:
                handle_overlaps(span, node_stack, docid, overlap_ids, annotation_dict, export_names)

    # Write xml to file
    etree.ElementTree(root_span.node).write(out, xml_declaration=False, method="xml", encoding=util.UTF8)
    util.log.info("Exported: %s", out)


@annotator("XML export preserving whitespace from source file", exporter=True)
def export_formatted(doc: str = Document,
                     docid: str = Annotation("<docid>", data=True),
                     out: str = Export("xml_formatted/[xml_export.filename_formatted={doc}_export.xml]"),
                     token: str = Annotation("<token>"),
                     annotations: list = ExportAnnotations,
                     original_annotations: Optional[list] = None):
    """Export annotations to xml in export_dir and keep whitespaces and indentation from original file.

    - doc: name of the original document
    - token: name of the token level annotation span
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
    annotations, _, export_names = util.get_annotation_names(doc, token, annotations, original_annotations)
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
                handle_overlaps(span, node_stack, docid, overlap_ids, annotation_dict, export_names)

    # Write xml to file
    etree.ElementTree(root_span.node).write(out, xml_declaration=False, method="xml", encoding=util.UTF8)
    util.log.info("Exported: %s", out)


def combine_xml(master, out, xmlfiles="", xmlfiles_list=""):
    """Combine xmlfiles into a single xml file and save to out."""
    # TODO: Test this
    assert master != "", "Master not specified"
    assert out != "", "Outfile not specified"
    assert (xmlfiles or xmlfiles_list), "Missing source"

    if xmlfiles:
        if isinstance(xmlfiles, str):
            xmlfiles = xmlfiles.split()
    elif xmlfiles_list:
        with open(xmlfiles_list) as insource:
            xmlfiles = [line.strip() for line in insource]

    xmlfiles.sort()

    with open(out, "w") as OUT:
        print('<corpus id="%s">' % master.replace("&", "&amp;").replace('"', "&quot;"), file=OUT)
        for infile in xmlfiles:
            util.log.info("Read: %s", infile)
            with open(infile, "r") as IN:
                # Append everything but <corpus> and </corpus>
                print(IN.read()[9:-10], end=' ', file=OUT)
        print("</corpus>", file=OUT)
        util.log.info("Exported: %s" % out)

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


def handle_overlaps(span, node_stack, docid, overlap_ids, annotation_dict, export_names):
    """Close and open overlapping spans in correct order and add IDs to them."""
    overlap_stack = []
    # Close all overlapping spans and add and _overlap attribute to them
    while node_stack[-1] != span:
        overlap_elem = node_stack.pop()
        overlap_ids[overlap_elem.name] += 1
        overlap_attr = "%s-%s" % (docid, str(overlap_ids[overlap_elem.name]))
        overlap_elem.node.set("_overlap", overlap_attr)
        overlap_stack.append(overlap_elem)
    node_stack.pop()  # Close current span

    # Re-open overlapping spans and add and _overlap attribute to them
    while overlap_stack:
        overlap_elem = overlap_stack.pop()
        overlap_elem.set_node(parent_node=node_stack[-1].node)
        overlap_elem.node.text = overlap_elem.node.tail = "\n"
        overlap_attr = "%s-%s" % (docid, str(overlap_ids[overlap_elem.name]))
        overlap_elem.node.set("_overlap", overlap_attr)
        node_stack.append(overlap_elem)
        add_attrs(overlap_elem.node, overlap_elem.name, annotation_dict, export_names, overlap_elem.index)


if __name__ == "__main__":
    util.run.main(export,
                  export_formatted=export_formatted,
                  combine_xml=combine_xml)
