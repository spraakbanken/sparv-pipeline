"""`sparv.api.util.export` provides utility functions for preparing data for export."""

from __future__ import annotations

import re
import xml.etree.ElementTree as etree  # noqa: N813
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from copy import deepcopy
from itertools import combinations
from typing import Any

from sparv.api import (
    Annotation,
    AnnotationAllSourceFiles,
    ExportAnnotations,
    ExportAnnotationsAllSourceFiles,
    HeaderAnnotations,
    Namespaces,
    SourceAnnotations,
    SourceAnnotationsAllSourceFiles,
    SparvErrorMessage,
    get_logger,
    util,
)
from sparv.core import io

from .constants import SPARV_DEFAULT_NAMESPACE, XML_NAMESPACE_SEP

logger = get_logger(__name__)


def gather_annotations(
    annotations: list[Annotation],
    export_names: dict[str, str],
    header_annotations: list[Annotation] | None = None,
    source_file: str | None = None,
    flatten: bool = True,
    split_overlaps: bool = False,
) -> tuple[list[tuple], dict[str, dict]]:
    """Calculate the span hierarchy and the `annotation_dict` containing all annotation elements and attributes.

    Args:
        annotations: List of annotations to include.
        export_names: Dictionary that maps from annotation names to export names.
        header_annotations: List of header annotations.
        source_file: The source filename.
        flatten: Whether to return the spans as a flat list.
        split_overlaps: Whether to split up overlapping spans.

    Returns:
        A `spans_dict` and an `annotation_dict` if `flatten` is `True`, otherwise returns `span_positions` and
            `annotation_dict`.

    Raises:
        SparvErrorMessage: If the source file is not found for header annotations.
    """

    class Span:
        """Object to store span information."""

        __slots__ = (
            "end",
            "end_sub",
            "export",
            "index",
            "is_header",
            "name",
            "node",
            "overlap_id",
            "start",
            "start_sub",
        )

        def __init__(
            self,
            name: str,
            index: int,
            start: tuple[int, ...],
            end: tuple[int, ...],
            export_names: dict[str, str],
            is_header: bool,
        ) -> None:
            """Set attributes."""
            self.name = name
            self.index = index
            self.start = start[0]
            self.end = end[0]
            self.start_sub = start[1] if len(start) > 1 else False
            self.end_sub = end[1] if len(end) > 1 else False
            self.export = export_names.get(self.name, self.name)
            self.is_header = is_header
            self.node = None
            self.overlap_id = None

        def set_node(self, parent_node: etree.Element | None = None) -> None:
            """Create an XML node under parent_node.

            Args:
                parent_node: The parent node to create the XML node under. If None, create a root node.
            """
            if parent_node is not None:
                self.node = etree.SubElement(parent_node, self.export)
            else:
                self.node = etree.Element(self.export)

        def __repr__(self) -> str:
            """Stringify the most interesting span info (for debugging mostly).

            Returns:
                A string representation of the span.
            """
            if self.export != self.name:
                return f"<{self.name}/{self.export} {self.index} {self.start}-{self.end}>"
            return f"<{self.name} {self.index} {self.start}-{self.end}>"

        def __lt__(self, other_span: Span) -> bool:
            """Return True if other_span comes after this span.

            Sort spans according to their position and hierarchy. Sort by:
            1. start position (smaller indices first)
            2. end position (larger indices first)
            3. the calculated element hierarchy
            """

            def get_sort_key(
                span: Span, hierarchy: int, sub_positions: bool = False, empty_span: bool = False
            ) -> tuple:
                """Return a sort key for span which makes span comparison possible."""
                if empty_span:
                    if sub_positions:
                        return (span.start, span.start_sub), hierarchy, (span.end, span.end_sub)
                    return span.start, hierarchy, span.end
                else:  # noqa: RET505
                    if sub_positions:
                        return (span.start, span.start_sub), (-span.end, -span.end_sub), hierarchy
                    return span.start, -span.end, hierarchy

            if self.name in elem_hierarchy and other_span.name in elem_hierarchy[self.name]:
                self_hierarchy = elem_hierarchy[self.name][other_span.name]
                other_hierarchy = 0 if self_hierarchy == 1 else 1
            else:
                self_hierarchy = other_hierarchy = -1

            # Sort empty spans according to hierarchy or put them first
            if (self.start, self.start_sub) == (self.end, self.end_sub) or (other_span.start, other_span.start_sub) == (
                other_span.end,
                other_span.end_sub,
            ):
                sort_key1 = get_sort_key(self, self_hierarchy, empty_span=True)
                sort_key2 = get_sort_key(other_span, other_hierarchy, empty_span=True)
            # Both spans have sub positions
            elif self.start_sub is not False and other_span.start_sub is not False:
                sort_key1 = get_sort_key(self, self_hierarchy, sub_positions=True)
                sort_key2 = get_sort_key(other_span, other_hierarchy, sub_positions=True)
            # At least one of the spans does not have sub positions
            else:
                sort_key1 = get_sort_key(self, self_hierarchy)
                sort_key2 = get_sort_key(other_span, other_hierarchy)

            return sort_key1 < sort_key2

    if header_annotations is None:
        header_annotations = []

    # Collect annotation information and list of all annotation spans
    annotation_dict = defaultdict(dict)
    spans_list = []
    for annots, is_header in ((annotations, False), (header_annotations, True)):
        for annotation in sorted(annots):
            base_name, attr = annotation.split()
            if not attr:
                annotation_dict[base_name] = {}
                for i, s in enumerate(annotation.read_spans(decimals=True)):
                    spans_list.append(Span(base_name, i, s[0], s[1], export_names, is_header))
            # TODO: assemble all attrs first and use read_annotation_attributes
            if attr and not annotation_dict[base_name].get(attr):
                annotation_dict[base_name][attr] = list(annotation.read())
            elif is_header:
                try:
                    annotation_dict[base_name][util.constants.HEADER_CONTENTS] = list(
                        Annotation(f"{base_name}:{util.constants.HEADER_CONTENTS}", source_file=source_file).read()
                    )
                except FileNotFoundError:
                    raise SparvErrorMessage(
                        f"Could not find data for XML header '{base_name}'. "
                        "Was this element listed in 'xml_import.header_elements'?"
                    ) from None

    # Calculate hierarchy (if needed) and sort the span objects
    elem_hierarchy = calculate_element_hierarchy(source_file, spans_list)
    sorted_spans = sorted(spans_list)

    # Add position information to sorted_spans
    spans_dict = defaultdict(list)
    for span in sorted_spans:
        # Treat empty spans differently
        if span.start == span.end:
            insert_index = len(spans_dict[span.start])
            if span.name in elem_hierarchy:
                for i, (instruction, s) in enumerate(spans_dict[span.start]):
                    if (
                        instruction == "close"
                        and s.name in elem_hierarchy[span.name]
                        and elem_hierarchy[span.name][s.name] == 1
                    ):
                        insert_index = i
                        break
            spans_dict[span.start].insert(insert_index, ("open", span))
            spans_dict[span.end].insert(insert_index + 1, ("close", span))
        else:
            # Append opening spans; prepend closing spans
            spans_dict[span.start].append(("open", span))
            spans_dict[span.end].insert(0, ("close", span))

    # Should overlapping spans be split?
    if split_overlaps:
        _handle_overlaps(spans_dict)

    # Return the span_dict without converting to list first
    if not flatten:
        return spans_dict, annotation_dict

    # Flatten structure
    span_positions = [(pos, span[0], span[1]) for pos, spans in sorted(spans_dict.items()) for span in spans]
    return span_positions, annotation_dict


