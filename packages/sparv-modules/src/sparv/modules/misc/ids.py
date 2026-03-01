"""Generate unique IDs for corpus files."""

import math
import random
from binascii import hexlify
from collections.abc import Collection
from pathlib import Path

from sparv.api import (
    AllSourceFilenames,
    Annotation,
    AnnotationData,
    Output,
    OutputDataAllSourceFiles,
    SourceFilename,
    Wildcard,
    annotator,
    get_logger,
)

logger = get_logger(__name__)
DEFAULT_ID_LENGTH = 10


@annotator("Give every source file a unique ID")
def file_id(
    out: OutputDataAllSourceFiles = OutputDataAllSourceFiles(
        "misc.fileid", cls="fileid", description="Unique IDs for every source file"
    ),
    source_files: AllSourceFilenames | None = AllSourceFilenames(),
    source_files_list: str | None = None,
    prefix: str = "",
    add: bool = False,
) -> None:
    """Create unique IDs for every source file in a list, using the source filenames as seed.

    Args:
        out: Output annotation for the unique IDs.
        source_files: List of source files to process.
        source_files_list: Path to a file containing a list of source files to process.
        prefix: Prefix for the unique IDs.
        add: If `True`, existing IDs will not be overwritten.
    """
    assert source_files or source_files_list, "source_files or source_files_list must be specified"

    if source_files_list:
        with Path(source_files_list).open(encoding="utf-8") as f:
            source_files = f.read().strip().splitlines()

    source_files = sorted(source_files)
    logger.progress(total=len(source_files))

    numfiles = len(source_files) * 2
    used_ids = set()
    files_with_ids = set()

    if add:
        for file in source_files:
            if outdata := out(file).exists():
                used_ids.add(outdata.read())
                files_with_ids.add(file)

    id_length = _get_id_length(numfiles)
    for file in source_files:
        if add and file in files_with_ids:
            continue
        _reset_id(file)
        new_id = _make_id(id_length, prefix, used_ids)
        used_ids.add(new_id)
        out(file).write(new_id)
        logger.progress()


@annotator("Unique IDs for {annotation}", wildcards=[Wildcard("annotation", Wildcard.ANNOTATION)])
def ids(
    source_file: SourceFilename = SourceFilename(),
    annotation: Annotation = Annotation("{annotation}"),
    out: Output = Output("{annotation}:misc.id", description="Unique ID for {annotation}"),
    fileid: AnnotationData = AnnotationData("<fileid>"),
    prefix: str = "",
) -> None:
    """Create unique IDs for every span of an existing annotation.

    To make the IDs unique across all files, the IDs are prefixed with the file ID of the source file.

    Args:
        source_file: Source filename.
        annotation: Annotation to create unique IDs for.
        out: Output annotation for the unique IDs.
        fileid: Annotation containing the unique IDs for the source files.
        prefix: Prefix for the unique IDs.
    """
    logger.progress()
    fileid = fileid.read()
    prefix += fileid

    ann = list(annotation.read())
    out_annotation = []
    used_ids: set[str] = set()
    logger.progress(total=len(ann) + 1)
    id_length = _get_id_length(len(ann))
    # Use source filename and annotation name as seed for the IDs
    _reset_id(f"{source_file}/{annotation}")
    for _ in ann:
        new_id = _make_id(id_length, prefix, used_ids)
        out_annotation.append(new_id)
        used_ids.add(new_id)
        logger.progress()
    out.write(out_annotation)
    logger.progress()


def _get_id_length(max_ids: int | None = None) -> int:
    """Get the length of the ID based on the maximum number of IDs.

    Args:
        max_ids: Maximum number of IDs to generate. If provided, this will determine the length of the IDs.

    Returns:
        Length of the IDs.
    """
    if max_ids:
        return int(math.log(max_ids, 16) + 1.5)
    return DEFAULT_ID_LENGTH


def _reset_id(seed: str) -> None:
    """Reset the random seed for identifiers.

    Args:
        seed: Seed for the random number generator.
        max_ids: Maximum number of IDs to generate. If provided, this will determine the length of the IDs.
    """
    seed_int = int(hexlify(seed.encode()), 16)  # For random.seed to work consistently regardless of platform
    random.seed(seed_int)


def _make_id(id_length: int, prefix: str, existing_ids: Collection[str] = ()) -> str:
    """Create a unique identifier with a given prefix.

    Args:
        id_length: Length of the ID.
        prefix: Prefix for the ID.
        existing_ids: Existing IDs to check against.

    Returns:
        A unique identifier.
    """
    while True:
        n = random.getrandbits(id_length * 4)
        ident = prefix + hex(n)[2:].zfill(id_length)  # noqa: FURB116, for performance
        if ident not in existing_ids:
            return ident
