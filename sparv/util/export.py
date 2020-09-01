"""Util functions for corpus export."""

import logging
import xml.etree.ElementTree as etree
from collections import defaultdict
from copy import deepcopy
from itertools import combinations
from typing import Any, List, Optional, Set, Tuple, Union

from sparv.util.classes import ExportAnnotations, Annotation, AnnotationAllDocs, ExportAnnotationsAllDocs
from sparv.util import corpus, misc, parent

log = logging.getLogger(__name__)


def gather_annotations(annotations: List[Annotation],
                       export_names,
                       header_annotations=None,
                       doc: Optional[str] = None,
                       flatten: bool = True,
                       split_overlaps: bool = False):
    """Calculate the span hierarchy and the annotation_dict containing all annotation elements and attributes.

    Args:
        annotations: List of annotations to include
        export_names: Dictionary that maps from annotation names to export names
        header_annotations: List of header annotations
        doc: The document name
        flatten: Whether to return the spans as a flat list
        split_overlaps: Whether to split up overlapping spans
    """
    class Span:
        """Object to store span information."""

        __slots__ = [
            "name",
            "index",
            "start",
            "end",
            "start_sub",
            "end_sub",
            "export",
            "is_header",
            "node",
            "overlap_id"
        ]

        def __init__(self, name, index, start, end, export_names, is_header):
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

        def set_node(self, parent_node=None):
            """Create an XML node under parent_node."""
            if parent_node is not None:
                self.node = etree.SubElement(parent_node, self.export)
            else:
                self.node = etree.Element(self.export)

        def __repr__(self):
            """Stringify the most interesting span info (for debugging mostly)."""
            if self.export != self.name:
                return "<%s/%s %s %s-%s>" % (self.name, self.export, self.index, self.start, self.end)
            return "<%s %s %s-%s>" % (self.name, self.index, self.start, self.end)

        def __lt__(self, other_span):
            """Return True if other_span comes after this span.

            Sort spans according to their position and hierarchy. Sort by:
            1. start position (smaller indices first)
            2. end position (larger indices first)
            3. the calculated element hierarchy
            """
            def get_sort_key(span, sub_positions=False):
                """Return a sort key for span which makes span comparison possible."""
                hierarchy_index = elem_hierarchy.index(span.name) if span.name in elem_hierarchy else -1
                if sub_positions:
                    return (span.start, span.start_sub), (-span.end, -span.end_sub), hierarchy_index
                else:
                    return span.start, -span.end, hierarchy_index

            # Both spans have sub positions
            if self.start_sub and other_span.start_sub:
                sort_key1 = get_sort_key(self, sub_positions=True)
                sort_key2 = get_sort_key(other_span, sub_positions=True)
            # At least one of the spans does not have sub positions
            else:
                sort_key1 = get_sort_key(self)
                sort_key2 = get_sort_key(other_span)

            if sort_key1 < sort_key2:
                return True
            return False

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
                annotation_dict[base_name][corpus.HEADER_CONTENT] = list(
                    corpus.read_annotation(doc, f"{base_name}:{corpus.HEADER_CONTENT}", allow_newlines=True))

    # Calculate hierarchy (if needed) and sort the span objects
    elem_hierarchy = calculate_element_hierarchy(doc, spans_list)
    sorted_spans = sorted(spans_list)

    # Add position information to sorted_spans
    spans_dict = defaultdict(list)
    for span in sorted_spans:
        if span.start == span.end:
            spans_dict[span.start].append(("open", span))
            spans_dict[span.end].append(("close", span))
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


def _handle_overlaps(spans_dict):
    """Split overlapping spans and give them unique IDs to preserve their original connection."""
    span_stack = []
    overlap_count = 0
    for position in sorted(spans_dict):
        for subposition, (event, span) in enumerate(spans_dict[position].copy()):
            subposition_shift = 0
            if event == "open":
                span_stack.append(span)
            elif event == "close":
                closing_span = span_stack.pop()
                if not closing_span == span:
                    # Overlapping spans found
                    overlap_stack = []

                    # Close all overlapping spans and add an overlap ID to them
                    while not closing_span == span:
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