def _handle_overlaps(spans_dict: dict[int, list[tuple]]) -> None:
    """Handle overlapping spans by splitting them and assigning unique IDs to maintain their original relationships.

    Overlapping spans, such as <aaa> ... <b> ... </aaa> ... </b>, need to be split for certain export formats,
    like XML, which do not support overlapping tags.

    Args:
        spans_dict: A dictionary mapping span positions to the spans that open and close at those positions.
    """
    span_stack = []
    overlap_count = 0
    for position in sorted(spans_dict):
        subposition_shift = 0
        for subposition, (event, span) in enumerate(spans_dict[position].copy()):
            if event == "open":
                span_stack.append(span)
            elif event == "close":
                closing_span = span_stack.pop()
                if closing_span != span:
                    # Overlapping spans found
                    overlap_stack = []

                    # Close all overlapping spans and add an overlap ID to them
                    while closing_span != span:
                        overlap_count += 1
                        closing_span.overlap_id = overlap_count

                        # Create a copy of this span, to be reopened after we close this one
                        new_span = deepcopy(closing_span)
                        new_span.start = span.end
                        overlap_stack.append(new_span)

                        # Replace the original overlapping span with the new copy
                        end_subposition = spans_dict[closing_span.end].index(("close", closing_span))
                        spans_dict[closing_span.end][end_subposition] = ("close", new_span)

                        # Close this overlapping span
                        closing_span.end = span.end
                        spans_dict[position].insert(subposition + subposition_shift, ("close", closing_span))
                        subposition_shift += 1

                        # Fetch a new closing span from the stack
                        closing_span = span_stack.pop()

                    # Re-open overlapping spans
                    while overlap_stack:
                        overlap_span = overlap_stack.pop()
                        span_stack.append(overlap_span)
                        spans_dict[position].insert(subposition + subposition_shift + 1, ("open", overlap_span))
                        subposition_shift += 1


