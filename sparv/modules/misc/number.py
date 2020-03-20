from collections import defaultdict
import random
import sparv.util as util
import re
from binascii import hexlify

START_DEFAULT = 1


def number_by_position(doc, out, chunk, prefix="", start=START_DEFAULT):
    """Number chunks by their position."""

    spans = list(util.read_annotation_spans(doc, chunk))

    def order(index, _value):
        return spans[index]

    read_chunks_and_write_new_ordering(doc, out, chunk, order, prefix, start)


def number_by_random(doc, out, chunk, prefix="", start=START_DEFAULT):
    """Number chunks randomly.
    Uses index as random seed."""
    def order(index, _value):
        random.seed(int(hexlify(str(index).encode()), 16))
        return random.random()

    read_chunks_and_write_new_ordering(doc, out, chunk, order, prefix, start)


def renumber_by_attribute(doc, out, chunk, prefix="", start=START_DEFAULT):
    """Renumber chunks, with the order determined by an attribute."""
    def order(_index, value):
        return natural_sorting(value)

    read_chunks_and_write_new_ordering(doc, out, chunk, order, prefix, start)


def renumber_by_shuffle(doc, out, chunk, prefix="", start=START_DEFAULT):
    """Renumber already numbered chunks, in new random order.
       Retains the connection between parallelly numbered chunks by using the values as random seed."""
    def order(_index, value):
        random.seed(int(hexlify(value.encode()), 16))
        return random.random(), natural_sorting(value)

    read_chunks_and_write_new_ordering(doc, out, chunk, order, prefix, start)


def number_by_parent(doc, out, chunk, parent_order, prefix="", start=START_DEFAULT):
    """Number chunks by (parent order, chunk order)."""
    parent_children, _orphans = util.get_children(doc, parent_order, chunk)

    child_order = {child_index: (parent_nr, child_index)
                   for parent_index, parent_nr in enumerate(util.read_annotation(doc, parent_order))
                   for child_index in parent_children[parent_index]}

    def order(index, _value):
        return child_order.get(index)

    read_chunks_and_write_new_ordering(doc, out, chunk, order, prefix, start)


def number_relative(doc, out, parent, child, prefix="", start=START_DEFAULT):
    """Number chunks by their relative position within a parent."""
    parent_children, orphans = util.get_children(doc, parent, child)

    util.write_annotation(doc, out, ("%s%0*d" % (prefix, len(str(len(parent) - 1 + start)), cnr)
                                     for parent in parent_children
                                     for cnr, _index in enumerate(parent, start)))


def read_chunks_and_write_new_ordering(doc, out, chunk, order, prefix="", start=START_DEFAULT):
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
            out_annotation[index] = "%s%0*d" % (prefix, nr_digits, nr)

    util.write_annotation(doc, out, out_annotation)


def natural_sorting(astr):
    """Convert a string into a naturally sortable tuple."""
    return tuple(int(s) if s.isdigit() else s for s in re.split(r"(\d+)", astr))


######################################################################

if __name__ == "__main__":
    util.run.main(position=number_by_position,
                  random=number_by_random,
                  attribute=renumber_by_attribute,
                  shuffle=renumber_by_shuffle,
                  parent_annotation=number_by_parent,
                  relative=number_relative,
                  )
