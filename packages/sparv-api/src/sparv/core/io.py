"""Corpus-related utility functions for operations on annotation files."""

from __future__ import annotations

import bz2
import gzip
import heapq
import logging
import lzma
import os
import pickle
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sparv.api.classes import BaseAnnotation, BaseOutput
from sparv.core.misc import SparvErrorMessage, get_logger
from sparv.core.paths import paths

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
    "lzma": lzma.open,
}


def annotation_exists(annotation: BaseAnnotation, source_file: str | None = None) -> bool:
    """Check if an annotation file exists.

    Args:
        annotation: Annotation object to check.
        source_file: Related source file.

    Returns:
        True if the annotation file exists, False otherwise.
    """
    annotation_path = get_annotation_path(source_file or annotation.source_file, annotation, data=annotation.data)
    return annotation_path.exists()


def remove_annotation(annotation: BaseAnnotation, source_file: str | None = None) -> None:
    """Remove an annotation file."""
    annotation_path = get_annotation_path(source_file or annotation.source_file, annotation, data=annotation.data)
    annotation_path.unlink(missing_ok=True)


def write_annotation(source_file: str, annotation: BaseOutput, values: list) -> None:
    """Write an annotation to one or more files. The file is overwritten if it exists.

    Args:
        source_file: Source filename.
        annotation: Annotation object.
        values: List of values to write.
    """
    annotations = annotation.name.split()

    if len(annotations) == 1:
        # Handle single annotation
        _write_single_annotation(source_file, annotations[0], values, annotation.root)
    else:
        elem_attrs = dict(split_annotation(ann) for ann in annotations)
        # Handle multiple annotations used as one
        assert all(elem_attrs.values()), (
            "Span annotations cannot be written while treating multiple annotations as one."
        )
        # Get spans and associated names for annotations. We need this information to figure out which value goes to
        # which annotation.
        spans = read_annotation(source_file, annotation, with_annotation_name=True, spans=True)
        annotation_values = {elem: [] for elem in elem_attrs}

        for value, (_, annotation_name) in zip(values, spans, strict=True):
            annotation_values[annotation_name].append(value)

        for annotation_name in annotation_values:  # noqa: PLC0206
            _write_single_annotation(
                source_file,
                join_annotation(annotation_name, elem_attrs[annotation_name]),
                annotation_values[annotation_name],
                annotation.root,
            )


