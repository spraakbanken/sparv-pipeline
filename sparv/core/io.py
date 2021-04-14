"""Corpus-related util functions like reading and writing annotations."""

import heapq
import logging
import os
import re
from pathlib import Path
from typing import Union, Tuple, List, Optional

from sparv.core import paths
from sparv.util.classes import BaseAnnotation, BaseOutput

_log = logging.getLogger(__name__)

DOC_CHUNK_DELIM = ":"
ELEM_ATTR_DELIM = ":"
SPAN_ANNOTATION = "@span"
TEXT_FILE = "@text"
STRUCTURE_FILE = "@structure"
HEADERS_FILE = "@headers"


def annotation_exists(doc: str, annotation: BaseAnnotation):
    """Check if an annotation file exists."""
    annotation_path = get_annotation_path(doc, annotation)
    return os.path.exists(annotation_path)


def data_exists(doc: str, name: BaseAnnotation):
    """Check if an annotation data file exists."""
    annotation_path = get_annotation_path(doc, name, data=True)
    return os.path.isfile(annotation_path)


def write_annotation(doc: str, annotation: BaseOutput, values, append: bool = False,
                     allow_newlines: bool = False) -> None:
    """Write an annotation to one or more files. The file is overwritten if it exists.

    The annotation should be a list of values.
    """
    annotations = annotation.name.split()

    if len(annotations) == 1:
        # Handle single annotation
        _write_single_annotation(doc, annotations[0], values, append, annotation.root, allow_newlines)
    else:
        elem_attrs = dict(split_annotation(ann) for ann in annotations)
        # Handle multiple annotations used as one
        assert all(
            elem_attrs.values()), "Span annotations can not be written while treating multiple annotations as one."
        # Get spans and associated names for annotations. We need this information to figure out which value goes to
        # which annotation.
        spans = read_annotation(doc, annotation, with_annotation_name=True, spans=True)
        annotation_values = {elem: [] for elem in elem_attrs.keys()}

        for value, (_, annotation_name) in zip(values, spans):
            annotation_values[annotation_name].append(value)

        for annotation_name in annotation_values:
            _write_single_annotation(doc, join_annotation(annotation_name, elem_attrs[annotation_name]),
                                     annotation_values[annotation_name], append, annotation.root, allow_newlines)


def _write_single_annotation(doc: str, annotation: str, values, append: bool, root: Path, allow_newlines: bool = False):
    """Write an annotation to a file."""
    is_span = not split_annotation(annotation)[1]

    if is_span:
        # Make sure that spans are sorted
        assert all(values[i] <= values[i + 1] for i in range(len(values) - 1)), "Annotation spans must be sorted."
    file_path = get_annotation_path(doc, annotation, root)
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
    _log.info(f"Wrote {ctr} items: {doc + '/' if doc else ''}{annotation}")


def read_annotation_spans(doc: str, annotation: BaseAnnotation, decimals: bool = False,
                          with_annotation_name: bool = False):
    """Iterate over the spans of an annotation."""
    # Strip any annotation attributes
    for span in read_annotation(doc, annotation, with_annotation_name, spans=True):
        if not decimals:
            yield tuple(v[0] for v in span)
        else:
            yield span


def read_annotation(doc: str, annotation: BaseAnnotation, with_annotation_name: bool = False,
                    allow_newlines: bool = False, spans: bool = False):
    """Yield each line from an annotation file."""
    if spans:
        annotations = [split_annotation(ann)[0] for ann in annotation.name.split()]
    else:
        annotations = annotation.name.split()
    root = annotation.root
    if len(annotations) == 1:
        # Handle single annotation
        yield from _read_single_annotation(doc, annotations[0], with_annotation_name, root, allow_newlines)
    else:
        # Handle multiple annotations used as one

        # Make sure we don't have multiple attributes on the same annotation
        assert len(annotations) == len(set(split_annotation(ann)[0]
                                           for ann in annotations)), "Reading multiple attributes on the same " \
                                                                     "annotation is not allowed."

        # Get iterators for all annotations
        all_annotations = {split_annotation(ann)[0]: _read_single_annotation(doc, ann, with_annotation_name, root,
                                                                             allow_newlines)
                           for ann in annotations}

        # We need to read the annotation spans to be able to interleave the values in the correct order
        for _, ann in heapq.merge(*[_read_single_annotation(doc, split_annotation(ann)[0], with_annotation_name=True,
                                                            root=root, allow_newlines=allow_newlines)
                                    for ann in annotations]):
            yield next(all_annotations[ann])


def read_annotation_attributes(doc: str, annotations: Union[List[BaseAnnotation], Tuple[BaseAnnotation, ...]],
                               with_annotation_name: bool = False, allow_newlines: bool = False):
    """Yield tuples of multiple attributes on the same annotation."""
    assert isinstance(annotations, (tuple, list)), "'annotations' argument must be tuple or list"
    assert len(set(split_annotation(annotation)[0] for annotation in annotations)) == 1, "All attributes need to be " \
                                                                                         "for the same annotation"
    return zip(*[read_annotation(doc, annotation, with_annotation_name, allow_newlines)
                 for annotation in annotations])


def _read_single_annotation(doc: str, annotation: str, with_annotation_name: bool, root: Path = None,
                            allow_newlines: bool = False):
    """Read a single annotation file."""
    ann_file = get_annotation_path(doc, annotation, root)

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
    _log.debug(f"Read {ctr} items: {doc + '/' if doc else ''}{annotation}")


def write_data(doc: Optional[str], name: Union[BaseAnnotation, str], value: str, append: bool = False):
    """Write arbitrary string data to file in workdir directory."""
    file_path = get_annotation_path(doc, name, data=True)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    mode = "a" if append else "w"

    with open(file_path, mode) as f:
        f.write(value)
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    _log.info(f"Wrote {len(value)} bytes: {doc + '/' if doc else ''}"
              f"{name.name if isinstance(name, BaseAnnotation) else name}")


def read_data(doc: Optional[str], name: Union[BaseAnnotation, str]):
    """Read arbitrary string data from file in workdir directory."""
    file_path = get_annotation_path(doc, name, data=True)

    with open(file_path) as f:
        data = f.read()
    _log.debug(f"Read {len(data)} bytes: {doc + '/' if doc else ''}"
               f"{name.name if isinstance(name, BaseAnnotation) else name}")
    return data


def split_annotation(annotation: Union[BaseAnnotation, str]) -> Tuple[str, str]:
    """Split annotation into annotation name and attribute."""
    if isinstance(annotation, BaseAnnotation):
        annotation = annotation.name
    elem, _, attr = annotation.partition(ELEM_ATTR_DELIM)
    return elem, attr


def join_annotation(name: str, attribute: str) -> str:
    """Join annotation name and attribute."""
    return ELEM_ATTR_DELIM.join((name, attribute)) if attribute else name


def get_annotation_path(doc: Optional[str], annotation: Union[BaseAnnotation, str], root: Path = None,
                        data: bool = False) -> Path:
    """Construct a path to an annotation file given a doc and annotation."""
    chunk = ""
    if doc:
        doc, _, chunk = doc.partition(DOC_CHUNK_DELIM)
    elem, attr = split_annotation(annotation)

    if data:
        if doc:
            path = paths.work_dir / doc / chunk / elem
        else:
            path = paths.work_dir / elem
    else:
        if not attr:
            attr = SPAN_ANNOTATION
        path = paths.work_dir / doc / chunk / elem / attr

    if root:
        path = root / path
    elif isinstance(annotation, BaseAnnotation):
        path = annotation.root / path

    return path