def calculate_element_hierarchy(doc, spans_list):
    """Calculate the hierarchy for spans with identical start and end positions.

    If two spans A and B have identical start and end positions, go through all occurences of A and B
    and check which element is most often parent to the other. That one will be first.
    """
    # Find elements with identical spans
    span_duplicates = defaultdict(set)
    for span in spans_list:
        span_duplicates[(span.start, span.end)].add(span.name)
    span_duplicates = [v for k, v in span_duplicates.items() if len(v) > 1]

    # Flatten structure
    unclear_spans = set([elem for elem_set in span_duplicates for elem in elem_set])

    # Read all annotation spans for quicker access later
    read_items = {}
    for span in unclear_spans:
        read_items[span] = sorted(enumerate(corpus.read_annotation_spans(
                                  doc, span, decimals=True)), key=lambda x: x[1])

    # Get pairs of relations that need to be ordered
    relation_pairs = list(combinations(unclear_spans, r=2))
    # Order each pair into [parent, children]
    ordered_pairs = set()
    for a, b in relation_pairs:
        a_parent = len([i for i in (parent.get_parents(doc, read_items[a], read_items[b])) if i is not None])
        b_parent = len([i for i in (parent.get_parents(doc, read_items[b], read_items[a])) if i is not None])
        if a_parent > b_parent:
            ordered_pairs.add((a, b))
        else:
            ordered_pairs.add((b, a))

    hierarchy = []
    error_msg = "Something went wrong while sorting annotation elements. Could there be circular relations?"
    # Loop until all unclear_spans are processed
    while unclear_spans:
        size = len(unclear_spans)
        for span in unclear_spans.copy():
            # Span is never a child in ordered_pairs, then it is first in the hierarchy
            if not any([b == span for _a, b in ordered_pairs]):
                hierarchy.append(span)
                unclear_spans.remove(span)
                # Remove pairs from ordered_pairs where span is the parent
                for pair in ordered_pairs.copy():
                    if pair[0] == span:
                        ordered_pairs.remove(pair)
        # Check that unclear_spans is getting smaller, otherwise there might be circularity
        assert len(unclear_spans) < size, error_msg
    return hierarchy


def get_available_source_annotations(doc: Optional[str] = None, docs: Optional[List[str]] = None) -> Set[str]:
    """Get the set of available annotations generated from the source, either for a single document or multiple."""
    assert doc or docs, "Either 'doc' or 'docs' must be provided"
    available_source_annotations = set()
    if docs:
        for d in docs:
            available_source_annotations.update(corpus.read_data(d, corpus.STRUCTURE_FILE).split())
    else:
        available_source_annotations.update(corpus.read_data(doc, corpus.STRUCTURE_FILE).split())

    return available_source_annotations


def get_source_annotations(source_annotation_names: Optional[List[str]], doc: Optional[str] = None,
                           docs: Optional[List[str]] = None):
    """Given a list of source annotation names (and possible export names), return a list of annotation objects.

    If no names are provided all available source annotations will be returnd.
    """
    # Get list of available source annotation names
    available_source_annotations = get_available_source_annotations(doc, docs)

    # Parse list
    annotation_names = misc.parse_annotation_list(source_annotation_names)

    if not annotation_names:
        # Include all available annotations from source
        source_annotations = [(Annotation(a, doc) if doc else AnnotationAllDocs(a), None) for a in
                              available_source_annotations]
    else:
        # Make sure source_annotations doesn't include annotations not in source
        source_annotations = [(Annotation(a[0], doc) if doc else AnnotationAllDocs(a[0]), a[1]) for a in
                              annotation_names if a[0] in available_source_annotations]

    return source_annotations