def calculate_element_hierarchy(source_file: str, spans_list: list) -> dict[str, dict[str, int]]:
    """Calculate the hierarchy for spans with identical start and end positions.

    If two spans A and B have identical start and end positions, go through all occurrences of A and B
    and check which element is most often parent to the other.

    Args:
        source_file: The source filename.
        spans_list: List of spans to check for hierarchy.

    Returns:
        A dictionary with the hierarchy of spans.
    """
    # Find elements with identical spans
    span_duplicates = defaultdict(set)
    startend_positions = defaultdict(set)
    empty_span_starts = defaultdict(set)
    for span in spans_list:
        # We don't include sub-positions here as we still need to compare spans with sub-positions with spans without
        span_duplicates[span.start, span.end].add(span.name)
        if (span.start, span.start_sub) == (span.end, span.end_sub):
            empty_span_starts[span.name].add(span.start)
        else:
            startend_positions[span.start].add(span.name)
            startend_positions[span.end].add(span.name)
    span_duplicates = {tuple(sorted(v)) for v in span_duplicates.values() if len(v) > 1}

    # Add empty spans and spans with identical start positions
    empty_spans = set()
    for empty_span, span_starts in empty_span_starts.items():
        for span_start in span_starts:
            empty_spans.update(tuple(sorted((empty_span, a))) for a in startend_positions[span_start])

    # Get pairs of relations that need to be ordered
    relation_pairs = set()
    for collisions in span_duplicates:
        relation_pairs.update(combinations(collisions, r=2))
    relation_pairs.update(empty_spans)

    hierarchy = defaultdict(dict)

    # Calculate parent-child relation for every pair
    for a, b in relation_pairs:
        a_annot = Annotation(a, source_file=source_file)
        b_annot = Annotation(b, source_file=source_file)
        a_parent = len([i for i in (b_annot.get_parents(a_annot)) if i is not None])
        b_parent = len([i for i in (a_annot.get_parents(b_annot)) if i is not None])
        if a_parent > b_parent:
            hierarchy[a][b] = 0
            hierarchy[b][a] = 1
        elif a_parent < b_parent:
            hierarchy[b][a] = 0
            hierarchy[a][b] = 1

    return hierarchy


