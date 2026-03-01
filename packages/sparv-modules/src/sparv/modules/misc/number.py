"""Annotators for numbering things."""

import random
import re
from binascii import hexlify
from collections import defaultdict

from sparv.api import (
    AllSourceFilenames,
    Annotation,
    AnnotationAllSourceFiles,
    Output,
    OutputCommonData,
    Wildcard,
    annotator,
    get_logger,
)

START_DEFAULT = 1

logger = get_logger(__name__)


@annotator("Number {annotation} by position", wildcards=[Wildcard("annotation", Wildcard.ANNOTATION)])
def number_by_position(
    out: Output = Output("{annotation}:misc.number_position", description="Position of {annotation} within file"),
    chunk: Annotation = Annotation("{annotation}"),
    prefix: str = "",
    zfill: bool = False,
    start: int = START_DEFAULT,
) -> None:
    """Number chunks by their position.

    Args:
        out: Output annotation.
        chunk: Input annotation.
        prefix: Prefix for the output number.
        zfill: Whether to zero-fill the output number.
        start: Starting number for the output.
    """
    spans = list(chunk.read_spans())

    def _order(index: int, _value: tuple) -> tuple:
        """Return the position of the chunk."""
        return spans[index]

    _read_chunks_and_write_new_ordering(out, chunk, _order, prefix, zfill, start)


@annotator("Number {annotation} randomly", wildcards=[Wildcard("annotation", Wildcard.ANNOTATION)])
def number_random(
    out: Output = Output("{annotation}:misc.number_random", description="Random number, unique within file"),
    chunk: Annotation = Annotation("{annotation}"),
    prefix: str = "",
    zfill: bool = False,
    start: int = START_DEFAULT,
) -> None:
    """Number chunks randomly.

    Uses index as random seed.

    Args:
        out: Output annotation.
        chunk: Input annotation.
        prefix: Prefix for the output number.
        zfill: Whether to zero-fill the output number.
        start: Starting number for the output.
    """

    def _order(index: int, _value: tuple) -> float:
        """Return a random number based on the index."""
        random.seed(int(hexlify(str(index).encode()), 16))
        return random.random()

    _read_chunks_and_write_new_ordering(out, chunk, _order, prefix, zfill, start)


@annotator(
    "Number {annotation}, with the order determined by {attribute}",
    wildcards=[Wildcard("annotation", Wildcard.ANNOTATION), Wildcard("attribute", Wildcard.ATTRIBUTE)],
)
def number_by_attribute(
    out: Output = Output("{annotation}:misc.number_by_{attribute}", description="Number determined by {attribute}"),
    chunk: Annotation = Annotation("{annotation}:{attribute}"),
    prefix: str = "",
    zfill: bool = False,
    start: int = START_DEFAULT,
) -> None:
    """Number chunks, with the order determined by an attribute.

    Args:
        out: Output annotation.
        chunk: Input annotation.
        prefix: Prefix for the output number.
        zfill: Whether to zero-fill the output number.
        start: Starting number for the output.
    """

    def _order(_index: int, value: str) -> tuple:
        """Return a tuple for natural sorting, based on the attribute value."""
        return _natural_sorting(value)

    _read_chunks_and_write_new_ordering(out, chunk, _order, prefix, zfill, start)


@annotator(
    "Renumber already numbered {annotation}:{attribute}, in new random order",
    wildcards=[Wildcard("annotation", Wildcard.ANNOTATION), Wildcard("attribute", Wildcard.ATTRIBUTE)],
)
def renumber_by_shuffle(
    out: Output = Output("{annotation}:misc.renumber_by_shuffle_{attribute}", description="New random order"),
    chunk: Annotation = Annotation("{annotation}:{attribute}"),
    prefix: str = "",
    zfill: bool = False,
    start: int = START_DEFAULT,
) -> None:
    """Renumber already numbered chunks, in new random order.

    Retains the connection between parallelly numbered chunks by using the values as random seed.

    Args:
        out: Output annotation.
        chunk: Input annotation.
        prefix: Prefix for the output number.
        zfill: Whether to zero-fill the output number.
        start: Starting number for the output.
    """

    def _order(_index: int, value: str) -> tuple:
        """Return a random number based on the attribute value."""
        random.seed(int(hexlify(value.encode()), 16))
        return random.random(), _natural_sorting(value)

    _read_chunks_and_write_new_ordering(out, chunk, _order, prefix, zfill, start)


@annotator(
    "Number {annotation} by ({parent_annotation}:{parent_attribute} order, {annotation} order)",
    wildcards=[
        Wildcard("annotation", Wildcard.ANNOTATION),
        Wildcard("parent_annotation", Wildcard.ANNOTATION),
        Wildcard("parent_attribute", Wildcard.ATTRIBUTE),
    ],
)
def number_by_parent(
    out: Output = Output(
        "{annotation}:misc.number_by_parent_{parent_annotation}__{parent_attribute}",
        description="Order based on parent order",
    ),
    chunk: Annotation = Annotation("{annotation}"),
    parent_order: Annotation = Annotation("{parent_annotation}:{parent_attribute}"),
    prefix: str = "",
    zfill: bool = False,
    start: int = START_DEFAULT,
) -> None:
    """Number chunks by (parent_order, chunk order).

    Args:
        out: Output annotation.
        chunk: Input annotation.
        parent_order: Parent annotation.
        prefix: Prefix for the output number.
        zfill: Whether to zero-fill the output number.
        start: Starting number for the output.
    """
    parent_children, _orphans = parent_order.get_children(chunk)

    child_order = {
        child_index: (parent_nr, child_index)
        for parent_index, parent_nr in enumerate(parent_order.read())
        for child_index in parent_children[parent_index]
    }

    def _order(index: int, _value: tuple) -> tuple:
        """Return the order based on the parent order and child position."""
        return child_order.get(index)

    _read_chunks_and_write_new_ordering(out, chunk, _order, prefix, zfill, start)


