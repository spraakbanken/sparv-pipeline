"""Corpus-related util functions like reading and writing annotations."""

import heapq
import logging
import os
import pathlib
import re
from typing import Union

from sparv.core import paths
from .classes import BaseAnnotation, Model, AnnotationAllDocs, Annotation

_log = logging.getLogger(__name__)

######################################################################
# Annotations

DOC_CHUNK_DELIM = ":"
ELEM_ATTR_DELIM = ":"
SPAN_ANNOTATION = "@span"
TEXT_FILE = "@text"
STRUCTURE_FILE = "@structure"
HEADERS_FILE = "@headers"
HEADER_CONTENT = "contents"


def annotation_exists(doc, annotation):
    """Check if an annotation file exists."""
    annotation_path = get_annotation_path(doc, annotation)
    return os.path.exists(annotation_path)


def data_exists(doc, name):
    """Check if an annotation data file exists."""
    annotation_path = get_annotation_path(doc, name, data=True)
    return os.path.isfile(annotation_path)


def clear_annotation(doc, annotation):
    """Remove an annotation file if it exists."""
    annotation_path = get_annotation_path(doc, annotation)
    if os.path.exists(annotation_path):
        os.remove(annotation_path)


def has_attribute(annotation):
    """Return True if annotation has an attribute."""
    return ELEM_ATTR_DELIM in annotation


def write_annotation(doc, annotation, values, append=False, allow_newlines=False):
    """Write an annotation to one or more files. The file is overwritten if it exists.

    The annotation should be a list of values.
    """
    if isinstance(annotation, BaseAnnotation):
        annotation = annotation.name.split()
    elif isinstance(annotation, str):
        annotation = annotation.split()

    if len(annotation) == 1:
        # Handle single annotation
        _write_single_annotation(doc, annotation[0], values, append, allow_newlines)
    else:
        elem_attrs = dict(split_annotation(ann) for ann in annotation)
        # Handle multiple annotations used as one
        assert all(elem_attrs.values()), "Span annotations can not be written while treating multiple annotations as one."
        # Get spans and associated names for annotations. We need this information to figure out which value goes to
        # which annotation.
        spans = read_annotation(doc, elem_attrs.keys(), with_annotation_name=True)
        annotation_values = {elem: [] for elem in elem_attrs.keys()}

        for value, (_, annotation_name) in zip(values, spans):
            annotation_values[annotation_name].append(value)

        for annotation_name in annotation_values:
            _write_single_annotation(doc, join_annotation(annotation_name, elem_attrs[annotation_name]),
                                     annotation_values[annotation_name], append, allow_newlines)


def _write_single_annotation(doc, annotation, values, append, allow_newlines=False):
    """Write an annotation to a file."""
    is_span = not split_annotation(annotation)[1]

    if is_span:
        # Make sure that spans are sorted
        assert all(values[i] <= values[i + 1] for i in range(len(values) - 1)), "Annotation spans must be sorted."
    file_path = get_annotation_path(doc, annotation)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    mode = "a" if append else "w"
    with open(file_path, mode) as f:
        ctr = 0
        for value in values:
            if value is None:
                value = ""
            elif is_span:
                start, end = value
                start_subpos, end_subpos = None, None
                if isinstance(start, tuple):
                    start, start_subpos = start
                if isinstance(end, tuple):
                    end, end_subpos = end
                start_subpos = ".{}".format(start_subpos) if start_subpos is not None else ""
                end_subpos = ".{}".format(end_subpos) if end_subpos is not None else ""
                value = "{}{}-{}{}".format(start, start_subpos, end, end_subpos)
            elif allow_newlines:
                # Replace line breaks with "\n"
                value = value.replace("\\", r"\\").replace("\n", r"\n").replace("\r", "")
            else:
                # Remove line breaks entirely
                value = value.replace("\n", "").replace("\r", "")
            print(value, file=f)
            ctr += 1
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    _log.info("Wrote %d items: %s/%s", ctr, doc, annotation)


