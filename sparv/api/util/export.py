"""Util functions for corpus export."""

import re
import xml.etree.ElementTree as etree
from collections import OrderedDict, defaultdict
from copy import deepcopy
from itertools import combinations
from typing import Any, List, Optional, Tuple, Union

from sparv.api import (Annotation, AnnotationAllSourceFiles, ExportAnnotations, ExportAnnotationsAllSourceFiles,
                       Headers, Namespaces, SourceStructure, SparvErrorMessage, get_logger, util)
from sparv.core import io

from .constants import SPARV_DEFAULT_NAMESPACE, XML_NAMESPACE_SEP

logger = get_logger(__name__)


def gather_annotations(annotations: List[Annotation],
                       export_names,
                       header_annotations=None,
                       source_file: Optional[str] = None,
                       flatten: bool = True,
                       split_overlaps: bool = False):
    """Calculate the span hierarchy and the annotation_dict containing all annotation elements and attributes.

    Args:
        annotations: List of annotations to include
        export_names: Dictionary that maps from annotation names to export names
        header_annotations: List of header annotations
        source_file: The source filename
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
            def get_sort_key(span, sub_positions=False, empty_span=False):
                """Return a sort key for span which makes span comparison possible."""
                hierarchy_index = elem_hierarchy.index(span.name) if span.name in elem_hierarchy else -1
                if empty_span:
                    if sub_positions:
                        return (span.start, span.start_sub), hierarchy_index, (span.end, span.end_sub)
                    else:
                        return span.start, hierarchy_index, span.end
                else:
                    if sub_positions:
                        return (span.start, span.start_sub), (-span.end, -span.end_sub), hierarchy_index
                    else:
                        return span.start, -span.end, hierarchy_index

            # Sort empty spans according to hierarchy or put them first
            if (self.start, self.start_sub) == (self.end, self.end_sub) or (
                other_span.start, other_span.start_sub) == (other_span.end, other_span.end_sub):
                sort_key1 = get_sort_key(self, empty_span=True)
                sort_key2 = get_sort_key(other_span, empty_span=True)
            # Both spans have sub positions
            elif self.start_sub and other_span.start_sub:
                sort_key1 = get_sort_key(self, sub_positions=True)
                sort_key2 = get_sort_key(other_span, sub_positions=True)
            # At least one of the spans does not have sub positions
            else:
                sort_key1 = get_sort_key(self)
                sort_key2 = get_sort_key(other_span)

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
                        Annotation(f"{base_name}:{util.constants.HEADER_CONTENTS}", source_file=source_file).read(
                        allow_newlines=True))
                except FileNotFoundError:
                    raise SparvErrorMessage(f"Could not find data for XML header '{base_name}'. "
                                            "Was this element listed in 'xml_import.header_elements'?")

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
                    if instruction == "close":
                        if s.name in elem_hierarchy and elem_hierarchy.index(s.name) < elem_hierarchy.index(span.name):
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


def _handle_overlaps(spans_dict):
    """Split overlapping spans and give them unique IDs to preserve their original connection."""
    span_stack = []
    overlap_count = 0
    for position in sorted(spans_dict):
        subposition_shift = 0
        for subposition, (event, span) in enumerate(spans_dict[position].copy()):
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


def calculate_element_hierarchy(source_file, spans_list):
    """Calculate the hierarchy for spans with identical start and end positions.

    If two spans A and B have identical start and end positions, go through all occurrences of A and B
    and check which element is most often parent to the other. That one will be first.
    """
    # Find elements with identical spans
    span_duplicates = defaultdict(set)
    start_positions = defaultdict(set)
    end_positions = defaultdict(set)
    empty_span_starts = set()
    for span in spans_list:
        span_duplicates[(span.start, span.end)].add(span.name)
        start_positions[span.start].add(span.name)
        end_positions[span.end].add(span.name)
        if span.start == span.end:
            empty_span_starts.add(span.start)
    span_duplicates = [v for v in span_duplicates.values() if len(v) > 1]
    # Add empty spans and spans with identical start positions
    for span_start in empty_span_starts:
        span_duplicates.append(start_positions[span_start])
        span_duplicates.append(end_positions[span_start])

    # Flatten structure
    unclear_spans = set([elem for elem_set in span_duplicates for elem in elem_set])

    # Get pairs of relations that need to be ordered
    relation_pairs = list(combinations(unclear_spans, r=2))
    # Order each pair into [parent, children]
    ordered_pairs = set()
    for a, b in relation_pairs:
        a_annot = Annotation(a, source_file=source_file)
        b_annot = Annotation(b, source_file=source_file)
        a_parent = len([i for i in (b_annot.get_parents(a_annot)) if i is not None])
        b_parent = len([i for i in (a_annot.get_parents(b_annot)) if i is not None])
        if a_parent > b_parent:
            ordered_pairs.add((a, b))
        elif a_parent < b_parent:
            ordered_pairs.add((b, a))

    hierarchy = []
    error_msg = ("Something went wrong while sorting annotation elements. Could there be circular relations? "
                 "The following elements could not be sorted: ")
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
        assert len(unclear_spans) < size, error_msg + " ".join(unclear_spans)
    return hierarchy


def get_available_source_annotations(source_file: Optional[str] = None,
                                     source_files: Optional[List[str]] = None) -> List[str]:
    """Get a list of available annotations generated from the source, either for a single source file or multiple."""
    assert source_file or source_files, "Either 'source_file' or 'source_files' must be provided"
    available_source_annotations = set()
    if source_files:
        for d in source_files:
            available_source_annotations.update(SourceStructure(d).read().split())
    else:
        available_source_annotations.update(SourceStructure(source_file).read().split())

    return sorted(available_source_annotations)


def get_source_annotations(source_annotation_names: Optional[List[str]], source_file: Optional[str] = None,
                           source_files: Optional[List[str]] = None):
    """Given a list of source annotation names (and possible export names), return a list of annotation objects.

    If no names are provided all available source annotations will be returnd.
    """
    # If source_annotation_names is en empty list, do not add any source annotations
    if not source_annotation_names and source_annotation_names is not None:
        return []

    # Get list of available source annotation names
    available_source_annotations = get_available_source_annotations(source_file, source_files)

    # Parse source_annotation_names
    annotation_names = util.misc.parse_annotation_list(source_annotation_names, available_source_annotations)

    # Make sure source_annotations doesn't include annotations not in source
    source_annotations = [(Annotation(a[0], source_file) if source_file else AnnotationAllSourceFiles(a[0]), a[1]) for a in
                          annotation_names if a[0] in available_source_annotations]

    return source_annotations


def get_annotation_names(annotations: Union[ExportAnnotations, ExportAnnotationsAllSourceFiles],
                         source_annotations=None,
                         source_file: Optional[str] = None, source_files: Optional[List[str]] = None,
                         token_name: Optional[str] = None,
                         remove_namespaces=False, keep_struct_names=False,
                         sparv_namespace: Optional[str] = None,
                         source_namespace: Optional[str] = None,
                         xml_mode: Optional[bool] = False):
    """Get a list of annotations, token attributes and a dictionary for renamed annotations.

    Args:
        annotations: List of elements:attributes (annotations) to include.
        source_annotations: List of elements:attributes from the source file to include. If not specified,
            everything will be included.
        source_file: Name of the source file.
        source_files: List of names of source files (alternative to `source_file`).
        token_name: Name of the token annotation.
        remove_namespaces: Remove all namespaces in export_names unless names are ambiguous.
        keep_struct_names: For structural attributes (anything other than token), include the annotation base name
            (everything before ":") in export_names (used in cwb encode).
        sparv_namespace: The namespace to be added to all Sparv annotations.
        source_namespace: The namespace to be added to all annotations present in the source.

    Returns:
        A list of annotations, a list of token attribute names, a dictionary with translation from annotation names to
        export names.
    """
    # Get source annotations
    source_annotations = get_source_annotations(source_annotations, source_file, source_files)

    # Combine all annotations
    all_annotations = _remove_duplicates(annotations + source_annotations)

    if token_name:
        # Get the names of all token attributes
        token_attributes = [a[0].attribute_name for a in all_annotations
                            if a[0].annotation_name == token_name and a[0].name != token_name]
    else:
        token_attributes = []

    # Get XML namespaces
    xml_namespaces = Namespaces(source_file).read()

    export_names = _create_export_names(all_annotations, token_name, remove_namespaces, keep_struct_names,
                                        source_annotations, sparv_namespace, source_namespace, xml_namespaces,
                                        xml_mode=xml_mode)

    return [i[0] for i in all_annotations], token_attributes, export_names


def get_header_names(header_annotation_names: Optional[List[str]],
                     source_file: Optional[str] = None,
                     source_files: Optional[List[str]] = None):
    """Get a list of header annotations and a dictionary for renamed annotations."""
    # Get source_header_names from headers file if it exists
    source_header_names = []
    if source_files:
        for f in source_files:
            h = Headers(f)
            if h.exists():
                source_header_names.extend(h.read())
        source_header_names = list(set(source_header_names))
    elif Headers(source_file).exists():
        source_header_names = Headers(source_file).read()

    # Parse header_annotation_names and convert to annotations
    annotation_names = util.misc.parse_annotation_list(header_annotation_names, source_header_names)
    header_annotations = [(Annotation(a[0], source_file) if source_file else AnnotationAllSourceFiles(a[0]), a[1]) for a in
                          annotation_names]

    # Get XML namespaces
    xml_namespaces = Namespaces(source_file).read()

    export_names = _create_export_names(header_annotations, None, False, keep_struct_names=False,
                                        xml_namespaces=xml_namespaces, xml_mode=True)

    return [a[0] for a in header_annotations], export_names


def _remove_duplicates(annotation_tuples):
    """Remove duplicates from annotation_tuples without changing the order."""
    new_annotations = OrderedDict()
    for a, new_name in annotation_tuples:
        if a not in new_annotations or new_name is not None:
            new_annotations[a] = new_name
    return list(new_annotations.items())


def _create_export_names(annotations: List[Tuple[Union[Annotation, AnnotationAllSourceFiles], Any]],
                         token_name: Optional[str],
                         remove_namespaces: bool,
                         keep_struct_names: bool,
                         source_annotations: list = [],
                         sparv_namespace: Optional[str] = None,
                         source_namespace: Optional[str] = None,
                         xml_namespaces: Optional[dict] = None,
                         xml_mode: Optional[bool] = False):
    """Create dictionary for renamed annotations."""
    if remove_namespaces:
        def shorten(annotation):
            """Shorten annotation name or attribute name.

            For example:
                segment.token -> token
                segment.token:saldo.baseform -> segment.token:baseform
            """
            def remove_before_dot(name):
                # Always remove "custom."
                if name.startswith("custom."):
                    name = name[7:]
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
            # Don't remove namespaces from elements and attributes contained in the source files
            if (annotation, new_name) in source_annotations:
                short_name = name
            else:
                short_name = shorten(annotation)
            if new_name:
                if ":" in name:
                    # Combine new attribute name with base annotation name
                    short_name = io.join_annotation(annotation.annotation_name, new_name)
                else:
                    short_name = new_name
            short_names_count[short_name] += 1
            base, attr = Annotation(short_name).split()
            short_names[name] = attr or base

        export_names = {}
        for annotation, new_name in sorted(annotations):  # Sorted in order to handle annotations before attributes
            name = annotation.name
            if not new_name:
                # Only use short name if it's unique
                if "." in name and short_names_count[shorten(annotation)] == 1:
                    new_name = short_names[name]
                else:
                    new_name = annotation.attribute_name or annotation.annotation_name

            if keep_struct_names:
                # Keep annotation base name (the part before ":") if this is not a token attribute
                if ":" in name and not name.startswith(token_name):
                    base_name = annotation.annotation_name
                    new_name = io.join_annotation(export_names.get(base_name, base_name), new_name)
            export_names[name] = new_name
    else:
        if keep_struct_names:
            export_names = {}
            for annotation, new_name in sorted(annotations):  # Sorted in order to handle annotations before attributes
                name = annotation.name
                if not new_name:
                    new_name = annotation.attribute_name or annotation.annotation_name
                if ":" in name and not name.startswith(token_name):
                    base_name = annotation.annotation_name
                    new_name = io.join_annotation(export_names.get(base_name, base_name), new_name)
                export_names[name] = new_name
        else:
            export_names = {annotation.name: (new_name if new_name else annotation.attribute_name or annotation.name)
                            for annotation, new_name in annotations}

    export_names = _add_global_namespaces(export_names, annotations, source_annotations, sparv_namespace,
                                          source_namespace)
    export_names = _check_name_collision(export_names, source_annotations)

    # Take care of XML namespaces
    export_names = {k: _get_xml_tagname(v, xml_namespaces, xml_mode) for k, v in export_names.items()}

    return export_names


def _get_xml_tagname(tag, xml_namespaces, xml_mode=False):
    """Take care of namespaces by looking up URIs for prefixes (if xml_mode=True) or by converting to dot notation."""
    sep = re.escape(XML_NAMESPACE_SEP)
    m = re.match(fr"(.*){sep}(.+)", tag)
    if m:
        if xml_mode:
            # Replace prefix+tag with {uri}tag
            uri = xml_namespaces.get(m.group(1), "")
            if not uri:
                raise SparvErrorMessage(f"You are trying to export the annotation '{tag}' but no URI was found for the "
                                        f"namespace prefix '{m.group(1)}'!")
            return re.sub(fr"(.*){sep}(.+)", fr"{{{uri}}}\2", tag)
        elif m.group(1):
            # Replace "prefix+tag" with "prefix.tag", skip this for default namespaces
            return re.sub(fr"(.*){sep}(.+)", fr"\1.\2", tag)
    return tag


def _add_global_namespaces(export_names: dict,
                           annotations: List[Tuple[Union[Annotation, AnnotationAllSourceFiles], Any]],
                           source_annotations: list,
                           sparv_namespace: Optional[str] = None,
                           source_namespace: Optional[str] = None):
    """Add sparv_namespace and source_namespace to export names."""
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


def _check_name_collision(export_names, source_annotations):
    """Detect collisions in attribute names and resolve them or send warnings."""
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
        for _elem, annots in attr_collisions.items():
            # If there are two colliding attributes and one is an automatic one, prefix it with SPARV_DEFAULT_NAMESPACE
            if len(annots) == 2 and len([a for a in annots if a.name not in source_names]) == 1:
                sparv_annot = annots[0] if annots[0].name not in source_names else annots[1]
                source_annot = annots[0] if annots[0].name in source_names else annots[1]
                new_name = SPARV_DEFAULT_NAMESPACE + "." + export_names[sparv_annot.name]
                export_names[sparv_annot.name] = new_name
                logger.info("Changing name of automatic annotation '{}' to '{}' due to collision with '{}'.".format(
                            sparv_annot.name, new_name, source_annot.name))
            # Warn the user if we cannot resolve collisions automatically
            else:
                annots_string = "\n".join([f"{a.name} ({'source' if a.name in source_names else 'sparv'} annotation)"
                                           for a in annots])
                logger.warning("The following annotations are exported with the same name ({}) and might overwrite "
                               "each other: \n\n{}\n\nIf you want to keep all of these annotations you can change "
                               "their export names.".format(attr, annots_string))
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
                # If chunk, check index to make sure it's the right chunk and not a nested one
                if span.name == chunk_name and int(chunk_order[span.index]) == current_s_index:
                    last_s_index = current_s_index
                    current_s_index = None
            else:
                # Encountered parent to chunk
                temp_stack.append((instruction, span))

    return new_s_order


def _fix_parents(new_s_order, chunk_name):
    """Go through new_span_positions, remove duplicate opened parents and close parents."""
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
            else:  # "close"
                # If chunk, check index to make sure it's the right chunk and not a nested one
                if span.name == chunk_name and span.index == current_chunk_index:
                    is_parent = True
                    current_chunk_index = None
                elif is_parent:
                    if open_parents[-1][1] == span:
                        open_parents.pop()
        # Check next chunk: close parents in current chunk that are not part of next chunk and
        # remove already opened parents from next chunk
        if i < len(new_s_order_indices) - 1:
            next_chunk = new_s_order[new_s_order_indices[i + 1]]
        else:
            next_chunk = []
        for p in reversed(open_parents):
            if p in next_chunk:
                next_chunk.remove(p)
            else:
                chunk.append(("close", p[1]))
                open_parents.remove(p)
