"""Export annotated corpus data to format-preserved xml."""

import logging
import os
import xml.etree.ElementTree as etree
from collections import defaultdict
from typing import Optional

from . import xml_utils
import sparv.util as util
from sparv import Annotation, Config, Document, Export, ExportAnnotations, exporter

log = logging.getLogger(__name__)


@exporter("XML export preserving whitespaces from source file", config=[
    Config("xml_export.filename_formatted", default="{doc}_export.xml")
])
def preserved_format(doc: str = Document,
                     docid: str = Annotation("<docid>", data=True),
                     out: str = Export("xml_preserve_formatting/[xml_export.filename_formatted]"),
                     token: str = Annotation("<token>"),
                     annotations: list = ExportAnnotations(export_type="xml_export"),
                     original_annotations: Optional[list] = Config("xml_export.original_annotations"),
                     remove_namespaces: bool = Config("export.remove_export_namespaces", False)):
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
    assert xml_utils.valid_root(sorted_positions[0], sorted_positions[-1]), "Root tag is missing!"

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

            xml_utils.add_attrs(span.node, span.name, annotation_dict, export_names, span.index)
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
                total_overlaps = xml_utils.handle_overlaps(span, node_stack, docid, overlap_ids, total_overlaps,
                                                           annotation_dict, export_names)

    # Write xml to file
    etree.ElementTree(root_span.node).write(out, xml_declaration=False, method="xml", encoding=util.UTF8)
    log.info("Exported: %s", out)
