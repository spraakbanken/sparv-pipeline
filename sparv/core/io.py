"""Corpus-related util functions like reading and writing annotations."""

import bz2
import gzip
import heapq
import logging
import lzma
import os
import pickle
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple, Union

from sparv.api.classes import BaseAnnotation, BaseOutput
from sparv.core import paths
from sparv.core.misc import SparvErrorMessage, get_logger

logger = get_logger(__name__)

DOC_CHUNK_DELIM = ":"
ELEM_ATTR_DELIM = ":"
SPAN_ANNOTATION = "@span"
TEXT_FILE = "@text"
STRUCTURE_FILE = "@structure"
HEADERS_FILE = "@headers"
NAMESPACE_FILE = "@namespaces"

# Compression used for annotation files (can be changed using sparv.compression in config file)
compression = "gzip"

_compressed_open = {
    "none": open,
    "gzip": gzip.open,
    "bzip2": bz2.open,
    "lzma": lzma.open
}


def annotation_exists(annotation: BaseAnnotation, source_file: Optional[str] = None) -> bool:
    """Check if an annotation file exists."""
    annotation_path = get_annotation_path(source_file or annotation.source_file, annotation, data=annotation.data)
    return annotation_path.exists()


def remove_annotation(annotation: BaseAnnotation, source_file: Optional[str] = None) -> None:
    """Remove an annotation file."""
    annotation_path = get_annotation_path(source_file or annotation.source_file, annotation, data=annotation.data)
    annotation_path.unlink(missing_ok=True)


def write_annotation(
    source_file: str,
    annotation: BaseOutput,
    values: list
) -> None:
    """Write an annotation to one or more files. The file is overwritten if it exists.

    The annotation should be a list of values.
    """
    annotations = annotation.name.split()

    if len(annotations) == 1:
        # Handle single annotation
        _write_single_annotation(source_file, annotations[0], values, annotation.root)
    else:
        elem_attrs = dict(split_annotation(ann) for ann in annotations)
        # Handle multiple annotations used as one
        assert all(
            elem_attrs.values()), "Span annotations can not be written while treating multiple annotations as one."
        # Get spans and associated names for annotations. We need this information to figure out which value goes to
        # which annotation.
        spans = read_annotation(source_file, annotation, with_annotation_name=True, spans=True)
        annotation_values = {elem: [] for elem in elem_attrs}

        for value, (_, annotation_name) in zip(values, spans):
            annotation_values[annotation_name].append(value)

        for annotation_name in annotation_values:
            _write_single_annotation(source_file, join_annotation(annotation_name, elem_attrs[annotation_name]),
                                     annotation_values[annotation_name], annotation.root)


def _write_single_annotation(
    source_file: str,
    annotation: str,
    values: list,
    root: Path
) -> None:
    """Write an annotation to a file."""
    is_span = not split_annotation(annotation)[1]

    if is_span:
        if not isinstance(values, list):
            values = list(values)
        # Validate that spans are sorted
        for i in range(len(values) - 1):
            if values[i] > values[i + 1]:
                raise SparvErrorMessage(
                    f"Annotation spans must be sorted. values[{i}]={values[i]} > values[{i+1}]={values[i+1]}",
                    module="core.io",
                    function="_write_single_annotation",
                )
        # Always save spans with decimal tuples
        if values and not isinstance(values[0][0], tuple):
            values = [((v[0],), (v[1],)) for v in values]
    else:
        # Convert all values to strings; convert None to empty string
        values = [str(v) if v is not None else "" for v in values]
    file_path = get_annotation_path(source_file, annotation, root)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    write_annotation_file(file_path, values)
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    logger.info("Wrote %d items: %s%s%s", len(values), source_file, "/" if source_file else "", annotation)


def get_annotation_size(source_file: str, annotation: BaseAnnotation) -> int:
    """Return number of lines in an annotation."""
    count = 0

    for ann in annotation.name.split():
        ann_file = get_annotation_path(source_file, ann, annotation.root)
        count += len(list(read_annotation_file(ann_file)))

    return count


def read_annotation_spans(
    source_file: str,
    annotation: BaseAnnotation,
    decimals: bool = False,
    with_annotation_name: bool = False
) -> Iterator[tuple]:
    """Iterate over the spans of an annotation."""
    # Strip any annotation attributes
    for span in read_annotation(source_file, annotation, with_annotation_name, spans=True):
        if not decimals:
            yield tuple(v[0] for v in span)
        else:
            yield span


def read_annotation(
    source_file: str,
    annotation: BaseAnnotation,
    with_annotation_name: bool = False,
    spans: bool = False
) -> Iterator:
    """Yield each line from an annotation file."""
    if spans:
        annotations = [split_annotation(ann)[0] for ann in annotation.name.split()]
    else:
        annotations = annotation.name.split()
    root = annotation.root
    if len(annotations) == 1:
        # Handle single annotation
        yield from _read_single_annotation(source_file, annotations[0], with_annotation_name, root)
    else:
        # Handle multiple annotations used as one

        # Make sure we don't have multiple attributes on the same annotation
        assert len(annotations) == len(
            {split_annotation(ann)[0] for ann in annotations}
        ), "Reading multiple attributes on the same annotation is not allowed."

        # Get iterators for all annotations
        all_annotations = {split_annotation(ann)[0]: _read_single_annotation(source_file, ann, with_annotation_name,
                                                                             root)
                           for ann in annotations}

        # We need to read the annotation spans to be able to interleave the values in the correct order
        for _, ann in heapq.merge(*[_read_single_annotation(source_file, split_annotation(ann)[0],
                                                            with_annotation_name=True,
                                                            root=root)
                                    for ann in annotations]):
            yield next(all_annotations[ann])