def get_annotation_names(
    annotations: ExportAnnotations
    | ExportAnnotationsAllSourceFiles
    | list[tuple[Annotation | AnnotationAllSourceFiles, str | None]],
    source_annotations: SourceAnnotations | SourceAnnotationsAllSourceFiles = None,
    source_file: str | None = None,
    token_name: str | None = None,
    remove_namespaces: bool = False,
    keep_struct_names: bool = False,
    sparv_namespace: str | None = None,
    source_namespace: str | None = None,
    xml_mode: bool | None = False,
) -> tuple[list[Annotation | AnnotationAllSourceFiles], list[str], dict[str, str]]:
    """Get a list of annotations, token attributes, and a dictionary translating annotation names to export names.

    Args:
        annotations: List of elements:attributes (annotations) to include, with possible export names.
        source_annotations: List of elements:attributes from the source file to include, with possible export names. If
            not specified, includes everything.
        source_file: Name of the source file.
        token_name: Name of the token annotation.
        remove_namespaces: Set to `True` to remove all namespaces in `export_names` unless names are ambiguous.
        keep_struct_names: Set to `True` to include the annotation base name (everything before ":") in `export_names`
            for annotations that are not token attributes.
        sparv_namespace: Namespace to add to all Sparv annotations.
        source_namespace: Namespace to add to all annotations from the source file.
        xml_mode: Set to `True` to use XML namespaces in `export_names`.

    Returns:
        A list of annotations, a list of token attribute names, a dictionary with translation from annotation names to
            export names.
    """
    # Combine all annotations
    all_annotations = _remove_duplicates(list(annotations) + list(source_annotations or []))

    if token_name:
        # Get the names of all token attributes
        token_attributes = [
            a[0].attribute_name
            for a in all_annotations
            if a[0].annotation_name == token_name and a[0].name != token_name
        ]
    else:
        token_attributes = []

    # Get XML namespaces
    xml_namespaces = Namespaces(source_file).read()

    export_names = _create_export_names(
        all_annotations,
        token_name,
        remove_namespaces,
        keep_struct_names,
        list(source_annotations or []),
        sparv_namespace,
        source_namespace,
        xml_namespaces,
        xml_mode=xml_mode,
    )

    return [i[0] for i in all_annotations], token_attributes, export_names


def get_header_names(
    header_annotations: HeaderAnnotations | None,
    xml_namespaces: dict[str, str],
) -> tuple[list[Annotation], dict[str, str]]:
    """Get a list of header annotations and a dictionary for renamed annotations.

    Args:
        header_annotations: List of header annotations from the source file to include. If not specified,
            includes everything.
        xml_namespaces: XML namespaces to use for the header annotations.

    Returns:
        A list of header annotations and a dictionary with translation from annotation names to export names.
    """
    export_names = _create_export_names(
        list(header_annotations), None, False, keep_struct_names=False, xml_namespaces=xml_namespaces, xml_mode=True
    )

    return [a[0] for a in header_annotations], export_names


def _remove_duplicates(
    annotation_tuples: list[tuple[Annotation | AnnotationAllSourceFiles, str | None]],
) -> list[tuple]:
    """Remove duplicates from annotation_tuples without changing the order.

    Args:
        annotation_tuples: List of tuples containing annotations and their export names.

    Returns:
        A list of tuples with unique annotations and their export names.
    """
    new_annotations = OrderedDict()
    for a, new_name in annotation_tuples:
        if a not in new_annotations or new_name is not None:
            new_annotations[a] = new_name
    return list(new_annotations.items())