def create_empty_attribute(annotation):
    """Return a list filled with None of the same size as 'annotation'.

    'annotation' can be either of the following:
    - the name of an annotation
    - a list (i.e. an annotation that has already been loaded)
    - an integer
    """
    assert isinstance(annotation, (Annotation, list, int))

    if isinstance(annotation, Annotation):
        length = len(list(annotation.read_spans()))
    elif isinstance(annotation, list):
        length = len(annotation)
    elif isinstance(annotation, int):
        length = annotation
    return [None] * length


def read_annotation_spans(doc, annotation, decimals=False, with_annotation_name=False):
    """Iterate over the spans of an annotation."""
    if isinstance(annotation, BaseAnnotation):
        annotation = annotation.name
    # Strip any annotation attributes
    annotation = [split_annotation(ann)[0] for ann in annotation.split()]
    for span in read_annotation(doc, annotation, with_annotation_name):
        if not decimals:
            yield tuple(v[0] for v in span)
        else:
            yield span


def read_annotation(doc, annotation, with_annotation_name=False, allow_newlines=False):
    """Yield each line from an annotation file."""
    if isinstance(annotation, BaseAnnotation):
        annotation = annotation.name.split()
    elif isinstance(annotation, str):
        annotation = annotation.split()
    if len(annotation) == 1:
        # Handle single annotation
        yield from _read_single_annotation(doc, annotation[0], with_annotation_name, allow_newlines)
    else:
        # Handle multiple annotations used as one

        # Make sure we don't have multiple attributes on the same annotation
        assert len(annotation) == len(set(split_annotation(ann)[0]
                                          for ann in annotation)), "Reading multiple attributes on the same " \
                                                                   "annotation is not allowed."

        # Get iterators for all annotations
        all_annotations = {split_annotation(ann)[0]: _read_single_annotation(doc, ann, with_annotation_name,
                                                                             allow_newlines)
                           for ann in annotation}

        # We need to read the annotation spans to be able to interleave the values in the correct order
        for _, ann in heapq.merge(*[_read_single_annotation(doc, split_annotation(ann)[0], with_annotation_name=True,
                                                            allow_newlines=allow_newlines)
                                    for ann in annotation]):
            yield next(all_annotations[ann])


def read_annotation_attributes(doc, annotations, with_annotation_name=False, allow_newlines=False):
    """Yield tuples of multiple attributes on the same annotation."""
    assert isinstance(annotations, (tuple, list)), "'annotations' argument must be tuple or list"
    assert len(set(split_annotation(annotation)[0] for annotation in annotations)), "All attributes need to be for " \
                                                                                    "the same annotation spans"
    return zip(*[read_annotation(doc, annotation, with_annotation_name, allow_newlines)
                 for annotation in annotations])


def _read_single_annotation(doc, annotation, with_annotation_name, allow_newlines=False):
    """Read a single annotation file."""
    ann_file = get_annotation_path(doc, annotation)

    with open(ann_file) as f:
        ctr = 0
        for line in f:
            value = line.rstrip("\n\r")
            if not split_annotation(annotation)[1]:  # If this is a span annotation
                value = tuple(tuple(map(int, pos.split("."))) for pos in value.split("-"))
            elif allow_newlines:
                # Replace literal "\n" with line break (if we allow "\n" in values)
                value = re.sub(r"((?<!\\)(?:\\\\)*)\\n", r"\1\n", value).replace(r"\\", "\\")
            yield value if not with_annotation_name else (value, annotation)
            ctr += 1
    _log.info("Read %d items: %s/%s", ctr, doc, annotation)


def write_data(doc, name, value, append=False):
    """Write arbitrary string data to file in annotations directory."""
    file_path = get_annotation_path(doc, name, data=True)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    mode = "a" if append else "w"

    with open(file_path, mode) as f:
        f.write(value)
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    _log.info("Wrote %d bytes: %s/%s", len(value), doc, name)


def read_data(doc, name):
    """Read arbitrary string data from file in annotations directory."""
    file_path = get_annotation_path(doc, name, data=True)

    with open(file_path) as f:
        data = f.read()
    _log.info("Read %d bytes: %s/%s", len(data), doc, name)
    return data


def write_common_data(name, value, append=False):
    """Write arbitrary corpus level string data to file in annotations directory."""
    write_data(None, name, value, append)
    _log.info("Wrote: %s", name)