@annotator(
    "Number {annotation} by relative position within {parent}",
    wildcards=[Wildcard("annotation", Wildcard.ANNOTATION), Wildcard("parent", Wildcard.ANNOTATION)],
)
def number_relative(
    out: Output = Output(
        "{annotation}:misc.number_rel_{parent}", description="Relative position of {annotation} within {parent}"
    ),
    parent: Annotation = Annotation("{parent}"),
    child: Annotation = Annotation("{annotation}"),
    prefix: str = "",
    zfill: bool = False,
    start: int = START_DEFAULT,
) -> None:
    """Number chunks by their relative position within a parent.

    Args:
        out: Output annotation.
        parent: Parent annotation.
        child: Child annotation.
        prefix: Prefix for the output number.
        zfill: Whether to zero-fill the output number.
        start: Starting number for the output.
    """
    parent_children, _orphans = parent.get_children(child)
    result = child.create_empty_attribute()

    for p in parent_children:
        for cnr, index in enumerate(p, start):
            result[index] = "{prefix}{nr:0{length}d}".format(
                prefix=prefix, length=len(str(len(p) - 1 + start)) if zfill else 0, nr=cnr
            )
    out.write(result)


@annotator("Annotate tokens with numerical IDs relative to their sentences")
def make_ref(
    out: Output = Output("<token>:misc.ref", cls="token:ref", description="Token IDs relative to their sentences"),
    sentence: Annotation = Annotation("<sentence>"),
    token: Annotation = Annotation("<token>"),
) -> None:
    """Annotate tokens with numerical IDs relative to their sentences.

    Args:
        out: Output annotation.
        sentence: Sentence annotation.
        token: Token annotation.
    """
    number_relative(out, sentence, token)


@annotator(
    "Chunk count file with number of {annotation} chunks in corpus",
    order=1,
    wildcards=[Wildcard("annotation", Wildcard.ANNOTATION)],
)
def count_chunks(
    out: OutputCommonData = OutputCommonData(
        "misc.{annotation}_count", description="Number of {annotation} chunks in corpus"
    ),
    chunk: AnnotationAllSourceFiles = AnnotationAllSourceFiles("{annotation}"),
    files: AllSourceFilenames = AllSourceFilenames(),
) -> None:
    """Count the number of occurrences of 'chunk' in the corpus.

    Args:
        out: Output annotation.
        chunk: Input annotation.
        files: All source filenames.
    """
    # Read 'chunk' annotations and count the number of chunks
    chunk_count = 0
    for file in files:
        try:
            chunk_count += len(chunk(file))
        except FileNotFoundError:
            pass

    if chunk_count == 0:
        logger.info("No %s chunks found in corpus", chunk.name)

    # Write chunk count data
    out.write(str(chunk_count))


@annotator(
    "Create chunk count file for non-existent {annotation} chunks",
    order=2,
    wildcards=[Wildcard("annotation", Wildcard.ANNOTATION)],
)
def count_zero_chunks(
    out: OutputCommonData = OutputCommonData(
        "misc.{annotation}_count", description="The value 0 for corpora without {annotation}"
    ),
    _files: AllSourceFilenames = AllSourceFilenames(),
) -> None:
    """Create chunk count file for non-existent 'annotation' chunks.

    Args:
        out: Output annotation.
        _files: All source filenames.
    """
    logger.info("No %s chunks found in corpus", out.name[5:-6])
    out.write("0")


def _read_chunks_and_write_new_ordering(
    out: Output, chunk: Annotation, order: callable, prefix: str = "", zfill: bool = False, start: int = START_DEFAULT
) -> None:
    """Common function called by other numbering functions.

    The `order` function is called for each chunk to determine the new order. It takes the index and the value of the
    chunk (either spans or attribute values) as arguments and returns a value that determines the new order.

    Args:
        out: Output annotation.
        chunk: Input annotation.
        order: Function to determine the new order of the chunks.
        prefix: Prefix for the output number.
        zfill: Whether to zero-fill the output number.
        start: Starting number for the output.
    """
    new_order = defaultdict(list)

    in_annotation = list(chunk.read() if chunk.has_attribute() else chunk.read_spans())

    for i, val in enumerate(in_annotation):
        sorting_key = order(i, val)
        new_order[sorting_key].append(i)

    out_annotation = chunk.create_empty_attribute()

    nr_digits = len(str(len(new_order) - 1 + start))
    for nr, key in enumerate(sorted(new_order), start):
        for index in new_order[key]:
            out_annotation[index] = "{prefix}{nr:0{length}d}".format(
                prefix=prefix, length=nr_digits if zfill else 0, nr=nr
            )

    out.write(out_annotation)


def _natural_sorting(astr: str) -> tuple:
    """Convert a string into a naturally sortable tuple.

    Args:
        astr: The string to be converted.

    Returns:
        A tuple containing the string split into parts, where each part is either an integer or a string.
    """
    return tuple(int(s) if s.isdigit() else s for s in re.split(r"(\d+)", astr))