def _create_export_names(
    annotations: list[tuple[Annotation | AnnotationAllSourceFiles, str | None]],
    token_name: str | None,
    remove_namespaces: bool,
    keep_struct_names: bool,
    source_annotations: Iterable[tuple[Annotation | AnnotationAllSourceFiles, str | None]] = (),
    sparv_namespace: str | None = None,
    source_namespace: str | None = None,
    xml_namespaces: dict | None = None,
    xml_mode: bool | None = False,
) -> dict[str, str]:
    """Create dictionary with translation from annotation names to export names.

    Args:
        annotations: List of tuples containing annotations and their export names.
        token_name: Name of the token annotation.
        remove_namespaces: Set to `True` to remove all namespaces from the export names unless names are ambiguous.
        keep_struct_names: Set to `True` to include the annotation base name (everything before ":") in the export names
            for annotations that are not token attributes.
        source_annotations: List of source annotations.
        sparv_namespace: Namespace to add to all Sparv annotations.
        source_namespace: Namespace to add to all annotations from the source file.
        xml_namespaces: Dictionary of XML namespaces.
        xml_mode: Set to `True` to use XML namespaces in the export names.

    Returns:
        A dictionary with translation from annotation names to export names.
    """
    if remove_namespaces:

        def shorten(annotation: Annotation | AnnotationAllSourceFiles) -> str:
            """Shorten annotation name or attribute name.

            For example:
                segment.token -> token
                segment.token:saldo.baseform -> segment.token:baseform

            Args:
                annotation: The annotation to shorten.

            Returns:
                The shortened annotation name.
            """

            def remove_before_dot(name: str) -> str:
                # Always remove "custom."
                name = name.removeprefix("custom.")
                # Remove everything before first "."
                if "." in name:
                    name = name.split(".", 1)[1]
                return name

            if annotation.attribute_name:
                short = io.join_annotation(annotation.annotation_name, remove_before_dot(annotation.attribute_name))
            else:
                short = io.join_annotation(remove_before_dot(annotation.annotation_name), None)
            return short

        # Create short names dictionary and count
        short_names_count = defaultdict(int)
        short_names = {}
        for annotation, new_name in annotations:
            name = annotation.name
            if new_name:
                # If attribute, combine new attribute name with base annotation name
                short_name = io.join_annotation(annotation.annotation_name, new_name) if ":" in name else new_name
            else:
                # Don't remove namespaces from elements and attributes contained in the source files
                short_name = name if (annotation, new_name) in source_annotations else shorten(annotation)
            short_names_count[short_name] += 1
            base, attr = Annotation(short_name).split()
            short_names[name] = attr or base

        export_names = {}
        for annotation, new_name in sorted(annotations):  # Sorted in order to handle annotations before attributes
            name = annotation.name
            if not new_name:
                # Only use short name if it's unique
                if "." in name and short_names_count[shorten(annotation)] == 1:
                    new_name = short_names[name]  # noqa: PLW2901
                else:
                    new_name = annotation.attribute_name or annotation.annotation_name  # noqa: PLW2901

            # Keep annotation base name (the part before ":") if this is not a token attribute
            if keep_struct_names and ":" in name and not name.startswith(token_name):
                base_name = annotation.annotation_name
                new_name = io.join_annotation(export_names.get(base_name, base_name), new_name)  # noqa: PLW2901
            export_names[name] = new_name
    else:  # noqa: PLR5501
        if keep_struct_names:
            export_names = {}
            for annotation, new_name in sorted(annotations):  # Sorted in order to handle annotations before attributes
                name = annotation.name
                if not new_name:
                    new_name = annotation.attribute_name or annotation.annotation_name  # noqa: PLW2901
                if ":" in name and not name.startswith(token_name):
                    base_name = annotation.annotation_name
                    new_name = io.join_annotation(export_names.get(base_name, base_name), new_name)  # noqa: PLW2901
                export_names[name] = new_name
        else:
            export_names = {
                annotation.name: (new_name or annotation.attribute_name or annotation.name)
                for annotation, new_name in annotations
            }

    export_names = _add_global_namespaces(
        export_names, annotations, source_annotations, sparv_namespace, source_namespace
    )
    export_names = _check_name_collision(export_names, source_annotations)

    # Take care of XML namespaces
    export_names = {k: _get_xml_tagname(v, xml_namespaces, xml_mode) for k, v in export_names.items()}

    return export_names  # noqa: RET504


def _get_xml_tagname(tag: str, xml_namespaces: dict, xml_mode: bool = False) -> str:
    """Take care of namespaces by looking up URIs for prefixes (if xml_mode=True) or by converting to dot notation.

    Args:
        tag: The tag name to convert.
        xml_namespaces: A dictionary of XML namespaces.
        xml_mode: If `True`, convert prefixes to URIs.

    Returns:
        The converted tag name.

    Raises:
        SparvErrorMessage: If the namespace prefix is not found in `xml_namespaces`.
    """
    sep = re.escape(XML_NAMESPACE_SEP)
    m = re.match(rf"(.*){sep}(.+)", tag)
    if m:
        if xml_mode:
            # Replace prefix+tag with {uri}tag
            uri = xml_namespaces.get(m.group(1), "")
            if not uri:
                raise SparvErrorMessage(
                    f"You are trying to export the annotation '{tag}' but no URI was found for the "
                    f"namespace prefix '{m.group(1)}'!"
                )
            return re.sub(rf"(.*){sep}(.+)", rf"{{{uri}}}\2", tag)
        elif m.group(1):  # noqa: RET505
            # Replace "prefix+tag" with "prefix.tag", skip this for default namespaces
            return re.sub(rf"(.*){sep}(.+)", r"\1.\2", tag)
    return tag