def read_common_data(name):
    """Read arbitrary corpus level string data from file in annotations directory."""
    return read_data(None, name)


def write_structure(doc, structure):
    """Sort the document's structural elements and write structure file."""
    file_path = get_annotation_path(doc, STRUCTURE_FILE, data=True)
    structure.sort()
    with open(file_path, "w") as f:
        f.write("\n".join(structure))
    _log.info("Wrote: %s", file_path)


def split_annotation(annotation):
    """Split annotation into annotation name and attribute."""
    if isinstance(annotation, BaseAnnotation):
        annotation = annotation.name
    elem, _, attr = annotation.partition(ELEM_ATTR_DELIM)
    return elem, attr


def join_annotation(name, attribute):
    """Join annotation name and attribute."""
    return ELEM_ATTR_DELIM.join((name, attribute)) if attribute else name


def get_annotation_path(doc, annotation, data=False):
    """Construct a path to an annotation file given a doc and annotation."""
    if doc:
        doc, _, chunk = doc.partition(DOC_CHUNK_DELIM)
    elem, attr = split_annotation(annotation)

    if data:
        if doc:
            path = os.path.join(paths.annotation_dir, doc, chunk, elem)
        else:
            path = os.path.join(paths.annotation_dir, elem)
    else:
        if not attr:
            attr = SPAN_ANNOTATION
        path = os.path.join(paths.annotation_dir, doc, chunk, elem, attr)
    return path


def chain(annotations, default=None):
    """Create a functional composition of a list of annotations.

    E.g., token.sentence + sentence.id -> token.sentence-id

    >>> from pprint import pprint
    >>> pprint(dict(
    ...   chain([{"w:1": "s:A",
    ...           "w:2": "s:A",
    ...           "w:3": "s:B",
    ...           "w:4": "s:C",
    ...           "w:5": "s:missing"},
    ...          {"s:A": "text:I",
    ...           "s:B": "text:II",
    ...           "s:C": "text:mystery"},
    ...          {"text:I": "The Bible",
    ...           "text:II": "The Samannaphala Sutta"}],
    ...         default="The Principia Discordia")))
    {'w:1': 'The Bible',
     'w:2': 'The Bible',
     'w:3': 'The Samannaphala Sutta',
     'w:4': 'The Principia Discordia',
     'w:5': 'The Principia Discordia'}
    """
    def follow(key):
        for annot in annotations:
            try:
                key = annot[key]
            except KeyError:
                return default
        return key
    return ((key, follow(key)) for key in annotations[0])


def test_lexicon(lexicon, testwords):
    """Test the validity of a lexicon.

    Takes a dictionary (lexicon) and a list of test words.
    Prints the value for each test word.
    """
    _log.info("Testing annotations...")
    for key in testwords:
        _log.info("  %s = %s", key, lexicon.get(key))


class PickledLexicon:
    """Read basic pickled lexicon and look up keys."""

    def __init__(self, picklefile: Union[pathlib.Path, Model], verbose=True):
        """Read lexicon from picklefile."""
        import pickle
        picklefile_path: pathlib.Path = picklefile.path if isinstance(picklefile, Model) else picklefile
        if verbose:
            _log.info("Reading lexicon: %s", picklefile)
        with open(picklefile_path, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            _log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, key, default=set()):
        """Lookup a key in the lexicon."""
        return self.lexicon.get(key, default)


######################################################################
# Corpus text

def read_corpus_text(doc):
    """Read the text contents of a corpus and return as a string."""
    text_file = get_annotation_path(doc, TEXT_FILE, data=True)
    with open(text_file) as f:
        text = f.read()
    _log.info("Read %d chars: %s", len(text), text_file)
    return text


def write_corpus_text(doc, text):
    """Write text to the designated file of a corpus.

    text is a unicode string.
    """
    doc, _, _chunk = doc.partition(DOC_CHUNK_DELIM)
    text_file = get_annotation_path(doc, TEXT_FILE, data=True)
    os.makedirs(os.path.dirname(text_file), exist_ok=True)
    with open(text_file, "w") as f:
        f.write(text)
    _log.info("Wrote %d chars: %s", len(text), text_file)