def read_annotation_attributes(source_file: str, annotations: Union[List[BaseAnnotation], Tuple[BaseAnnotation, ...]],
                               with_annotation_name: bool = False) -> Iterator[tuple]:
    """Yield tuples of multiple attributes on the same annotation."""
    assert isinstance(annotations, (tuple, list)), "'annotations' argument must be tuple or list"
    assert len({split_annotation(annotation)[0] for annotation in
                annotations}) == 1, "All attributes need to be for the same annotation"
    return zip(*[read_annotation(source_file, annotation, with_annotation_name)
                 for annotation in annotations])


def _read_single_annotation(
    source_file: str,
    annotation: str,
    with_annotation_name: bool,
    root: Optional[Path] = None
) -> Iterator[Any]:
    """Read a single annotation file."""
    ann_file = get_annotation_path(source_file, annotation, root)

    ctr = 0
    for value in read_annotation_file(ann_file):
        yield value if not with_annotation_name else (value, annotation)
        ctr += 1
    logger.debug("Read %d items: %s%s%s", ctr, source_file, "/" if source_file else "", annotation)


def write_data(source_file: Optional[str], name: Union[BaseAnnotation, str], value: Any) -> None:
    """Write arbitrary data to file in workdir directory."""
    file_path = get_annotation_path(source_file, name, data=True)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    write_annotation_file(file_path, value, is_data=True)

    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    if logger.isEnabledFor(logging.INFO):
        logger.info(
            "Wrote %d bytes: %s%s%s",
            file_path.stat().st_size,
            source_file,
            "/" if source_file else "",
            name.name if isinstance(name, BaseAnnotation) else name
        )


def read_data(source_file: Optional[str], name: Union[BaseAnnotation, str]) -> Any:
    """Read arbitrary data from file in workdir directory."""
    file_path = get_annotation_path(source_file, name, data=True)
    data = next(read_annotation_file(file_path, is_data=True))

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Read %d bytes: %s%s%s",
            file_path.stat().st_size,
            source_file,
            "/" if source_file else "",
            name.name if isinstance(name, BaseAnnotation) else name
        )
    return data


def split_annotation(annotation: Union[BaseAnnotation, str]) -> Tuple[str, str]:
    """Split annotation into annotation name and attribute."""
    if isinstance(annotation, BaseAnnotation):
        annotation = annotation.name
    elem, _, attr = annotation.partition(ELEM_ATTR_DELIM)
    return elem, attr


def join_annotation(name: str, attribute: Optional[str]) -> str:
    """Join annotation name and attribute."""
    return ELEM_ATTR_DELIM.join((name, attribute)) if attribute else name


def get_annotation_path(source_file: Optional[str], annotation: Union[BaseAnnotation, str], root: Optional[Path] = None,
                        data: bool = False) -> Path:
    """Construct a path to an annotation file given a source filename and annotation."""
    chunk = ""
    if source_file:
        source_file, _, chunk = source_file.partition(DOC_CHUNK_DELIM)
    elem, attr = split_annotation(annotation)

    if data:
        if source_file:
            path = paths.work_dir / source_file / chunk / elem
        else:
            path = paths.work_dir / elem
    else:
        if not attr:
            attr = SPAN_ANNOTATION
        path = paths.work_dir / source_file / chunk / elem / attr

    if root:
        path = root / path
    elif isinstance(annotation, BaseAnnotation):
        path = annotation.root / path

    return path


def write_annotation_file(file_path: Path, value: Any, is_data: bool = False) -> None:
    """Write annotation data to a file."""
    chunk_size = 1000
    opener = _compressed_open.get(compression, open)
    with opener(file_path, mode="wb") as f:
        if is_data:
            pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            for i in range(0, len(value), chunk_size):
                pickle.dump(value[i:i + chunk_size], f, protocol=pickle.HIGHEST_PROTOCOL)


def read_annotation_file(file_path: Path, is_data: bool = False) -> Iterator:
    """Return an iterator for reading an annotation file."""
    opener = _compressed_open.get(compression, open)
    with opener(file_path, mode="rb") as f:
        try:
            if is_data:
                yield pickle.load(f)
                return
            else:
                try:
                    while True:
                        yield from pickle.load(f)
                except EOFError:
                    return
        except pickle.UnpicklingError:
            raise SparvErrorMessage(
                "The workdir files for this corpus could not be read. They were probably created using an older "
                "version of Sparv. Run 'sparv clean' to start over with a clean workdir."
            ) from None
        except (gzip.BadGzipFile, OSError, lzma.LZMAError, UnicodeDecodeError) as e:
            if isinstance(e, OSError) and str(e) != "Invalid data stream":
                raise e
            raise SparvErrorMessage(
                f"Compression of workdir files is set to '{compression}', but '{file_path}' is in another "
                "format. Use the configuration key 'sparv.compression' to set the correct compression or "
                "use 'sparv clean' to start over with a clean workdir.") from None
