"""Export annotated corpus data to format-preserved xml."""

import logging
import os
import xml.etree.ElementTree as etree
from typing import Optional

import sparv.util as util
from sparv import Annotation, Config, Document, Export, ExportAnnotations, exporter
from . import xml_utils

log = logging.getLogger(__name__)


@exporter("XML export preserving whitespaces from source file", config=[
    Config("xml_export.filename_formatted", default="{doc}_export.xml"),
    Config("xml_export.original_annotations"),
    Config("xml_export.header_annotations")
])
def preserved_format(doc: str = Document,
                     docid: str = Annotation("<docid>", data=True),
                     out: str = Export("xml_preserved_format/[xml_export.filename_formatted]"),
                     annotations: list = ExportAnnotations(export_type="xml_export"),
                     original_annotations: Optional[list] = Config("xml_export.original_annotations"),
                     header_annotations: Optional[list] = Config("xml_export.header_annotations"),
                     remove_namespaces: bool = Config("export.remove_export_namespaces", False)):
    """Export annotations to XML in export_dir and keep whitespaces and indentation from original file.

    Args:
        doc: Name of the original document.
        docid: Annotation with document IDs.
        out: Path and filename pattern for resulting file.
        annotations: List of elements:attributes (annotations) to include.
        original_annotations: List of elements:attributes from the original document
            to be kept. If not specified, everything will be kept.
        header_annotations: List of header elements from the original document to include
            in the export. If not specified, all headers will be kept.
        remove_namespaces: Whether to remove module "namespaces" from element and attribute names.
            Disabled by default.

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
    annotations, _, export_names = util.get_annotation_names(doc, None, annotations, original_annotations,
                                                             remove_namespaces)
    h_annotations, h_export_names = util.get_header_names(doc, header_annotations, remove_namespaces)
    export_names.update(h_export_names)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names, flatten=False,
                                                              split_overlaps=True, header_annotations=h_annotations)
    sorted_positions = [(pos, span[0], span[1]) for pos, spans in sorted(span_positions.items()) for span in spans]

    # Root tag sanity check
    if not xml_utils.valid_root(sorted_positions[0], sorted_positions[-1]):
        raise util.SparvErrorMessage("Root tag is missing! If you have manually specified which elements to include, "
                                     "make sure to include an element that encloses all other included elements and "
                                     "text content.")

    # Create root node
    root_span = sorted_positions[0][2]
    root_span.set_node()
    node_stack = []
    last_pos = 0  # Keeps track of the position of the processed text

    for x, (_pos, instruction, span) in enumerate(sorted_positions):
        # Open node: Create child node under the top stack node
        if instruction == "open":
            # Set tail for previous node if necessary
            if last_pos < span.start:
                # Get last closing node in this position
                _, tail_span = [i for i in span_positions[last_pos] if i[0] == "close"][-1]
                tail_span.node.tail = corpus_text[last_pos:span.start]
                last_pos = span.start

            # Handle headers
            if span.is_header:
                header = annotation_dict[span.name][util.HEADER_CONTENT][span.index]
                header_xml = etree.fromstring(header)
                header_xml.tag = span.export  # Rename element if needed
                span.node = header_xml
                node_stack[-1].node.append(header_xml)
            else:
                if node_stack:  # Don't create root node, it already exists
                    span.set_node(parent_node=node_stack[-1].node)

                xml_utils.add_attrs(span.node, span.name, annotation_dict, export_names, span.index)
                if span.overlap_id:
                    span.node.set("_overlap", f"{docid}-{span.overlap_id}")
                node_stack.append(span)

                # Set text if there should be any between this node and the next one
                next_item = sorted_positions[x + 1]
                if next_item[1] == "open" and next_item[2].start > span.start:
                    span.node.text = corpus_text[last_pos:next_item[2].start]
                    last_pos = next_item[2].start

        # Close node
        else:
            if span.is_header:
                continue
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

            # Make sure closing node == top stack node
            assert span == node_stack[-1], "Overlapping elements found: {}".format(node_stack[-2:])
            # Pop stack and move on to next span
            node_stack.pop()

    # Write xml to file
    etree.ElementTree(root_span.node).write(out, encoding="unicode", method="xml", xml_declaration=True)
    log.info("Exported: %s", out)
