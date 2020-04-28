"""Annotators for numbering things."""

import random
import re
from binascii import hexlify
from collections import defaultdict

import sparv.util as util
from sparv import Annotation, Document, Output, annotator

START_DEFAULT = 1


@annotator("Number {annotation} by position")
def number_by_position(doc: str = Document,
                       out: str = Output("{annotation}:misc.number_position"),
                       chunk: str = Annotation("{annotation}"),
                       prefix: str = "",
                       zfill: bool = False,
                       start: int = START_DEFAULT):
    """Number chunks by their position."""
    spans = list(util.read_annotation_spans(doc, chunk))

    def _order(index, _value):
        return spans[index]

    _read_chunks_and_write_new_ordering(doc, out, chunk, _order, prefix, zfill, start)


@annotator("Number {annotation} randomly")
def number_random(doc: str = Document,
                  out: str = Output("{annotation}:misc.number_random"),
                  chunk: str = Annotation("{annotation}"),
                  prefix: str = "",
                  zfill: bool = False,
                  start: int = START_DEFAULT):
    """Number chunks randomly.

    Uses index as random seed.
    """
    def _order(index, _value):
        random.seed(int(hexlify(str(index).encode()), 16))
        return random.random()

    _read_chunks_and_write_new_ordering(doc, out, chunk, _order, prefix, zfill, start)


def renumber_by_attribute(doc, out, chunk, prefix="", zfill=False, start=START_DEFAULT):
    """Renumber chunks, with the order determined by an attribute."""
    def _order(_index, value):
        return _natural_sorting(value)

    _read_chunks_and_write_new_ordering(doc, out, chunk, _order, prefix, zfill, start)


def renumber_by_shuffle(doc, out, chunk, prefix="", zfill=False, start=START_DEFAULT):
    """Renumber already numbered chunks, in new random order.

    Retains the connection between parallelly numbered chunks by using the values as random seed.
    """
    def _order(_index, value):
        random.seed(int(hexlify(value.encode()), 16))
        return random.random(), _natural_sorting(value)

    _read_chunks_and_write_new_ordering(doc, out, chunk, _order, prefix, zfill, start)


def number_by_parent(doc, out, chunk, parent_order, prefix="", zfill=False, start=START_DEFAULT):
    """Number chunks by (parent order, chunk order)."""
    parent_children, _orphans = util.get_children(doc, parent_order, chunk)

    child_order = {child_index: (parent_nr, child_index)
                   for parent_index, parent_nr in enumerate(util.read_annotation(doc, parent_order))
                   for child_index in parent_children[parent_index]}

    def _order(index, _value):
        return child_order.get(index)

    _read_chunks_and_write_new_ordering(doc, out, chunk, _order, prefix, zfill, start)


@annotator("Number {annotation} by relative position within {parent}")
def number_relative(doc: str = Document,
                    out: str = Output("{annotation}:misc.number_rel_{parent}"),
                    parent: str = Annotation("{parent}"),
                    child: str = Annotation("{annotation}"),
                    prefix: str = "",
                    zfill: bool = False,
                    start: int = START_DEFAULT):
    """Number chunks by their relative position within a parent."""
    parent_children, _orphans = util.get_children(doc, parent, child)

    util.write_annotation(doc, out, ("{prefix}{nr:0{length}d}".format(prefix=prefix,
                                                                      length=len(str(len(parent) - 1 + start))
                                                                      if zfill else 0,
                                                                      nr=cnr)
                                     for parent in parent_children
                                     for cnr, _index in enumerate(parent, start)))


def _read_chunks_and_write_new_ordering(doc, out, chunk, order, prefix="", zfill=False, start=START_DEFAULT):
    """Common function called by other numbering functions."""
    new_order = defaultdict(list)

    in_annotation = list(util.read_annotation(doc, chunk))

    for i, val in enumerate(in_annotation):
        val = order(i, val)
        new_order[val].append(i)

    out_annotation = util.create_empty_attribute(doc, in_annotation)

    nr_digits = len(str(len(new_order) - 1 + start))
    for nr, key in enumerate(sorted(new_order), start):
        for index in new_order[key]:
            out_annotation[index] = "{prefix}{nr:0{length}d}".format(prefix=prefix,
                                                                     length=nr_digits if zfill else 0,
                                                                     nr=nr)

    util.write_annotation(doc, out, out_annotation)


def _natural_sorting(astr):
    """Convert a string into a naturally sortable tuple."""
    return tuple(int(s) if s.isdigit() else s for s in re.split(r"(\d+)", astr))


######################################################################

if __name__ == "__main__":
    util.run.main(attribute=renumber_by_attribute,
                  shuffle=renumber_by_shuffle,
                  parent_annotation=number_by_parent
                  )
