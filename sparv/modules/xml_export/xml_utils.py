"""Util functions for XML export."""

import bz2
import io
import logging
import os
import re
import xml.etree.ElementTree as etree
from typing import Optional

import sparv.util as util

log = logging.getLogger(__name__)

INDENTATION = "  "


def make_pretty_xml(span_positions, annotation_dict, export_names, token_name: str, word_annotation, docid,
                    include_empty_attributes: bool, sparv_namespace: Optional[str] = None):
    """Create a pretty formatted XML string from span_positions.

    Used by pretty and sentence_scrambled.
    """
    # Root tag sanity check
    if not valid_root(span_positions[0], span_positions[-1]):
        raise util.SparvErrorMessage("Root tag is missing! If you have manually specified which elements to include, "
                                     "make sure to include an element that encloses all other included elements and "
                                     "text content.")

    # Create root node
    root_span = span_positions[0][2]
    root_span.set_node()
    add_attrs(root_span.node, root_span.name, annotation_dict, export_names, 0, include_empty_attributes)
    node_stack = [root_span]

    last_start_pos = None
    last_end_pos = -1
    current_token_text = None
    last_node = None
    inside_token = False

    def handle_subtoken_text(position, last_start_position, last_end_position, node, token_text):
        """Handle text for subtoken elements."""
        if last_start_position < last_end_position < position:
            node.tail = token_text[:position - last_end_position]
            token_text = token_text[position - last_end_position:]
        elif position > last_start_position:
            node.text = token_text[:position - last_start_position]
            token_text = token_text[position - last_start_position:]
        return token_text

    # Go through span_positions and build xml tree
    for _pos, instruction, span in span_positions[1:]:
        # Handle headers
        if span.is_header:
            if instruction == "open":
                header = annotation_dict[span.name][util.HEADER_CONTENTS][span.index]
                # Replace any leading tabs with spaces
                header = re.sub(r"^\t+", lambda m: INDENTATION * len(m.group()), header, flags=re.MULTILINE)
                header_xml = etree.fromstring(header)
                header_xml.tag = span.export  # Rename element if needed
                node_stack[-1].node.append(header_xml)
            continue

        # Create child node under the top stack node
        if instruction == "open":
            span.set_node(parent_node=node_stack[-1].node)
            node_stack.append(span)
            add_attrs(span.node, span.name, annotation_dict, export_names, span.index, include_empty_attributes)
            if span.overlap_id:
                if sparv_namespace:
                    span.node.set(f"{sparv_namespace}.{util.OVERLAP_ATTR}", f"{docid}-{span.overlap_id}")
                else:
                    span.node.set(f"{util.SPARV_DEFAULT_NAMESPACE}.{util.OVERLAP_ATTR}", f"{docid}-{span.overlap_id}")

            # Add text if this node is a token
            if span.name == token_name:
                inside_token = True
                # Save text until later
                last_start_pos = span.start
                current_token_text = word_annotation[span.index]

            if inside_token and current_token_text:
                current_token_text = handle_subtoken_text(span.start, last_start_pos, last_end_pos, last_node,
                                                          current_token_text)
                last_start_pos = span.start
                last_node = span.node

        # Close node
        else:
            if inside_token and current_token_text:
                current_token_text = handle_subtoken_text(span.end, last_start_pos, last_end_pos, last_node,
                                                          current_token_text)
                last_end_pos = span.end
                last_node = span.node
            if span.name == token_name:
                inside_token = False

            # Make sure closing node == top stack node
            assert span == node_stack[-1], "Overlapping elements found: {}".format(node_stack[-2:])
            # Pop stack and move on to next span
            node_stack.pop()

    # Pretty formatting of XML tree
    indent(root_span.node)

    # We use write() instead of tostring() here to be able to get an XML declaration
    stream = io.StringIO()
    etree.ElementTree(root_span.node).write(stream, encoding="unicode", method="xml", xml_declaration=True)
    return stream.getvalue()


def indent(elem, level=0) -> None:
    """Add pretty-print indentation to XML tree.

    From http://effbot.org/zone/element-lib.htm#prettyprint
    """
    i = "\n" + level * INDENTATION
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + INDENTATION
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def valid_root(first_item, last_item):
    """Check the validity of the root tag."""
    return (first_item[1] == "open"
            and last_item[1] == "close"
            and first_item[2].name == last_item[2].name
            and first_item[2].index == last_item[2].index)


def add_attrs(node, annotation, annotation_dict, export_names, index, include_empty_attributes: bool):
    """Add attributes from annotation_dict to node."""
    for attrib_name, attrib_values in annotation_dict[annotation].items():
        export_name = export_names.get(":".join([annotation, attrib_name]), attrib_name)
        if attrib_values[index] or include_empty_attributes:
            node.set(export_name, attrib_values[index])


def combine(corpus, out, docs, xml_input):
    """Combine xml_files into one single file."""
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


def compress(xmlfile, out):
    """Compress xmlfile to out."""
    with open(xmlfile) as f:
        file_data = f.read()
        compressed_data = bz2.compress(file_data.encode(util.UTF8))
    with open(out, "wb") as f:
        f.write(compressed_data)


def install_compressed_xml(corpus, xmlfile, out, export_path, host):
    """Install xml file on remote server."""
    if not host:
        raise(Exception("No host provided! Export not installed."))
    filename = corpus + ".xml.bz2"
    remote_file_path = os.path.join(export_path, filename)
    util.install_file(host, xmlfile, remote_file_path)
    out.write("")