def get_annotation_names(annotations: Union[ExportAnnotations, ExportAnnotationsAllDocs],
                         source_annotations=None,
                         doc: Optional[str] = None, docs: Optional[List[str]] = None,
                         token_name: Optional[str] = None,
                         remove_namespaces=False, keep_struct_names=False):
    """Get a list of annotations, token attributes and a dictionary for renamed annotations.

    Args:
        annotations:
        source_annotations:
        doc:
        docs:
        token_name:
        remove_namespaces: Remove all namespaces in export_names unless names are ambiguous.
        keep_struct_names: For structural attributes (anything other than token), include the annotation base name
            (everything before ":") in export_names (used in cwb encode).

    Returns:
        A list of annotations, a list of token attribute names, a dictionary with translation from annotation names to
        export names.
    """
    # Get source annotations
    source_annotations = get_source_annotations(source_annotations, doc, docs)

    # Combine all annotations
    all_annotations = _remove_duplicates(annotations + source_annotations)

    if token_name:
        # Get the names of all token attributes
        token_attributes = [a[0].attribute_name() for a in all_annotations
                            if a[0].annotation_name() == token_name and a[0].name != token_name]
    else:
        token_attributes = []

    export_names = _create_export_names(all_annotations, token_name, remove_namespaces, keep_struct_names,
                                        source_annotations)

    return [i[0] for i in all_annotations], token_attributes, export_names


def get_header_names(header_annotation_names: Optional[List[str]],
                     doc: Optional[str] = None,
                     docs: Optional[List[str]] = None):
    """Get a list of header annotations and a dictionary for renamed annotations."""
    annotation_names = misc.parse_annotation_list(header_annotation_names)
    if not annotation_names:
        # Get header_annotation_names from HEADERS_FILE if it exists
        if docs:
            annotation_names = []
            for d in docs:
                if corpus.data_exists(d, corpus.HEADERS_FILE):
                    annotation_names.extend(
                        misc.parse_annotation_list(corpus.read_data(d, corpus.HEADERS_FILE).splitlines()))
        elif corpus.data_exists(doc, corpus.HEADERS_FILE):
            annotation_names = misc.parse_annotation_list(corpus.read_data(doc, corpus.HEADERS_FILE).splitlines())

    header_annotations = [(Annotation(a[0], doc) if doc else AnnotationAllDocs(a[0]), a[1]) for a in
                          annotation_names]

    export_names = _create_export_names(header_annotations, None, False, keep_struct_names=False)

    return [a[0] for a in header_annotations], export_names


def _remove_duplicates(annotation_tuples):
    """Remove duplicates from annotation_tuples without changing the order."""
    new_annotations = []
    new_annotations_set = set()
    for a, new_name in annotation_tuples:
        if (a.name, new_name) not in new_annotations_set:
            new_annotations.append((a, new_name))
            new_annotations_set.add((a.name, new_name))
    return new_annotations


