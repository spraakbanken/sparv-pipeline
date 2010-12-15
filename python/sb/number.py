# -*- coding: utf-8 -*-

import random
import util


def number_by_position(out, text, chunk, prefix=""):
    _txt, anchor2pos, _pos2anchor = util.corpus.read_corpus_text(text)
    new_order = [(edge, prefix, anchor2pos[util.edgeStart(edge)])
                 for edge in util.read_annotation_iterkeys(chunk)]
    write_ordering(out, new_order)


def number_by_random(out, chunk, prefix=""):
    new_order = [(edge, prefix, edge) for edge in util.read_annotation_iterkeys(chunk)]
    write_ordering(out, new_order)


def number_by_attribute(out, chunk, prefix=""):
    def order(val):
        try: return int(nr)
        except ValueError: pass
        try: return float(nr)
        except ValueError: pass
        return str(nr).strip()
    new_order = [(edge, prefix, order(val))
                 for (edge, val) in util.read_annotation_iteritems(chunk)]
    write_ordering(out, new_order)


def number_by_parent(out, order, child, prefix=""):
    parent_children = dict((pid, cids.split())
                           for (pid, cids) in util.read_annotation_iteritems(child))
    new_order = [(cid, pn + prefix, (pn, n))
                 for (pid, pn) in util.read_annotation_iteritems(order)
                 for (n, cid) in enumerate(parent_children.get(pid, ()))]
    write_ordering(out, new_order)


def write_ordering(out, new_order):
    new_order.sort(key=lambda item:item[-1])
    nr_digits = len(str(len(new_order)))
    zeropad = lambda nr: "%0*d" % (nr_digits, nr)
    util.write_annotation(out, ((edge, prefix + zeropad(nr))
                                for (nr, (edge, prefix, _order)) in enumerate(new_order)))


######################################################################

if __name__ == '__main__':
    util.run.main(position=number_by_position,
                  random=number_by_random,
                  attribute=number_by_attribute,
                  parent=number_by_parent)

