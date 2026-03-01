"""Util functions for XML export."""

from __future__ import annotations

import bz2
import io
import re
import xml.etree.ElementTree as etree  # noqa: N813
from collections.abc import Sequence
from pathlib import Path
from shutil import copyfileobj

from sparv.api import SparvErrorMessage, get_logger, util
from sparv.api.classes import Corpus, ExportInput, OutputMarker

logger = get_logger(__name__)

INDENTATION = "  "


def make_pretty_xml(
    span_positions: list[tuple],
    annotation_dict: dict[str, dict],
    export_names: dict[str, str],
    token_name: str,
    word_annotation: list[str],
    fileid: str,
    include_empty_attributes: bool,
    sparv_namespace: str | None = None,
    xml_namespaces: dict | None = None,
) -> str:
    """Create a pretty formatted XML string from span_positions.

    Used by pretty and sentence_scrambled.

    Args:
        span_positions: List of tuples with span positions.
        annotation_dict: Dictionary with annotations.
        export_names: Dictionary with export names.
        token_name: Name of the token element.
        word_annotation: Word annotation.
        fileid: File ID.
        include_empty_attributes: Whether to include empty attributes.
        sparv_namespace: Optional namespace for Sparv attributes.
        xml_namespaces: Optional dictionary with XML namespaces.

    Returns:
        Pretty formatted XML string.

    Raises:
        SparvErrorMessage: If the root tag is missing.
    """
    # Root tag sanity check
    if not valid_root(span_positions[0], span_positions[-1]):
        raise SparvErrorMessage(
            "Root tag is missing! If you have manually specified which elements to include, "
            "make sure to include an element that encloses all other included elements and "
            "text content."
        )

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

    def handle_subtoken_text(
        position: int, last_start_position: int, last_end_position: int, node: etree.Element, token_text: str
    ) -> str:
        """Handle text for subtoken elements.

        Args:
            position: Current position.
            last_start_position: Last start position.
            last_end_position: Last end position.
            node: Current node.
            token_text: Current token text.

        Returns:
            Updated token text.
        """
        if last_start_position < last_end_position < position:
            node.tail = token_text[: position - last_end_position]
            token_text = token_text[position - last_end_position :]
        elif position > last_start_position:
            node.text = token_text[: position - last_start_position]
            token_text = token_text[position - last_start_position :]
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
                    span.node.set(
                        f"{util.constants.SPARV_DEFAULT_NAMESPACE}.{util.constants.OVERLAP_ATTR}",
                        f"{fileid}-{span.overlap_id}",
                    )

            # Add text if this node is a token
            if span.name == token_name:
                inside_token = True
                # Save text until later
                last_start_pos = span.start
                current_token_text = word_annotation[span.index]

            if inside_token and current_token_text:
                current_token_text = handle_subtoken_text(
                    span.start, last_start_pos, last_end_pos, last_node, current_token_text
                )
                last_start_pos = span.start
                last_node = span.node

        # Close node
        else:
            if inside_token and current_token_text:
                current_token_text = handle_subtoken_text(
                    span.end, last_start_pos, last_end_pos, last_node, current_token_text
                )
                last_end_pos = span.end
                last_node = span.node
            if span.name == token_name:
                inside_token = False

            # Make sure closing node == top stack node
            assert span == node_stack[-1], f"Overlapping elements found. Expected {span} but found {node_stack[-1]}"
            # Pop stack and move on to next span
            node_stack.pop()

    # Pretty formatting of XML tree
    etree.indent(root_span.node, space=INDENTATION)

    # We use write() instead of tostring() here to be able to get an XML declaration
    stream = io.StringIO()
    etree.ElementTree(root_span.node).write(stream, encoding="unicode", method="xml", xml_declaration=True)
    return stream.getvalue()


def valid_root(first_item: tuple, last_item: tuple, true_root: bool = False) -> bool:
    """Check the validity of the root tag.

    Checks that the first item is an opening tag and the last item is a closing tag with the same name and index. If
    `true_root` is `True`, it also checks that the first item's index is 0, meaning that it is the real root tag.

    Args:
        first_item: First item from the list of spans.
        last_item: Last item in the list of spans.
        true_root: Whether to check for a true root tag.

    Returns:
        `True` if the root tag is valid, `False` otherwise.
    """
    return (
        first_item[1] == "open"
        and last_item[1] == "close"
        and first_item[2].name == last_item[2].name
        and first_item[2].index == last_item[2].index
        and (not true_root or (first_item[0] == 0))
    )


def register_namespaces(xml_namespaces: dict) -> None:
    """Register all namespace prefixes."""
    for prefix, uri in xml_namespaces.items():
        etree.register_namespace(prefix, uri)


