# -*- coding: utf-8 -*-

"""
Small annotations that don't fit as standalone python files.
"""

import util

def text_spans(text, chunk, out):
    """Add the text content for each edge as a new annotation."""
    corpus_text, anchor2pos, _pos2anchor = util.corpus.read_corpus_text(text)
    OUT = {}
    for edge in util.read_annotation_iterkeys(chunk):
        start = anchor2pos[util.edgeStart(edge)]
        end = anchor2pos[util.edgeEnd(edge)]
        OUT[edge] = corpus_text[start:end]
    util.write_annotation(out, OUT)


def translate_tag(tag, out, mapping):
    """Convert part-of-speech tags, specified by the mapping.
    Example mappings: parole_to_suc, suc_to_simple, ...
    """
    if isinstance(mapping, basestring):
        mapping = util.tagsets.__dict__[mapping]
    util.write_annotation(out, ((n, mapping.get(t,t))
                                for (n, t) in util.read_annotation_iteritems(tag)))


def chain(out, annotations, default=None):
    """Create a functional composition of a list of annotations.
    E.g., token.sentence + sentence.id -> token.sentence-id
    """
    if isinstance(annotations, basestring):
        annotations = annotations.split()
    annotations = [util.read_annotation(a) for a in annotations]
    def follow(key):
        for annot in annotations:
            try: key = annot[key]
            except KeyError: return default
        return key
    util.write_annotation(out, ((key, follow(key)) for key in annotations[0]))


def span_as_value(out, keys):
    """Create new annotation, with edge span as value."""
    util.write_annotation(out, ((key, util.edgeStart(key) + "-" + util.edgeEnd(key)) for key in util.read_annotation(keys)))


def select(out, annotation, index, separator=None):
    """Select a specific index from the values of an annotation.
    The given annotation values are separated by 'separator',
    default by whitespace, with at least index - 1 elements.
    """
    if isinstance(index, basestring):
        index = int(index)
    util.write_annotation(out, ((key, items.split(separator)[index])
                                for (key, items) in util.read_annotation_iteritems(annotation)))


def constant(chunk, out, value=None):
    """Create an annotation with a constant value for each key."""
    util.write_annotation(out, ((key, value) for key in util.read_annotation_iterkeys(chunk)))
    

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

def concat(out, left, right, separator="", encoding=util.UTF8):
    b = util.read_annotation(right)
    util.write_annotation(out, ((key_a, u"%s%s%s" % (val_a, separator.decode(encoding), b[key_a])) for (key_a, val_a) in util.read_annotation_iteritems(left)))
    

if __name__ == '__main__':
    util.run.main(text_spans=text_spans,
                  translate_tag=translate_tag,
                  chain=chain,
                  select=select,
                  constant=constant,
                  affix=affix,
                  replace=replace,
                  replace_list=replace_list,
                  find_replace=find_replace,
                  span_as_value=span_as_value,
                  concat=concat
                  )

