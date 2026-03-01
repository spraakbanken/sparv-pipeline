"""Export annotated corpus data to format-preserved xml."""

import xml.etree.ElementTree as etree  # noqa: N813
from pathlib import Path

from sparv.api import (
    AnnotationData,
    Config,
    Export,
    ExportAnnotations,
    HeaderAnnotations,
    Namespaces,
    SourceAnnotations,
    SourceFilename,
    SparvErrorMessage,
    Text,
    exporter,
    get_logger,
    util,
)

from . import xml_utils

logger = get_logger(__name__)


@exporter(
    "XML export preserving whitespaces from source file",
    config=[
        Config(
            "xml_export.filename_formatted",
            default="{file}_export.xml",
            description="Filename pattern for resulting XML files, with '{file}' representing the source name.",
            datatype=str,
            pattern=r".*\{file\}.*",
        )
    ],
)
def preserved_format(
    source_file: SourceFilename = SourceFilename(),
    text: Text = Text(),
    fileid: AnnotationData = AnnotationData("<fileid>"),
    out: Export = Export("xml_export.preserved_format/[xml_export.filename_formatted]"),
    annotations: ExportAnnotations = ExportAnnotations("xml_export.annotations"),
    source_annotations: SourceAnnotations = SourceAnnotations("xml_export.source_annotations"),
    header_annotations: HeaderAnnotations = HeaderAnnotations("xml_export.header_annotations"),
    remove_namespaces: bool = Config("export.remove_module_namespaces", False),
    sparv_namespace: str = Config("export.sparv_namespace"),
    source_namespace: str = Config("export.source_namespace"),
    include_empty_attributes: bool = Config("xml_export.include_empty_attributes"),
) -> None:
    """Export annotations to XML in export_dir and keep whitespaces and indentation from original file.

    Args:
        source_file: Name of the source file.
        text: The corpus text.
        fileid: Annotation with file IDs.
        out: Path and filename pattern for resulting file.
        annotations: List of elements:attributes (annotations) to include.
        source_annotations: List of elements:attributes from the source file
            to be kept. If not specified, everything will be kept.
        header_annotations: List of header elements from the source file to include
            in the export. If not specified, all headers will be kept.
        remove_namespaces: Whether to remove module "namespaces" from element and attribute names.
            Disabled by default.
        sparv_namespace: The namespace to be added to all Sparv annotations.
        source_namespace: The namespace to be added to all annotations present in the source.
        include_empty_attributes: Whether to include attributes even when they are empty. Disabled by default.

    Raises:
        SparvErrorMessage: If the root tag is missing.
    """
    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Read corpus text, file ID and XML namespaces
    corpus_text = text.read()
    fileid = fileid.read()
    xml_namespaces = Namespaces(source_file).read()

    # Get annotation spans, annotations list etc.
    annotation_list, _, export_names = util.export.get_annotation_names(
        annotations,
        source_annotations,
        source_file=source_file,
        remove_namespaces=remove_namespaces,
        sparv_namespace=sparv_namespace,
        source_namespace=source_namespace,
        xml_mode=True,
    )
    h_annotations, h_export_names = util.export.get_header_names(header_annotations, xml_namespaces)
    export_names.update(h_export_names)
    xml_utils.replace_invalid_chars_in_names(export_names)
    span_positions, annotation_dict = util.export.gather_annotations(
        annotation_list, export_names, h_annotations, source_file=source_file, flatten=False, split_overlaps=True
    )
    sorted_positions = [(pos, span[0], span[1]) for pos, spans in sorted(span_positions.items()) for span in spans]

    # Root tag sanity check
    if not xml_utils.valid_root(sorted_positions[0], sorted_positions[-1], true_root=True):
        raise SparvErrorMessage(
            "Root tag is missing! If you have manually specified which elements to include, "
            "make sure to include an element that encloses all other included elements and "
            "text content (including whitespace characters such as newlines)."
        )

    # Register XML namespaces
    xml_utils.register_namespaces(xml_namespaces)

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
                tail_span.node.tail = corpus_text[last_pos : span.start]
                last_pos = span.start

            # Handle headers
            if span.is_header:
                header = annotation_dict[span.name][util.constants.HEADER_CONTENTS][span.index]
                header_xml = etree.fromstring(header)
                header_xml.tag = span.export  # Rename element if needed
                span.node = header_xml
                node_stack[-1].node.append(header_xml)
            else:
                if node_stack:  # Don't create root node, it already exists
                    span.set_node(parent_node=node_stack[-1].node)

                xml_utils.add_attrs(
                    span.node, span.name, annotation_dict, export_names, span.index, include_empty_attributes
                )
                if span.overlap_id:
                    if sparv_namespace:
                        span.node.set(f"{sparv_namespace}.{util.constants.OVERLAP_ATTR}", f"{fileid}-{span.overlap_id}")
                    else:
                        span.node.set(
                            f"{util.constants.SPARV_DEFAULT_NAMESPACE}.{util.constants.OVERLAP_ATTR}",
                            f"{fileid}-{span.overlap_id}",
                        )
                node_stack.append(span)

                # Set text if there should be any between this node and the next one
                next_item = sorted_positions[x + 1]
                if next_item[1] == "open" and next_item[2].start > span.start:
                    span.node.text = corpus_text[last_pos : next_item[2].start]
                    last_pos = next_item[2].start

        # Close node
        else:
            if span.is_header:
                continue
            if last_pos < span.end:
                # Set node text if necessary
                if span.start == last_pos:
                    span.node.text = corpus_text[last_pos : span.end]
                # Set tail for previous node if necessary
                else:
                    # Get last closing node in this position
                    _, tail_span = [i for i in span_positions[last_pos] if i[0] == "close"][-1]
                    tail_span.node.tail = corpus_text[last_pos : span.end]
                last_pos = span.end

            # Make sure closing node == top stack node
            assert span == node_stack[-1], f"Overlapping elements found: {node_stack[-2:]}"
            # Pop stack and move on to next span
            node_stack.pop()

    # Write xml to file
    etree.ElementTree(root_span.node).write(out, encoding="unicode", method="xml", xml_declaration=True)
    logger.info("Exported: %s", out)