def _add_global_namespaces(
    export_names: dict,
    annotations: list[tuple[Annotation | AnnotationAllSourceFiles, Any]],
    source_annotations: Iterable,
    sparv_namespace: str | None = None,
    source_namespace: str | None = None,
) -> dict:
    """Add sparv_namespace and source_namespace to export names.

    Args:
        export_names: Dictionary with export names.
        annotations: List of all Sparv annotations for the corpus.
        source_annotations: List of source annotations.
        sparv_namespace: Namespace to add to all Sparv annotations.
        source_namespace: Namespace to add to all annotations from the source file.

    Returns:
        A dictionary with updated export names.
    """
    source_annotation_names = [a.name for a, _ in source_annotations]

    if sparv_namespace:
        for a, _ in annotations:
            name = a.name
            if name not in source_annotation_names:
                export_names[name] = f"{sparv_namespace}.{export_names.get(name, name)}"

    if source_namespace:
        for name in source_annotation_names:
            export_names[name] = f"{source_namespace}.{export_names.get(name, name)}"

    return export_names


def _check_name_collision(export_names: dict, source_annotations: Iterable) -> dict:
    """Detect collisions in attribute names and resolve them or send warnings.

    Args:
        export_names: Dictionary with export names.
        source_annotations: List of source annotations.

    Returns:
        A dictionary with updated export names.
    """
    source_names = [a.name for a, _ in source_annotations]

    # Get annotations with identical export attribute names
    reverse_index = defaultdict(set)
    for k, v in export_names.items():
        if ":" in k:
            reverse_index[v].add(k)
    possible_collisions = {k: [Annotation(v) for v in values] for k, values in reverse_index.items() if len(values) > 1}
    # Only keep the ones with matching element names
    for attr, values in possible_collisions.items():
        attr_dict = defaultdict(list)
        for v in values:
            attr_dict[v.annotation_name].append(v)
        attr_collisions = {k: v for k, v in attr_dict.items() if len(v) > 1}
        for annots in attr_collisions.values():
            # If there are two colliding attributes and one is an automatic one, prefix it with SPARV_DEFAULT_NAMESPACE
            if len(annots) == 2 and len([a for a in annots if a.name not in source_names]) == 1:  # noqa: PLR2004
                sparv_annot = annots[0] if annots[0].name not in source_names else annots[1]
                source_annot = annots[0] if annots[0].name in source_names else annots[1]
                new_name = SPARV_DEFAULT_NAMESPACE + "." + export_names[sparv_annot.name]
                export_names[sparv_annot.name] = new_name
                logger.info(
                    "Changing name of automatic annotation '%s' to '%s' due to collision with '%s'.",
                    sparv_annot.name,
                    new_name,
                    source_annot.name,
                )
            # Warn the user if we cannot resolve collisions automatically
            else:
                annots_string = "\n".join(
                    [f"{a.name} ({'source' if a.name in source_names else 'sparv'} annotation)" for a in annots]
                )
                logger.warning(
                    "The following annotations are exported with the same name (%s) and might overwrite "
                    "each other: \n\n%s\n\nIf you want to keep all of these annotations you can change "
                    "their export names.",
                    attr,
                    annots_string,
                )
    return export_names


################################################################################
# Scrambling
################################################################################


