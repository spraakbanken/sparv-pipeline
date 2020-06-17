"""Small annotators that don't fit as standalone python files."""

import re
from typing import Optional

from sparv import Annotation, Document, Output, annotator, util


@annotator("Text value of a span (usually a token)")
def text_spans(doc: str = Document,
               chunk: str = Annotation("<token>"),
               out: str = Output("<token>:misc.word", cls="token:word")):
    """Add the text content for each edge as a new annotation."""
    corpus_text = util.corpus.read_corpus_text(doc)
    if isinstance(chunk, (str, Annotation)):
        chunk = util.read_annotation_spans(doc, chunk)
    out_annotation = []
    for span in chunk:
        out_annotation.append(corpus_text[span[0]:span[1]])
    if out:
        util.write_annotation(doc, out, out_annotation)
    else:
        return out_annotation


@annotator("Head and tail whitespace characters for tokens")
def text_headtail(doc: str = Document,
                  chunk: str = Annotation("<token>"),
                  out_head: str = Output("<token>:misc.head"),
                  out_tail: str = Output("<token>:misc.tail")):
    """Extract "head" and "tail" whitespace characters for tokens."""
    def escape(t):
        """Escape whitespace characters."""
        return t.replace(" ", "\\s").replace("\n", "\\n").replace("\t", "\\t")

    text = util.corpus.read_corpus_text(doc)
    chunk = list(util.read_annotation(doc, chunk))

    out_head_annotation = util.create_empty_attribute(doc, chunk)
    out_tail_annotation = util.create_empty_attribute(doc, chunk)
    head_text = None

    for i, span in enumerate(chunk):
        if head_text:
            out_head_annotation[i] = escape(head_text)
            head_text = None

        if i < len(chunk) - 1:
            tail_start = span[1][0]
            tail_end = chunk[i + 1][0][0]
            tail_text = text[tail_start:tail_end]

            try:
                n_pos = tail_text.rindex("\n")
            except ValueError:
                n_pos = None
            if n_pos is not None and n_pos + 1 < len(tail_text):
                head_text = tail_text[n_pos + 1:]
                tail_text = tail_text[:n_pos + 1]

            if tail_text:
                out_tail_annotation[i] = escape(tail_text)

    util.write_annotation(doc, out_head, out_head_annotation)
    util.write_annotation(doc, out_tail, out_tail_annotation)


def translate_tag(tag, out, mapping):
    """Convert part-of-speech tags, specified by the mapping.

    Example mappings: parole_to_suc, suc_to_simple, ...
    """
    if isinstance(mapping, str):
        mapping = util.tagsets.__dict__[mapping]
    util.write_annotation(out, ((n, mapping.get(t, t))
                                for (n, t) in util.read_annotation_iteritems(tag)))


@annotator("Convert {struct}:{attr} into a token annotation")
def struct_to_token(doc: str = Document,
                    struct: str = Annotation("{struct}"),
                    attr: str = Annotation("{struct}:{attr}"),
                    token: str = Annotation("<token>"),
                    out: str = Output("<token>:misc.from_struct_{struct}_{attr}")):
    """Convert a structural annotation into a token annotation."""
    token_parents = util.get_parents(doc, attr, token)
    attr_values = list(util.read_annotation(doc, attr))
    out_values = [attr_values[p] if p else "" for p in token_parents]
    util.write_annotation(doc, out, out_values)


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


def select(doc, out, annotation, index, separator=None):
    """Select a specific index from the values of an annotation.

    The given annotation values are separated by 'separator',
    by default whitespace, with at least index + 1 elements.
    """
    if isinstance(index, str):
        index = int(index)
    util.write_annotation(doc, out, (value.split(separator)[index]
                                     for value in util.read_annotation(doc, annotation)))


def constant(chunk, out, value=None):
    """Create an annotation with a constant value for each key."""
    util.write_annotation(out, ((key, value if value else value) for key in util.read_annotation_iterkeys(chunk)))


@annotator("Add prefix and/or suffix to an annotation.")
def affix(doc: str = Document,
          chunk: str = Annotation,
          out: str = Output,
          prefix: Optional[str] = "",
          suffix: Optional[str] = ""):
    """Add prefix and/or suffix to annotation."""
    util.write_annotation(doc, out, [(prefix + val + suffix) for val in util.read_annotation(doc, chunk)])


def replace(chunk, out, find, sub=""):
    """Find and replace annotation. Find string must match whole annotation."""
    util.write_annotation(out, ((key, sub if val == find else val) for (key, val) in util.read_annotation_iteritems(chunk)))


def replace_list(chunk, out, find, sub=""):
    """Find and replace annotations.

    Find string must match whole annotation.
    find and sub are whitespace separated lists of words to replace and their replacement.
    """
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

    If merge_twins is set to True, no concatenation will be done on identical values.
    """
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
