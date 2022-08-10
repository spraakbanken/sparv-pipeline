"""Util functions for XML export."""

import bz2
import io
import os
import re
import xml.etree.ElementTree as etree
from shutil import copyfileobj
from typing import Optional

from sparv.api import SparvErrorMessage, get_logger, util

logger = get_logger(__name__)

INDENTATION = "  "


def make_pretty_xml(span_positions, annotation_dict, export_names, token_name: str, word_annotation, fileid,
                    include_empty_attributes: bool, sparv_namespace: Optional[str] = None,
                    xml_namespaces: Optional[dict] = None):
    """Create a pretty formatted XML string from span_positions.

    Used by pretty and sentence_scrambled.
    """
    # Root tag sanity check
    if not valid_root(span_positions[0], span_positions[-1]):
        raise SparvErrorMessage("Root tag is missing! If you have manually specified which elements to include, "
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

    register_namespaces(xml_namespaces)

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
                header = annotation_dict[span.name][util.constants.HEADER_CONTENTS][span.index]
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
                    span.node.set(f"{sparv_namespace}.{util.constants.OVERLAP_ATTR}", f"{fileid}-{span.overlap_id}")
                else:
                    span.node.set(f"{util.constants.SPARV_DEFAULT_NAMESPACE}.{util.constants.OVERLAP_ATTR}",
                                  f"{fileid}-{span.overlap_id}")

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
            assert span == node_stack[-1], "Overlapping elements found. Expected {} but found {}".format(span, node_stack[-1])
            # Pop stack and move on to next span
            node_stack.pop()

    # Pretty formatting of XML tree
    util.misc.indent_xml(root_span.node, indentation=INDENTATION)

    # We use write() instead of tostring() here to be able to get an XML declaration
    stream = io.StringIO()
    etree.ElementTree(root_span.node).write(stream, encoding="unicode", method="xml", xml_declaration=True)
    return stream.getvalue()


def valid_root(first_item, last_item, true_root: bool = False):
    """Check the validity of the root tag."""
    return (first_item[1] == "open"
            and last_item[1] == "close"
            and first_item[2].name == last_item[2].name
            and first_item[2].index == last_item[2].index
            and (not true_root or (first_item[0] == 0)))


def register_namespaces(xml_namespaces: dict):
    """Register all namespace prefixes."""
    for prefix, uri in xml_namespaces.items():
        etree.register_namespace(prefix, uri)


def add_attrs(node, annotation, annotation_dict, export_names, index, include_empty_attributes: bool):
    """Add attributes from annotation_dict to node."""
    for attrib_name, attrib_values in annotation_dict[annotation].items():
        export_name = export_names.get(":".join([annotation, attrib_name]), attrib_name)
        if attrib_values[index] or include_empty_attributes:
            node.set(export_name, attrib_values[index])


def combine(corpus, out, source_files, xml_input, version_info_file=None):
    """Combine xml_files into one single file."""
    xml_files = [xml_input.replace("{file}", file) for file in source_files]
    xml_files.sort()
    with open(out, "w", encoding="utf-8") as outf:
        print("<?xml version='1.0' encoding='UTF-8'?>", file=outf)
        if version_info_file:
            print("<!--", file=outf)
            with open(version_info_file, encoding="utf-8") as vi:
                for line in vi.readlines():
                    print(line.strip(), file=outf)
            print("-->", file=outf)
        print('<corpus id="%s">' % corpus.replace("&", "&amp;").replace('"', "&quot;"), file=outf)
        for infile in xml_files:
            logger.info("Read: %s", infile)
            with open(infile, encoding="utf-8") as inf:
                for n, line in enumerate(inf):
                    # Skip xml declaration
                    if n == 0 and line.startswith("<?xml"):
                        continue
                    # Indent line
                    outf.write(f"{INDENTATION}{line}")
        print("</corpus>", file=outf)
        logger.info("Exported: %s" % out)


def compress(xmlfile, out):
    """Compress XML file using bzip2.

    Args:
        xmlfile: Path to source file.
        out: Path to target bz2 file.
    """
    with open(xmlfile, "rb") as infile:
        with bz2.BZ2File(out, "wb") as outfile:
            copyfileobj(infile, outfile)


def install_compressed_xml(corpus, bz2file, out, export_path, host):
    """Install xml file on remote server."""
    if not host:
        raise Exception("No host provided! Export not installed.")
    filename = corpus + ".xml.bz2"
    remote_file_path = os.path.join(export_path, filename)
    util.install.install_file(bz2file, host, remote_file_path)
    out.write("")
