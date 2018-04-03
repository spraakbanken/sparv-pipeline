# -*- coding: utf-8 -*-
from collections import defaultdict
import random
import sparv.util as util
import re
from binascii import hexlify

START_DEFAULT = 1


def number_by_position(out, texts, chunks, prefix="", start=START_DEFAULT):
    """ Number chunks by their position. """
    if isinstance(chunks, str):
        chunks = chunks.split()
    if isinstance(texts, str):
        texts = texts.split()
    assert len(chunks) == len(texts), "You must supply the same number of texts and chunks."

    anchors = []
    for text in texts:
        _txt, anchor2pos, _pos2anchor = util.corpus.read_corpus_text(text)
        anchors.append(anchor2pos)

    def order(chunknr, edge, _value):
        value = anchors[chunknr][util.edgeStart(edge)]  # Position in corpus
        return (chunknr, value)

    read_chunks_and_write_new_ordering(out, chunks, order, prefix, start)


def number_by_random(out, chunks, prefix="", start=START_DEFAULT):
    """ Number chunks randomly. """
    def order(chunknr, edge, _value):
        random.seed(int(hexlify(edge.encode()), 16))
        return (chunknr, random.random())

    read_chunks_and_write_new_ordering(out, chunks, order, prefix, start)


def renumber_by_attribute(out, chunks, prefix="", start=START_DEFAULT):
    """ Renumber chunks, with the order determined by an attribute. """
    def order(_chunknr, _edge, value):
        return natural_sorting(value)

    read_chunks_and_write_new_ordering(out, chunks, order, prefix, start)


def renumber_by_shuffle(out, chunks, prefix="", start=START_DEFAULT):
    """ Renumber already numbered chunks, in new random order.
        Retains the connection between parallelly numbered chunks by using the values as random seed. """
    def order(_chunknr, _edge, value):
        random.seed(int(hexlify(value.encode()), 16))
        return random.random(), natural_sorting(value)

    read_chunks_and_write_new_ordering(out, chunks, order, prefix, start)


def number_by_parent(out, chunks, parent_order, parent_children, prefix="", start=START_DEFAULT):
    """ Number chunks by (parent order, chunk order). """
    PARENT_CHILDREN = util.read_annotation(parent_children)
    CHILD_ORDER = dict((cid, (pnr, cnr))
                       for (pid, pnr) in util.read_annotation_iteritems(parent_order)
                       for (cnr, cid) in enumerate(PARENT_CHILDREN.get(pid, "").split()))

    def order(chunknr, edge, _value):
        return (chunknr, CHILD_ORDER.get(edge))

    read_chunks_and_write_new_ordering(out, chunks, order, prefix, start)


def number_relative(out, parent_children, prefix="", start=START_DEFAULT):
    """ Number chunks by their relative position within a parent. """
    PARENT_CHILDREN = util.read_annotation(parent_children)

    util.write_annotation(out, ((child, "%s%0*d" % (prefix, len(str(len(PARENT_CHILDREN[parent].split()) - 1 + start)), cnr))
                                for parent in PARENT_CHILDREN
                                for cnr, child in enumerate(PARENT_CHILDREN[parent].split(), start)))


def read_chunks_and_write_new_ordering(out, chunks, order, prefix="", start=START_DEFAULT):
    if isinstance(chunks, str):
        chunks = chunks.split()

    new_order = defaultdict(list)
    for chunknr, chunk in enumerate(chunks):
        for edge, val in util.read_annotation_iteritems(chunk):
            val = order(chunknr, edge, val)
            new_order[val].append(edge)

    nr_digits = len(str(len(new_order) - 1 + start))
    util.write_annotation(out, ((edge, "%s%0*d" % (prefix, nr_digits, nr))
                                for nr, key in enumerate(sorted(new_order), start)
                                for edge in new_order[key]))


def natural_sorting(astr):
    return tuple(int(s) if s.isdigit() else s for s in re.split(r'(\d+)', astr))


######################################################################

if __name__ == '__main__':
    util.run.main(position=number_by_position,
                  random=number_by_random,
                  attribute=renumber_by_attribute,
                  shuffle=renumber_by_shuffle,
                  parent=number_by_parent,
                  relative=number_relative,
                  )