def scramble_spans(span_positions: list[tuple], chunk_name: str, chunk_order: Annotation) -> list[tuple]:
    """Reorder spans based on `chunk_order` and ensure tags are opened and closed correctly.

    Args:
        span_positions: Original span positions, typically obtained from `gather_annotations()`.
        chunk_name: Name of the annotation to reorder.
        chunk_order: Annotation specifying the new order of the chunks.

    Returns:
        List of tuples with the new span positions and instructions.
    """
    new_s_order = _reorder_spans(span_positions, chunk_name, chunk_order)
    _fix_parents(new_s_order, chunk_name)

    # Reformat span positions
    new_span_positions = [v for k, v in sorted(new_s_order.items())]  # Sort dict into list
    new_span_positions = [t for s in new_span_positions for t in s]  # Unpack chunks
    new_span_positions = [(0, instruction, span) for instruction, span in new_span_positions]  # Add fake position (0)

    return new_span_positions  # noqa: RET504


def _reorder_spans(span_positions: list[tuple], chunk_name: str, chunk_order: Annotation) -> dict:
    """Scramble chunks according to the chunk_order.

    Args:
        span_positions: Original span positions, typically obtained from `gather_annotations()`.
        chunk_name: Name of the annotation to reorder.
        chunk_order: Annotation specifying the new order of the chunks.

    Returns:
        Dictionary with the new span positions and instructions.
    """
    new_s_order = defaultdict(list)
    parent_stack = []
    temp_stack = []
    current_s_index = None
    last_s_index = None

    for _pos, instruction, span in span_positions:
        if instruction == "open":
            if span.name == chunk_name and current_s_index is None:  # Check current_s_index to avoid nested chunks
                current_s_index = int(chunk_order[span.index])

                for temp_instruction, temp_span in temp_stack:
                    if current_s_index == last_s_index:
                        # Continuing split annotation
                        new_s_order[current_s_index].append((temp_instruction, temp_span))

                    if temp_instruction == "open":
                        parent_stack.append((temp_instruction, temp_span))
                    elif temp_instruction == "close" and parent_stack[-1][1] == temp_span:
                        parent_stack.pop()

                temp_stack = []

                # If this is the start of this chunk, add all open parents first
                if not new_s_order[current_s_index]:
                    new_s_order[current_s_index].extend(parent_stack)
                new_s_order[current_s_index].append((instruction, span))
            elif current_s_index is not None:
                # Encountered child to chunk
                new_s_order[current_s_index].append((instruction, span))
            else:
                # Encountered parent to chunk
                temp_stack.append((instruction, span))

        elif instruction == "close":
            if current_s_index is not None:
                # Encountered child to chunk
                new_s_order[current_s_index].append((instruction, span))
                # If chunk, check index to make sure it's the right chunk and not a nested one
                if span.name == chunk_name and int(chunk_order[span.index]) == current_s_index:
                    last_s_index = current_s_index
                    current_s_index = None
            else:
                # Encountered parent to chunk
                temp_stack.append((instruction, span))

    return new_s_order


def _fix_parents(new_s_order: dict, chunk_name: str) -> None:
    """Go through new_s_order, remove duplicate opened parents and close parents.

    Args:
        new_s_order: Dictionary with the new span positions and instructions.
        chunk_name: Name of the annotation used to reorder the chunks.
    """
    open_parents = []
    new_s_order_indices = sorted(new_s_order.keys())
    for i, s_index in enumerate(new_s_order_indices):
        chunk = new_s_order[s_index]
        is_parent = True
        current_chunk_index = None
        for instruction, span in chunk:
            if instruction == "open":
                if span.name == chunk_name and current_chunk_index is None:
                    is_parent = False
                    current_chunk_index = span.index
                elif is_parent:
                    open_parents.append((instruction, span))
            else:  # "close"  # noqa: PLR5501
                # If chunk, check index to make sure it's the right chunk and not a nested one
                if span.name == chunk_name and span.index == current_chunk_index:
                    is_parent = True
                    current_chunk_index = None
                elif is_parent:
                    if open_parents[-1][1] == span:
                        open_parents.pop()
        # Check next chunk: close parents in current chunk that are not part of next chunk and
        # remove already opened parents from next chunk
        if i < len(new_s_order_indices) - 1:  # noqa: SIM108
            next_chunk = new_s_order[new_s_order_indices[i + 1]]
        else:
            next_chunk = []
        for p in reversed(open_parents):
            if p in next_chunk:
                next_chunk.remove(p)
            else:
                chunk.append(("close", p[1]))
                open_parents.remove(p)