def add_attrs(
    node: etree.Element,
    annotation: str,
    annotation_dict: dict[str, dict],
    export_names: dict[str, str],
    index: int,
    include_empty_attributes: bool,
) -> None:
    """Add attributes from annotation_dict to node.

    Args:
        node: XML node to add attributes to.
        annotation: Annotation name.
        annotation_dict: Dictionary with attribute annotations and values.
        export_names: Dictionary with export names.
        index: Index of the annotation.
        include_empty_attributes: Whether to include empty attributes.
    """
    for attrib_name, attrib_values in annotation_dict[annotation].items():
        export_name = export_names.get(f"{annotation}:{attrib_name}", attrib_name)
        if attrib_values[index] or include_empty_attributes:
            node.set(export_name, attrib_values[index])


def replace_invalid_chars_in_names(export_names: dict) -> None:
    """Replace invalid characters with underscore in export names.

    Args:
        export_names: Dictionary with export names.
    """
    # https://www.w3.org/TR/REC-xml/#NT-NameStartChar
    start_chars = [
        ":",
        "A-Z",
        "_",
        "a-z",
        "\xc0-\xd6",
        "\xd8-\xf6",
        "\xf8-\u02ff",
        "\u0370-\u037d",
        "\u037f-\u1fff",
        "\u200c-\u200d",
        "\u2070-\u218f",
        "\u2c00-\u2fef",
        "\u3001-\ud7ff",
        "\uf900-\ufdcf",
        "\ufdf0-\ufffd",
        "\u10000-\uefffF",
    ]
    chars = ["-", ".", "0-9", "\xb7", "\u0300-\u036f", "\u203f-\u2040"]

    name_start_char = re.compile(r"[^{}]".format("".join(start_chars)))
    name_char = re.compile(r"[^{}{}]".format("".join(chars), "".join(start_chars)))
    namespace_split = re.compile(r"^({[^}]+})?(.+)")

    for n, n2 in export_names.items():
        namespace, name = namespace_split.match(n2).groups()
        original_name = name

        if name_start_char.match(name[0]):
            name = name_start_char.sub("_", name[0]) + name[1:]

        if name_char.search(name[1:]):
            name = name[0] + name_char.sub("_", name[1:])

        if name != original_name:
            logger.warning(
                "The name '%s' contains invalid characters and will be renamed to '%s'.", original_name, name
            )
            export_names[n] = (namespace or "") + name


def combine(
    corpus: str,
    out: str,
    source_files: Sequence[str],
    xml_input: str,
    version_info_file: str | None = None,
    compress: bool = False,
) -> None:
    """Combine XML files into one single XML file, optionally compressing it."""
    xml_files = [xml_input.replace("{file}", file) for file in source_files]
    xml_files.sort()
    logger.progress(total=len(xml_files))
    opener = bz2.open if compress else open
    with opener(out, "wt", encoding="utf-8") as outf:
        print("<?xml version='1.0' encoding='UTF-8'?>", file=outf)
        if version_info_file:
            print("<!--", file=outf)
            with Path(version_info_file).open(encoding="utf-8") as vi:
                for line in vi:
                    print(line.strip(), file=outf)
            print("-->", file=outf)
        print('<corpus id="{}">'.format(corpus.replace("&", "&amp;").replace('"', "&quot;")), file=outf)
        for infile in xml_files:
            logger.info("Read: %s", infile)
            with Path(infile).open(encoding="utf-8") as inf:
                for n, line in enumerate(inf):
                    # Skip xml declaration
                    if n == 0 and line.startswith("<?xml"):
                        continue
                    # Indent line
                    outf.write(f"{INDENTATION}{line}")
                logger.progress()
        print("</corpus>", file=outf)
        logger.info("Exported: %s", out)


def compress(xmlfile: str, out: str) -> None:
    """Compress XML file using bzip2.

    Args:
        xmlfile: Path to source file.
        out: Path to target bz2 file.
    """
    with Path(xmlfile).open("rb") as infile, bz2.BZ2File(out, "wb") as outfile:
        copyfileobj(infile, outfile)


def install_compressed_xml(
    corpus: Corpus, bz2file: ExportInput, marker: OutputMarker, export_path: str, host: str | None
) -> None:
    """Install XML file.

    Args:
        corpus: Corpus name.
        bz2file: Path to the bz2 file.
        marker: Installation marker to write.
        export_path: Path to the export directory to install to.
        host: Optional host name to install to.
    """
    filename = corpus + ".xml.bz2"
    remote_file_path = Path(export_path) / filename
    util.install.install_path(bz2file, host, remote_file_path)
    marker.write()


def uninstall_compressed_xml(corpus: Corpus, marker: OutputMarker, export_path: str, host: str | None) -> None:
    """Uninstall XML file.

    Args:
        corpus: Corpus name.
        marker: Uninstallation marker to write.
        export_path: Path to the export directory to uninstall from.
        host: Optional host name to uninstall from.
    """
    remote_file_path = Path(export_path) / (corpus + ".xml.bz2")
    util.install.uninstall_path(remote_file_path, host)
    marker.write()