def _write_single_annotation(source_file: str, annotation: str, values: list, root: Path) -> None:
    """Write an annotation to a file.

    Args:
        source_file: Source filename.
        annotation: Annotation name.
        values: List of values to write.
        root: Root directory for the annotation.

    Raises:
        SparvErrorMessage: If annotation spans are not sorted.
    """
    is_span = not split_annotation(annotation)[1]

    if is_span:
        if not isinstance(values, list):
            values = list(values)
        # Validate that spans are sorted
        for i in range(len(values) - 1):
            if values[i] > values[i + 1]:
                raise SparvErrorMessage(
                    f"Annotation spans must be sorted. values[{i}]={values[i]} > values[{i + 1}]={values[i + 1]}",
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
    """Return the number of lines in an annotation.

    Args:
        source_file: Source filename.
        annotation: Annotation object.

    Returns:
        Number of values in the annotation.
    """
    count = 0

    for ann in annotation.name.split():
        ann_file = get_annotation_path(source_file, ann, annotation.root)
        count += len(list(read_annotation_file(ann_file)))

    return count


def read_annotation_spans(
    source_file: str, annotation: BaseAnnotation, decimals: bool = False, with_annotation_name: bool = False
) -> Iterator[tuple]:
    """Iterate over the spans of an annotation.

    Args:
        source_file: Source filename.
        annotation: Annotation object.
        decimals: Whether to return spans as decimals or not. Defaults to False.
        with_annotation_name: Whether to yield the annotation name along with the value.

    Yields:
        The annotation spans. If with_annotation_name is True, yields a tuple with the value and the annotation name.
    """
    # Strip any annotation attributes
    for span in read_annotation(source_file, annotation, with_annotation_name, spans=True):
        if not decimals:
            yield tuple(v[0] for v in span)
        else:
            yield span


def read_annotation(
    source_file: str, annotation: BaseAnnotation, with_annotation_name: bool = False, spans: bool = False
) -> Iterator:
    """Yield each line from an annotation file.

    Args:
        source_file: Source filename.
        annotation: Annotation object.
        with_annotation_name: Whether to yield the annotation name along with the value.
        spans: Whether to read annotation spans or regular values.

    Yields:
        The annotation values. If with_annotation_name is True, yields a tuple with the value and the annotation name.
    """
    annotations = [split_annotation(ann)[0] for ann in annotation.name.split()] if spans else annotation.name.split()
    root = annotation.root
    if len(annotations) == 1:
        # Handle single annotation
        yield from _read_single_annotation(source_file, annotations[0], with_annotation_name, spans, root)
    else:
        # Handle multiple annotations used as one

        # Make sure we don't have multiple attributes on the same annotation
        assert len(annotations) == len({split_annotation(ann)[0] for ann in annotations}), (
            "Reading multiple attributes on the same annotation is not allowed."
        )

        # Get iterators for all annotations
        all_annotations = {
            split_annotation(ann)[0]: _read_single_annotation(source_file, ann, with_annotation_name, spans, root)
            for ann in annotations
        }

        # We need to read the annotation spans to be able to interleave the values in the correct order
        for _, ann in heapq.merge(
            *[
                _read_single_annotation(
                    source_file, split_annotation(ann)[0], with_annotation_name=True, spans=spans, root=root
                )
                for ann in annotations
            ]
        ):
            yield next(all_annotations[ann])


def read_annotation_attributes(
    source_file: str, annotations: list[BaseAnnotation] | tuple[BaseAnnotation, ...], with_annotation_name: bool = False
) -> Iterator[tuple]:
    """Yield tuples of multiple attributes on the same annotation.

    Args:
        source_file: Source filename.
        annotations: List of annotation objects.
        with_annotation_name: Whether to yield the annotation name along with the value.

    Returns:
        An iterator of tuples with the values of the attributes.
    """
    assert isinstance(annotations, (tuple, list)), "'annotations' argument must be tuple or list"
    assert len({split_annotation(annotation)[0] for annotation in annotations}) == 1, (
        "All attributes need to be for the same annotation"
    )
    return zip(
        *[read_annotation(source_file, annotation, with_annotation_name) for annotation in annotations], strict=True
    )


def _read_single_annotation(
    source_file: str, annotation: str, with_annotation_name: bool, spans: bool, root: Path | None = None
) -> Iterator[Any]:
    """Read a single annotation file and yield each value, or the underlying text if the annotation has no attribute.

    Args:
        source_file: Source filename.
        annotation: Annotation name.
        with_annotation_name: Whether to yield the annotation name along with the value.
        spans: Whether to read annotation spans or regular values.
        root: Root path.

    Yields:
        The annotation values. If with_annotation_name is True, yields a tuple with the value and the annotation name.
    """
    ann_file = get_annotation_path(source_file, annotation, root)

    span_text = not spans and not split_annotation(annotation)[1]
    text_data = read_data(source_file, TEXT_FILE) if span_text else None
    ctr = 0
    for value in read_annotation_file(ann_file):
        if span_text:
            yield (
                text_data[value[0][0] : value[1][0]]
                if not with_annotation_name
                else (text_data[value[0][0] : value[1][0]], annotation)
            )
        else:
            yield value if not with_annotation_name else (value, annotation)
        ctr += 1
    logger.debug("Read %d items: %s%s%s", ctr, source_file, "/" if source_file else "", annotation)


def write_data(source_file: str | None, name: BaseAnnotation | str, value: Any) -> None:
    """Write arbitrary data to a file in the workdir directory.

    Args:
        source_file: Source filename.
        name: Annotation object or name.
        value: Data to write.
    """
    file_path = get_annotation_path(source_file, name, data=True)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    write_annotation_file(file_path, value, is_data=True)

    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    if logger.isEnabledFor(logging.INFO):
        logger.info(
            "Wrote %d bytes: %s%s%s",
            file_path.stat().st_size,
            source_file or "",
            "/" if source_file else "",
            name.name if isinstance(name, BaseAnnotation) else name,
        )


def read_data(source_file: str | None, name: BaseAnnotation | str) -> Any:
    """Read arbitrary data from a file in the workdir directory.

    Args:
        source_file: Source filename.
        name: Annotation object or name.

    Returns:
        The data read from the annotation.
    """
    file_path = get_annotation_path(source_file, name, data=True)
    data = next(read_annotation_file(file_path, is_data=True))

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Read %d bytes: %s%s%s",
            file_path.stat().st_size,
            source_file or "",
            "/" if source_file else "",
            name.name if isinstance(name, BaseAnnotation) else name,
        )
    return data


def split_annotation(annotation: BaseAnnotation | str) -> tuple[str, str]:
    """Split annotation into annotation name and attribute.

    Args:
        annotation: Annotation object or name.

    Returns:
        Tuple with annotation name and attribute.
    """
    if isinstance(annotation, BaseAnnotation):
        annotation = annotation.name
    elem, _, attr = annotation.partition(ELEM_ATTR_DELIM)
    return elem, attr


def join_annotation(name: str, attribute: str | None) -> str:
    """Join annotation name and attribute.

    Args:
        name: Annotation name.
        attribute: Annotation attribute.

    Returns:
        Annotation name joined with attribute.
    """
    return ELEM_ATTR_DELIM.join((name, attribute)) if attribute else name


def get_annotation_path(
    source_file: str | None, annotation: BaseAnnotation | str, root: Path | None = None, data: bool = False
) -> Path:
    """Construct a path to an annotation file given a source filename and annotation.

    Args:
        source_file: Source filename.
        annotation: Annotation object or name.
        root: Root path.
        data: Whether the annotation is of the type data or not.

    Returns:
        The path to the annotation file.
    """
    chunk = ""
    if source_file:
        source_file, _, chunk = source_file.partition(DOC_CHUNK_DELIM)
    elem, attr = split_annotation(annotation)

    if data:
        path = paths.work_dir / source_file / chunk / elem if source_file else paths.work_dir / elem
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
    """Write annotation data to a file.

    Args:
        file_path: Path to the file to write.
        value: Data to write.
        is_data: Whether the value is of the type data.
    """
    chunk_size = 1000
    opener = _compressed_open.get(compression, open)
    with opener(file_path, mode="wb") as f:
        if is_data:
            pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            for i in range(0, len(value), chunk_size):
                pickle.dump(value[i : i + chunk_size], f, protocol=pickle.HIGHEST_PROTOCOL)


def read_annotation_file(file_path: Path, is_data: bool = False) -> Iterator:
    """Return an iterator for reading an annotation file.

    Args:
        file_path: Path to the file to read.
        is_data: Whether the value is of the type data.

    Yields:
        The annotation values.

    Raises:
        SparvErrorMessage: If the file is not in the correct format.
    """
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
                "use 'sparv clean' to start over with a clean workdir."
            ) from None