def _create_export_names(annotations: List[Tuple[Union[Annotation, AnnotationAllDocs], Any]],
                         token_name: Optional[str],
                         remove_namespaces: bool,
                         keep_struct_names: bool,
                         source_annotations: list = []):
    """Create dictionary for renamed annotations."""
    if remove_namespaces:
        def shorten(_name):
            """Shorten annotation name or attribute name.

            For example:
                segment.token -> token
                segment.token:saldo.baseform -> segment.token:baseform
            """
            annotation, attribute = corpus.split_annotation(_name)
            if attribute:
                short = corpus.join_annotation(annotation, attribute.split(".")[-1])
            else:
                short = corpus.join_annotation(annotation.split(".")[-1], None)
            return short

        # Create short names dictionary and count
        short_names_count = defaultdict(int)
        short_names = {}
        for annotation, new_name in annotations:
            name = annotation.name
            # Don't remove namespaces from elements and attributes contained in the original documents
            if (annotation, new_name) in source_annotations:
                short_name = name
            else:
                short_name = shorten(name)
            if new_name:
                if ":" in name:
                    # Combine new attribute name with base annotation name
                    short_name = corpus.join_annotation(annotation.annotation_name(), new_name)
                else:
                    short_name = new_name
            short_names_count[short_name] += 1
            base, attr = corpus.split_annotation(short_name)
            short_names[name] = attr or base

        export_names = {}
        for annotation, new_name in sorted(annotations):
            name = annotation.name
            if not new_name:
                # Only use short name if it's unique
                if "." in name and short_names_count[shorten(name)] == 1:
                    new_name = short_names[name]
                else:
                    base, attr = corpus.split_annotation(name)
                    new_name = attr or base

            if keep_struct_names:
                # Keep annotation base name (the part before ":") if this is not a token attribute
                if ":" in name and not name.startswith(token_name):
                    base_name = annotation.annotation_name()
                    new_name = corpus.join_annotation(export_names.get(base_name, base_name), new_name)
            export_names[name] = new_name
    else:
        if keep_struct_names:
            export_names = {}
            for annotation, new_name in sorted(annotations):
                name = annotation.name
                if not new_name:
                    base, attr = corpus.split_annotation(name)
                    new_name = attr or base
                if ":" in name and not name.startswith(token_name):
                    base_name = annotation.annotation_name()
                    new_name = corpus.join_annotation(export_names.get(base_name, base_name), new_name)
                export_names[name] = new_name
        else:
            export_names = {annotation.name: new_name for annotation, new_name in annotations if new_name}
    return export_names


################################################################################
# Scrambling
################################################################################


def scramble_spans(span_positions, chunk_name: str, chunk_order):
    """Reorder chunks and open/close tags in correct order."""
    new_s_order = _reorder_spans(span_positions, chunk_name, chunk_order)
    _fix_parents(new_s_order, chunk_name)

    # Reformat span positions
    new_span_positions = [v for k, v in sorted(new_s_order.items())]  # Sort dict into list
    new_span_positions = [t for s in new_span_positions for t in s]  # Unpack chunks
    new_span_positions = [(0, instruction, span) for instruction, span in new_span_positions]  # Add fake position (0)

    return new_span_positions


def _reorder_spans(span_positions, chunk_name: str, chunk_order):
    """Scramble chunks according to the chunk_order."""
    new_s_order = defaultdict(list)
    parent_stack = []
    temp_stack = []
    current_s_index = None
    last_s_index = None

    for _pos, instruction, span in span_positions:
        if instruction == "open":
            if span.name == chunk_name:
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
            else:
                if current_s_index is not None:
                    # Encountered child to chunk
                    new_s_order[current_s_index].append((instruction, span))
                else:
                    # Encountered parent to chunk
                    temp_stack.append((instruction, span))

        elif instruction == "close":
            if current_s_index is not None:
                # Encountered child to chunk
                new_s_order[current_s_index].append((instruction, span))
                if span.name == chunk_name:
                    last_s_index = current_s_index
                    current_s_index = None
            else:
                # Encountered parent to chunk
                temp_stack.append((instruction, span))

    return new_s_order


def _fix_parents(new_s_order, chunk_name):
    """Go through new_span_positions, remove duplicate opened parents and close parents."""
    open_parents = []
    for s_index, chunk in sorted(new_s_order.items()):
        is_parent = True
        for instruction, span in chunk:
            if instruction == "open":
                if span.name == chunk_name:
                    is_parent = False
                elif is_parent:
                    open_parents.append((instruction, span))
            else:
                if span.name == chunk_name:
                    is_parent = True
                elif is_parent:
                    if open_parents[-1][1] == span:
                        open_parents.pop()
        # Check next chunk: close parents in current chunk that are not part of next chunk and
        # remove already opened parents from next chunk
        next_chunk = new_s_order.get(s_index + 1, [])
        for p in reversed(open_parents):
            if p in next_chunk:
                next_chunk.remove(p)
            else:
                chunk.append(("close", p[1]))
                open_parents.remove(p)
