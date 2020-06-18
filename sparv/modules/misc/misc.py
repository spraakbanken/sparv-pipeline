"""Small annotators that don't fit as standalone python files."""

import re
from typing import List, Optional

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


@annotator("Convert part-of-speech tags, specified by the mapping")
def translate_tag(doc: str = Document,
                  out: str = Output,
                  tag: str = Annotation,
                  mapping: dict = {}):
    """Convert part-of-speech tags, specified by the mapping.

    Example mappings: parole_to_suc, suc_to_simple, ...
    """
    if isinstance(mapping, str):
        mapping = util.tagsets.__dict__[mapping]
    util.write_annotation(doc, out, (mapping.get(t, t)
                                     for t in util.read_annotation(doc, tag)))


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


# TODO: Do we still need this? struct_to_token probably mostly replaces it
def chain(doc, out, annotations, default=None):
    """Create a functional composition of a list of annotations.

    E.g., token.sentence + sentence.id -> token.sentence-id
    """
    if isinstance(annotations, str):
        annotations = annotations.split()
    annotations = [util.read_annotation(doc, a) for a in annotations]
    util.write_annotation(doc, out, util.corpus.chain(annotations, default))


@annotator("Create new annotation, with spans as values")
def span_as_value(doc: str = Document,
                  chunk: str = Annotation,
                  out: str = Output):
    """Create new annotation, with spans as values."""
    util.write_annotation(doc, out, (f"{start}-{end}" for start, end in util.read_annotation_spans(doc, chunk)))


@annotator("Select a specific index from the values of an annotation")
def select(doc: str = Document,
           out: str = Output,
           annotation: str = Annotation,
           index: Optional[int] = 0,
           separator: Optional[str] = " "):
    """Select a specific index from the values of an annotation.

    The given annotation values are separated by 'separator',
    by default whitespace, with at least index + 1 elements.
    """
    if isinstance(index, str):
        index = int(index)
    util.write_annotation(doc, out, (value.split(separator)[index]
                                     for value in util.read_annotation(doc, annotation)))


@annotator("Create an annotation with a constant value")
def constant(doc: str = Document,
             chunk: str = Annotation,
             out: str = Output,
             value: str = ""):
    """Create an annotation with a constant value."""
    util.write_annotation(doc, out, (value for _ in util.read_annotation(doc, chunk)))


@annotator("Add prefix and/or suffix to an annotation")
def affix(doc: str = Document,
          chunk: str = Annotation,
          out: str = Output,
          prefix: Optional[str] = "",
          suffix: Optional[str] = ""):
    """Add prefix and/or suffix to annotation."""
    util.write_annotation(doc, out, [(prefix + val + suffix) for val in util.read_annotation(doc, chunk)])


@annotator("Find and replace whole annotation")
def replace(doc: str = Document,
            chunk: str = Annotation,
            out: str = Output,
            find: str = "",
            sub: Optional[str] = ""):
    """Find and replace whole annotation. Find string must match whole annotation."""
    util.write_annotation(doc, out, (sub if val == find else val for val in util.read_annotation(doc, chunk)))


@annotator("Find and replace whole annotation values")
def replace_list(doc: str = Document,
                 chunk: str = Annotation,
                 out: str = Output,
                 find: str = "",
                 sub: str = ""):
    """Find and replace annotations.

    Find string must match whole annotation.
    find and sub are whitespace separated lists of words to replace and their replacement.
    """
    find = find.split()
    sub = sub.split()
    if len(find) != len(sub):
        raise util.SparvErrorMessage("Find and sub must have the same number of words.")
    translate = dict((f, s) for (f, s) in zip(find, sub))
    util.write_annotation(doc, out, (translate.get(val, val) for val in util.read_annotation(doc, chunk)))


@annotator("Find and replace parts of or whole annotation")
def find_replace(doc: str = Document,
                 chunk: str = Annotation,
                 out: str = Output,
                 find: str = "",
                 sub: str = ""):
    """Find and replace parts of or whole annotation."""
    util.write_annotation(doc, out, (val.replace(find, sub) for val in util.read_annotation(doc, chunk)))


@annotator("Do find and replace in values of annotation using a regular expressions")
def find_replace_regex(doc: str = Document,
                       chunk: str = Annotation,
                       out: str = Output,
                       find: str = "",
                       sub: str = ""):
    """
    Do find and replace in values of annotation using a regular expressions.

    N.B: When writing regular expressions in YAML they should be enclosed in single quotes.
    """
    util.write_annotation(doc, out, (re.sub(find, sub, val) for val in util.read_annotation(doc, chunk)))


@annotator("Concatenate values from two annotations, with an optional separator")
def concat(doc: str = Document,
           out: str = Output,
           left: str = Annotation,
           right: str = Annotation,
           separator: str = "",
           merge_twins: bool = False):
    """Concatenate values from two annotations, with an optional separator.

    If merge_twins is set to True, no concatenation will be done on identical values.
    """
    b = list(util.read_annotation(doc, right))
    util.write_annotation(doc, out, (f"{val_a}{separator}{b[n]}" if not (merge_twins and val_a == b[n]) else val_a
                                     for (n, val_a) in enumerate(util.read_annotation(doc, left))))


# TODO: not working yet because we cannot handle lists of annotations as input
# @annotator("Concatenate two or more annotations, with an optional separator")
def concat2(doc: str = Document,
            out: str = Output,
            annotations: List[str] = [Annotation],
            separator: str = ""):
    """Concatenate two or more annotations, with an optional separator."""
    annotations = [list(util.read_annotation(doc, a)) for a in annotations]
    util.write_annotation(doc, out, [separator.join([a[n] for a in annotations]) for (n, _) in enumerate(annotations[0])])


@annotator("Replace empty values in 'chunk' with values from 'backoff'")
def backoff(doc: str = Document,
            chunk: str = Annotation,
            backoff: str = Annotation,
            out: str = Output):
    """Replace empty values in 'chunk' with values from 'backoff'."""
    # Function was called 'merge' before.
    backoff = list(util.read_annotation(doc, backoff))
    util.write_annotation(doc, out, (val if val else backoff[n] for (n, val) in enumerate(util.read_annotation(doc, chunk))))


@annotator("Replace values in 'chunk' with non empty values from 'repl'")
def override(doc: str = Document,
             chunk: str = Annotation,
             repl: str = Annotation,
             out: str = Output):
    """Replace values in 'chunk' with non empty values from 'repl'."""
    def empty(val):
        if not val:
            return True
        return val == "|"

    repl = list(util.read_annotation(doc, repl))
    util.write_annotation(doc, out, (
        repl[n] if not empty(repl[n]) else val for (n, val) in enumerate(util.read_annotation(doc, chunk))))


@annotator("Round floats to the given number of decimals")
def roundfloat(doc: str = Document,
               chunk: str = Annotation,
               out: str = Output,
               decimals: int = 2):
    """Round floats to the given number of decimals."""
    decimals = int(decimals)
    strformat = "%." + str(decimals) + "f"
    util.write_annotation(doc, out, (strformat % round(float(val), decimals) for val in util.read_annotation(doc, chunk)))
