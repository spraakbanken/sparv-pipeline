"""Export annotated corpus data to scrambled xml."""

import logging
import os
from collections import defaultdict
from typing import Optional

import sparv.modules.xml_export.xml_utils as xml_utils
import sparv.util as util
from sparv import (AllDocuments, Annotation, Config, Corpus, Document, Export, ExportAnnotations, ExportInput, Output,
                   exporter, installer)

log = logging.getLogger(__name__)


@exporter("Scrambled XML export")
def scrambled(doc: str = Document,
              docid: str = Annotation("<docid>", data=True),
              out: str = Export("xml_scrambled/[xml_export.filename]"),
              chunk: str = Annotation("[export.scramble_on]"),
              chunk_order: str = Annotation("[export.scramble_on]:misc.number_random"),
              token: str = Annotation("<token>"),
              word: str = Annotation("<token:word>"),
              annotations: list = ExportAnnotations(export_type="xml_export"),
              original_annotations: Optional[list] = Config("xml_export.original_annotations"),
              remove_namespaces: bool = Config("export.remove_export_namespaces", False)):
    """Export annotations to scrambled XML."""
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Read words and document ID
    word_annotation = list(util.read_annotation(doc, word))
    chunk_order = list(util.read_annotation(doc, chunk_order))
    docid = util.read_data(doc, docid)

    # Get annotation spans, annotations list etc.
    annotations, _, export_names = util.get_annotation_names(doc, token, annotations, original_annotations,
                                                             remove_namespaces)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names)

    # Reorder chunks and open/close tags in correct order
    new_s_order = _reorder_spans(span_positions, chunk, chunk_order)
    _fix_dangling_elems(new_s_order, chunk)
    _fix_parents(new_s_order, chunk)

    # Reformat span positions to fit the specs of make_pretty_xml
    new_span_positions = [v for k, v in sorted(new_s_order.items())]  # Sort dict into list
    new_span_positions = [t for s in new_span_positions for t in s]  # Unpack chunks
    new_span_positions = [(0, instruction, span) for instruction, span in new_span_positions]  # Add fake position (0)

    # Construct XML string
    xmlstr = xml_utils.make_pretty_xml(new_span_positions, annotation_dict, export_names, token, word_annotation, docid)

    # Write XML to file
    with open(out, mode="w") as outfile:
        outfile.write(xmlstr)
    log.info("Exported: %s", out)


@exporter("Combined scrambled XML export")
def combined_scrambled(corpus: str = Corpus,
                       out: str = Export("[id]_scrambled.xml"),
                       docs: list = AllDocuments,
                       xml_input: str = ExportInput("xml_scrambled/[xml_export.filename]", all_docs=True)):
    """Combine XML export files into a single XML file."""
    xml_utils.combine(corpus, out, docs, xml_input)


@exporter("Compressed combined scrambled XML export")
def compressed_scrambled(out: str = Export("[id]_scrambled.xml.bz2"),
                         xmlfile: str = ExportInput("[id]_scrambled.xml")):
    """Compress combined XML export."""
    xml_utils.compress(xmlfile, out)


@installer("Copy compressed scrambled XML to remote host")
def install_scrambled(corpus: Corpus,
                      xmlfile: str = ExportInput("[id]_scrambled.xml"),
                      out: str = Output("xml_export.time_install_export", data=True, common=True),
                      export_path: str = Config("xml_export.export_path", ""),
                      host: str = Config("xml_export.export_host", "")):
    """Copy compressed combined scrambled XML to remote host."""
    xml_utils.install_compressed_xml(corpus, xmlfile, out, export_path, host)


########################################################################################################
# HELPERS
########################################################################################################

def _reorder_spans(span_positions, chunk_name, chunk_order):
    """Scramble chunks according to the chunk_order."""
    new_s_order = defaultdict(list)
    parent_stack = []
    current_s_index = -1

    for _pos, instruction, span in span_positions:
        if instruction == "open":
            if span.name == chunk_name:
                current_s_index = int(chunk_order[span.index])
                new_s_order[current_s_index].extend(parent_stack)
                new_s_order[current_s_index].append((instruction, span))
            else:
                if current_s_index == -1:
                    # Encountered parent to chunk
                    parent_stack.append((instruction, span))
                else:
                    # Encountered child to chunk
                    new_s_order[current_s_index].append((instruction, span))

        if instruction == "close":
            if parent_stack and parent_stack[-1][1] == span:
                if current_s_index != -1:
                    new_s_order[current_s_index].append((instruction, span))
                parent_stack.pop()
            else:
                new_s_order[current_s_index].append((instruction, span))
                if span.name == chunk_name:
                    current_s_index = -1

    return new_s_order


def _fix_dangling_elems(new_s_order, chunk_name):
    """Fix child spans to chunk that are not being opened or closed."""
    for chunk in new_s_order.values():
        is_parent = True
        for instruction, span in chunk:
            if instruction == "open":
                if span.name == chunk_name:
                    is_parent = False
                    chunk_span = span
                elif not is_parent:
                    if ("close", span) not in chunk:
                        # This child span has no closing tag. Close it!
                        close_s_indx = chunk.index(("close", chunk_span))
                        chunk.insert(close_s_indx, ("close", span))
            elif instruction == "close" and span.name != chunk_name:
                if ("open", span) not in chunk:
                    # This child span has no opening tag. Open it!
                    open_s_indx = chunk.index(("open", chunk_span))
                    chunk.insert(open_s_indx + 1, ("open", span))


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
        # Check next chunk: close parents that are not opened again and remove already opened parents
        next_chunk = new_s_order.get(s_index + 1, [])
        for parent in reversed(open_parents):
            if parent in next_chunk:
                next_chunk.remove(parent)
            else:
                chunk.append(("close", parent[1]))
                open_parents.remove(parent)
