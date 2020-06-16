"""Util functions for corpus export."""

import logging
import xml.etree.ElementTree as etree
from collections import defaultdict
from copy import deepcopy
from itertools import combinations
from typing import List, Optional, Union

from sparv.util import corpus, misc, parent

log = logging.getLogger(__name__)


def gather_annotations(doc: str, annotations, export_names, flatten: bool = True, split_overlaps: bool = False,
                       header_annotations=None):
    """Calculate the span hierarchy and the annotation_dict containing all annotation elements and attributes.

    - doc: the name of the document
    - annotations: list of annotations to include
    - annotation_names: dictionary that maps from annotation names to export names
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
        for annotation_pointer in annots:
            span_name, attr = corpus.split_annotation(annotation_pointer)
            if span_name not in annotation_dict:
                annotation_dict[span_name] = {}  # span_name needs to be in the dictionary
                try:
                    for i, s in enumerate(corpus.read_annotation_spans(doc, span_name, decimals=True)):
                        spans_list.append(Span(span_name, i, s[0], s[1], export_names, is_header))
                except FileNotFoundError:
                    log.info("Element %s not present in %s. Skipping." % (span_name, doc))
            # TODO: assemble all attrs first and use read_annotation_attributes
            if attr and not annotation_dict[span_name].get(attr):
                try:
                    annotation_dict[span_name][attr] = list(corpus.read_annotation(doc, annotation_pointer))
                except FileNotFoundError:
                    log.info("Attribute %s not present in %s. Skipping." % (annotation_pointer, doc))
            elif is_header:
                annotation_dict[span_name][corpus.HEADER_CONTENT] = list(
                    corpus.read_annotation(doc, f"{span_name}:{corpus.HEADER_CONTENT}", allow_newlines=True))

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


def get_annotation_names(doc: Union[str, List[str]], token_name: Optional[str], annotations: List[str], original_annotations=None,
                         remove_namespaces=False, keep_struct_refs=False):
    """Get a list of annotations, token annotations and a dictionary for renamed annotations.

    remove_namespaces: remove all namespaces in export_names unless names are ambiguous.
    keep_struct_refs: for structural attributes, include everything before ":" in export_names (used in cwb encode)
    """
    # Combine annotations and original_annotations
    annotations = misc.split_tuples_list(annotations)
    original_annotations = misc.split_tuples_list(original_annotations)
    if not original_annotations:
        # Get original_annotations from STRUCTURE_FILE
        if isinstance(doc, list):
            original_annotations = []
            for d in doc:
                original_annotations.extend(misc.split_tuples_list(corpus.read_data(d, corpus.STRUCTURE_FILE)))
        else:
            original_annotations = misc.split_tuples_list(corpus.read_data(doc, corpus.STRUCTURE_FILE))
    annotations.extend(original_annotations)

    # Add plain annotations (non-attribute annotations) to annotations if user has not done that
    plain_annots = [a for a, _ in annotations if ":" not in a]
    for a, _name in annotations:
        plain_annot = corpus.split_annotation(a)[0]
        if (plain_annot not in plain_annots) and ((plain_annot, None) not in annotations):
            annotations.append((plain_annot, None))

    if token_name:
        # Get the names of all token annotations (but not token itself)
        token_annotations = [corpus.split_annotation(i[0])[1] for i in annotations
                             if corpus.split_annotation(i[0])[0] == token_name and i[0] != token_name]
    else:
        token_annotations = []

    export_names = _create_export_names(annotations, token_name, remove_namespaces, keep_struct_refs, original_annotations)

    return [i[0] for i in annotations], token_annotations, export_names


def get_header_names(doc: Union[str, List[str]], header_annotations):
    """Get a list of header annotations and a dictionary for renamed annotations."""
    header_annotations = misc.split_tuples_list(header_annotations)
    if not header_annotations:
        # Get header_annotations from HEADERS_FILE if it exists
        if isinstance(doc, list):
            header_annotations = []
            for d in doc:
                if corpus.data_exists(d, corpus.HEADERS_FILE):
                    header_annotations.extend(misc.split_tuples_list(corpus.read_data(d, corpus.HEADERS_FILE)))
        elif corpus.data_exists(doc, corpus.HEADERS_FILE):
            header_annotations = misc.split_tuples_list(corpus.read_data(doc, corpus.HEADERS_FILE))

    export_names = _create_export_names(header_annotations, None, False, keep_struct_refs=False)

    return [a[0] for a in header_annotations], export_names


def _create_export_names(annotations, token_name, remove_namespaces: bool, keep_struct_refs: bool,
                         original_annotations: list = []):
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
        for name, new_name in annotations:
            # Don't remove namespaces from elements and attributes contained in the original documents
            if (name, new_name) in original_annotations:
                short_name = name
            else:
                short_name = shorten(name)
            if new_name:
                if ":" in name:
                    short_name = corpus.join_annotation(corpus.split_annotation(name)[0], new_name)
                else:
                    short_name = new_name
            short_names_count[short_name] += 1
            short_names[name] = short_name.split(":")[-1]

        export_names = {}
        for name, new_name in sorted(annotations):
            if not new_name:
                # Only use short name if it's unique
                if "." in name and short_names_count[shorten(name)] == 1:
                    new_name = short_names[name]
                else:
                    new_name = name.split(":")[-1]

            if keep_struct_refs:
                # Keep reference (the part before ":") if this is not a token attribute
                if ":" in name and not name.startswith(token_name):
                    ref, _ = corpus.split_annotation(name)
                    new_name = corpus.join_annotation(export_names.get(ref, ref), new_name)
            export_names[name] = new_name
    else:
        if keep_struct_refs:
            export_names = {}
            for name, new_name in sorted(annotations):
                if not new_name:
                    new_name = name.split(":")[-1]
                if ":" in name and not name.startswith(token_name):
                    ref, _ = corpus.split_annotation(name)
                    new_name = corpus.join_annotation(export_names.get(ref, ref), new_name)
                export_names[name] = new_name
        else:
            export_names = {name: new_name for name, new_name in annotations if new_name}
    return export_names


################################################################################
# Scrambling
################################################################################


def scramble_spans(span_positions, chunk, chunk_order):
    """Reorder chunks and open/close tags in correct order."""
    new_s_order = _reorder_spans(span_positions, chunk, chunk_order)
    _fix_parents(new_s_order, chunk)

    # Reformat span positions
    new_span_positions = [v for k, v in sorted(new_s_order.items())]  # Sort dict into list
    new_span_positions = [t for s in new_span_positions for t in s]  # Unpack chunks
    new_span_positions = [(0, instruction, span) for instruction, span in new_span_positions]  # Add fake position (0)

    return new_span_positions


def _reorder_spans(span_positions, chunk_name, chunk_order):
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
