# -*- coding: utf-8 -*-

"""
Small annotations that don't fit as standalone python files.
"""

from . import util
import re


def text_spans(text, chunk, out):
    """Add the text content for each edge as a new annotation."""
    if isinstance(text, str):
        text = util.corpus.read_corpus_text(text)
    if isinstance(chunk, str):
        chunk = util.read_annotation_iterkeys(chunk)
    corpus_text, anchor2pos, _pos2anchor = text
    OUT = {}
    for edge in chunk:
        start = anchor2pos[util.edgeStart(edge)]
        end = anchor2pos[util.edgeEnd(edge)]
        OUT[edge] = corpus_text[start:end]
    if out:
        util.write_annotation(out, OUT)
    else:
        return OUT


def text_headtail(text, chunk, order, out_head, out_tail):
    """Extract "head" and "tail" whitespace characters for tokens."""

    def escape(t):
        return t.replace(" ", "\\s").replace("\n", "\\n").replace("\t", "\\t")

    if isinstance(text, str):
        text = util.corpus.read_corpus_text(text)
    if isinstance(chunk, str):
        chunk = util.read_annotation_iterkeys(chunk)
    if isinstance(order, str):
        order = util.read_annotation(order)
    corpus_text, anchor2pos, _pos2anchor = text
    OUT_HEAD = {}
    OUT_TAIL = {}
    head_text = None
    sorted_chunk = sorted(chunk, key=lambda x: order[x])

    for i, edge in enumerate(sorted_chunk):
        if head_text:
            OUT_HEAD[edge] = escape(head_text)
            head_text = None

        if i < len(sorted_chunk) - 1:
            tail_start = anchor2pos[util.edgeEnd(edge)]
            tail_end = anchor2pos[util.edgeStart(sorted_chunk[i + 1])]
            tail_text = corpus_text[tail_start:tail_end]

            try:
                n_pos = tail_text.rindex("\n")
            except ValueError:
                n_pos = None
            if n_pos is not None and n_pos + 1 < len(tail_text):
                head_text = tail_text[n_pos + 1:]
                tail_text = tail_text[:n_pos + 1]

            if tail_text:
                OUT_TAIL[edge] = escape(tail_text)

    if out_head and out_tail:
        util.write_annotation(out_head, OUT_HEAD)
        util.write_annotation(out_tail, OUT_TAIL)
    else:
        return OUT_HEAD, OUT_TAIL


def translate_tag(tag, out, mapping):
    """Convert part-of-speech tags, specified by the mapping.
    Example mappings: parole_to_suc, suc_to_simple, ...
    """
    if isinstance(mapping, str):
        mapping = util.tagsets.__dict__[mapping]
    util.write_annotation(out, ((n, mapping.get(t, t))
                                for (n, t) in util.read_annotation_iteritems(tag)))


def chain(out, annotations, default=None):
    """Create a functional composition of a list of annotations.
    E.g., token.sentence + sentence.id -> token.sentence-id
    """
    if isinstance(annotations, str):
        annotations = annotations.split()
    annotations = [util.read_annotation(a) for a in annotations]
    util.write_annotation(out, util.corpus.chain(annotations, default))


def span_as_value(out, keys):
    """Create new annotation, with edge span as value."""
    util.write_annotation(out, ((key, util.edgeStart(key) + "-" + util.edgeEnd(key)) for key in util.read_annotation(keys)))


def select(out, annotation, index, separator=None):
    """Select a specific index from the values of an annotation.
    The given annotation values are separated by 'separator',
    by default whitespace, with at least index + 1 elements.
    """
    if isinstance(index, str):
        index = int(index)
    util.write_annotation(out, ((key, items.split(separator)[index])
                                for (key, items) in util.read_annotation_iteritems(annotation)))


def constant(chunk, out, value=None):
    """Create an annotation with a constant value for each key."""
    util.write_annotation(out, ((key, value if value else value) for key in util.read_annotation_iterkeys(chunk)))


def affix(chunk, out, prefix="", suffix=""):
    """Add prefix and/or suffix to annotation."""
    util.write_annotation(out, ((key, prefix + val + suffix) for (key, val) in util.read_annotation_iteritems(chunk)))


def replace(chunk, out, find, sub=""):
    """Find and replace annotation. Find string must match whole annotation."""
    util.write_annotation(out, ((key, sub if val == find else val) for (key, val) in util.read_annotation_iteritems(chunk)))


def replace_list(chunk, out, find, sub=""):
    """Find and replace annotations. Find string must match whole annotation.
    find and sub are whitespace separated lists of words to replace and their replacement."""
    find = find.split()
    sub = sub.split()
    assert len(find) == len(sub), "find and len must have the same number of words."
    translate = dict((f, s) for (f, s) in zip(find, sub))
    util.write_annotation(out, ((key, translate.get(val, val)) for (key, val) in util.read_annotation_iteritems(chunk)))


def find_replace(chunk, out, find, sub=""):
    """Find and replace parts of or whole annotation."""
    util.write_annotation(out, ((key, val.replace(find, sub)) for (key, val) in util.read_annotation_iteritems(chunk)))


def find_replace_regex(chunk, out, find, sub=""):
    """Find and replace parts of or whole annotation."""
    util.write_annotation(out, ((key, re.sub(find, sub, val)) for (key, val) in util.read_annotation_iteritems(chunk)))


def concat(out, left, right, separator="", merge_twins=""):
    """Concatenate values from two annotations, with an optional separator.
    If merge_twins is set to True, no concatenation will be done on identical values."""
    merge_twins = merge_twins.lower() == "true"
    b = util.read_annotation(right)
    util.write_annotation(out, ((key_a, u"%s%s%s" % (val_a, separator, b[key_a]) if not (merge_twins and val_a == b[key_a]) else val_a) for (key_a, val_a) in util.read_annotation_iteritems(left)))


def concat2(out, annotations, separator=""):
    """Concatenate two or more annotations, with an optional separator."""
    if isinstance(annotations, str):
        annotations = annotations.split()

    annotations = [util.read_annotation(a) for a in annotations]
    util.write_annotation(out, [(k, separator.join([a[k] for a in annotations])) for k in annotations[0]])


def merge(out, main, backoff, encoding=util.UTF8):
    """Take two annotations, and for keys without values in 'main', use value from 'backoff'."""
    backoff = util.read_annotation(backoff)
    util.write_annotation(out, ((key, val) if val else (key, backoff[key]) for (key, val) in util.read_annotation_iteritems(main)))


def override(out, main, repl, encoding=util.UTF8):
    """Take two annotations, and for keys that have values in 'repl', use value from 'repl'."""
    repl = util.read_annotation(repl)
    util.write_annotation(out, ((key, repl[key]) if repl.get(key) else (key, val) for (key, val) in util.read_annotation_iteritems(main)))


def roundfloat(chunk, out, decimals):
    """Round floats to the given number of decimals."""
    decimals = int(decimals)
    strformat = "%." + str(decimals) + "f"
    util.write_annotation(out, ((key, strformat % round(float(val), decimals)) for (key, val) in util.read_annotation_iteritems(chunk)))


if __name__ == '__main__':
    util.run.main(text_spans=text_spans,
                  text_headtail=text_headtail,
                  translate_tag=translate_tag,
                  chain=chain,
                  select=select,
                  constant=constant,
                  affix=affix,
                  replace=replace,
                  replace_list=replace_list,
                  find_replace=find_replace,
                  find_replace_regex=find_replace_regex,
                  span_as_value=span_as_value,
                  concat=concat,
                  concat2=concat2,
                  merge=merge,
                  override=override,
                  roundfloat=roundfloat
                  )
