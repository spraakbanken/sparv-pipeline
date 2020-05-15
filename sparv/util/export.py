"""Util functions for corpus export."""

import logging
import xml.etree.ElementTree as etree
from collections import defaultdict
from itertools import combinations

from sparv.util import corpus, misc, parent

log = logging.getLogger(__name__)


def gather_annotations(doc, annotations, export_names, flatten=True):
    """Calculate the span hierarchy and the annotation_dict containing all annotation elements and attributes.

    - doc: the name of the document
    - annotations: list of annotations to include
    - annotation_names: dictionary that maps from annotation names to export names
    """
    class Span(object):
        """Object to store span information."""

        def __init__(self, name, index, start, end, export_names):
            """Set attributes."""
            self.name = name
            self.index = index
            self.start = start[0]
            self.end = end[0]
            self.start_sub = start[1] if len(start) > 1 else False
            self.end_sub = end[1] if len(end) > 1 else False
            self.export = export_names.get(self.name, self.name)
            self.node = None

        def set_node(self, parent_node=None):
            """Create an xml node under parent_node."""
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
                    return ((span.start, span.start_sub), (- span.end, - span.end_sub), hierarchy_index)
                else:
                    return (span.start, - span.end, hierarchy_index)

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

    # Collect annotation information and list of all annotation spans
    annotation_dict = defaultdict(dict)
    spans_list = []
    for annotation_pointer in annotations:
        span_name, attr = corpus.split_annotation(annotation_pointer)
        if span_name not in annotation_dict:
            annotation_dict[span_name] = {}  # span_name needs to be in the dictionary
            try:
                for i, s in enumerate(corpus.read_annotation_spans(doc, span_name, decimals=True)):
                    spans_list.append(Span(span_name, i, s[0], s[1], export_names))
            except FileNotFoundError:
                log.info("Element %s not present in %s. Skipping." % (span_name, doc))
        # TODO: assemble all attrs first and use read_annotation_attributes
        if attr and not annotation_dict[span_name].get(attr):
            try:
                a = list(corpus.read_annotation(doc, annotation_pointer))
                annotation_dict[span_name][attr] = a
            except FileNotFoundError:
                log.info("Attribute %s not present in %s. Skipping." % (annotation_pointer, doc))

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

    # Return the span_dict without converting to list first
    if not flatten:
        return spans_dict, annotation_dict

    # Flatten structure
    span_positions = [(pos, span[0], span[1]) for pos, spans in sorted(spans_dict.items()) for span in spans]
    return span_positions, annotation_dict


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


def get_annotation_names(doc, token_name, annotations, original_annotations=None, remove_namespaces=False,
                         keep_struct_refs=False):
    """Get a list of annotations, token annotations and a dictionary for renamed annotations.

    remove_namespaces: remove all name spaces in export_names unless names are ambiguous.
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
    all_annotations = set(annotations)
    for a, _name in annotations:
        plain_annot = corpus.split_annotation(a)[0]
        if plain_annot not in plain_annots:
            all_annotations.add((plain_annot, None))
    annotations = sorted(list(all_annotations))

    # Get the names of all token annotations (but not token itself)
    token_annotations = [corpus.split_annotation(i[0])[1] for i in annotations
                         if corpus.split_annotation(i[0])[0] == token_name and i[0] != token_name]

    export_names = _create_export_names(annotations, token_name, remove_namespaces, keep_struct_refs)

    return [i[0] for i in annotations], token_annotations, export_names


def _create_export_names(annotations, token_name, remove_namespaces, keep_struct_refs):
    """Create dictionary for renamed annotations."""
    if remove_namespaces:
        short_names = [name.split(".")[-1] for name, new_name in annotations if not new_name]
        export_names = {}
        for name, new_name in annotations:
            if not new_name:
                # Skip if there is no name space
                if "." not in name:
                    continue
                # Don't use short_name unless it is unique
                short_name = name.split(".")[-1]
                if short_names.count(short_name) == 1:
                    new_name = short_name
                else:
                    continue
            if keep_struct_refs:
                # Keep reference (the part before ":") if this is not a token attribute
                if ":" in name and new_name != name and not name.startswith(token_name):
                    ref = name[0:name.find(":")]
                    new_name = export_names.get(ref, ref) + ":" + new_name
            export_names[name] = new_name
    else:
        export_names = dict((a, b) for a, b in annotations if b)

    return export_names
