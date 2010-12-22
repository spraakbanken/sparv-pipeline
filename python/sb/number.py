# -*- coding: utf-8 -*-

from collections import defaultdict
import random
import util


def read_chunks_and_write_new_ordering(out, chunks, order, prefix=""):
    if isinstance(chunks, basestring):
        chunks = chunks.split()

    new_order = defaultdict(list)
    for chunk in chunks:
        for edge, val in util.read_annotation_iteritems(chunk):
            if val is None or val.strip() == "":
                val = edge
            else:
                try: val = int(val)
                except ValueError: 
                    try: val = float(val)
                    except ValueError: pass
            new_order[val].append(edge)

    def get_item_order(item):
        val, edges = item
        return [order(edge, val) for edge in edges]

    new_order = sorted(new_order.iteritems(), key=get_item_order)

    nr_digits = len(str(len(new_order)))
    util.write_annotation(out, ((edge, "%s%0*d" % (prefix, nr_digits, nr))
                                for nr, (_key, edges) in enumerate(new_order)
                                for edge in edges))



def number_by_position(out, texts, chunk, prefix=""):
    assert " " not in chunk, "Number by position cannot handle parallel chunks."
    _txt, anchor2pos, _pos2anchor = util.corpus.read_corpus_text(text)
    order = lambda edge, _val: anchor2pos[util.edgeStart(edge)]
    read_chunks_and_write_new_ordering(out, chunk, order, prefix)


def number_by_random(out, chunks, prefix=""):
    # Since the anchors are (almost) random, we can use the edge spans as ordering:
    order = lambda edge, _val: util.edgeSpans(edge)
    read_chunks_and_write_new_ordering(out, chunks, order, prefix)


def number_by_attribute(out, chunks, prefix=""):
    order = lambda _edge, val: val
    read_chunks_and_write_new_ordering(out, chunks, order, prefix)


def number_by_parent(out, chunk, parent_order, parent_children, prefix=""):
    assert " " not in chunk, "Number by parent cannot handle parallel chunks."
    PARENT_CHILDREN = util.read_annotation(parent_children)
    CHILD_ORDER = dict((cid, (pnr, cnr))
                       for (pid, pnr) in util.read_annotation_iteritems(parent_order)
                       for (cnr, cid) in enumerate(PARENT_CHILDREN.get(pid,"").split()))
    order = lambda edge, _val: CHILD_ORDER.get(edge)
    read_chunks_and_write_new_ordering(out, chunk, order, prefix)


######################################################################

if __name__ == '__main__':
    util.run.main(position=number_by_position,
                  random=number_by_random,
                  attribute=number_by_attribute,
                  parent=number_by_parent,
                  )

