"""Generate unique IDs for corpus files."""

import math
import random
from binascii import hexlify
from typing import Optional

from sparv.api import (AllSourceFilenames, Annotation, AnnotationData, SourceFilename, Output, Wildcard,
                       OutputDataAllSourceFiles, annotator, get_logger)

logger = get_logger(__name__)
_ID_LENGTH = 10


@annotator("Give every source file a unique ID")
def file_id(out: OutputDataAllSourceFiles = OutputDataAllSourceFiles("misc.fileid", cls="fileid"),
            source_files: Optional[AllSourceFilenames] = AllSourceFilenames(),
            source_files_list: Optional[str] = None,
            prefix: str = "",
            add: bool = False):
    """Create unique IDs for every source file in a list, using the source filenames as seed.

    The resulting IDs are written to the annotation specified by 'out'.
    If 'add' is True, existing IDs will not be overwritten.
    """
    assert source_files or source_files_list, "source_files or source_files_list must be specified"

    if source_files_list:
        with open(source_files_list, encoding="utf-8") as f:
            source_files = f.read().strip().splitlines()

    source_files.sort()
    logger.progress(total=len(source_files))

    numfiles = len(source_files) * 2
    used_ids = set()
    files_with_ids = set()

    if add:
        for file in source_files:
            if out.exists(file):
                used_ids.add(out.read(file))
                files_with_ids.add(file)

    for file in source_files:
        if add and file in files_with_ids:
            continue
        _reset_id(file, numfiles)
        new_id = _make_id(prefix, used_ids)
        used_ids.add(new_id)
        out.write(new_id, file)
        logger.progress()


@annotator("Unique IDs for {annotation}", wildcards=[Wildcard("annotation", Wildcard.ANNOTATION)])
def ids(source_file: SourceFilename = SourceFilename(),
        annotation: Annotation = Annotation("{annotation}"),
        out: Output = Output("{annotation}:misc.id", description="Unique ID for {annotation}"),
        fileid: AnnotationData = AnnotationData("<fileid>"),
        prefix: str = ""):
    """Create unique IDs for every span of an existing annotation."""
    logger.progress()
    fileid = fileid.read()
    prefix = prefix + fileid

    ann = list(annotation.read())
    out_annotation = []
    logger.progress(total=len(ann) + 1)
    # Use source filename and annotation name as seed for the IDs
    _reset_id("{}/{}".format(source_file, annotation), len(ann))
    for _ in ann:
        new_id = _make_id(prefix, out_annotation)
        out_annotation.append(new_id)
        logger.progress()
    out.write(out_annotation)
    logger.progress()


def _reset_id(seed, max_ids=None):
    """Reset the random seed for identifiers."""
    if max_ids:
        global _ID_LENGTH
        _ID_LENGTH = int(math.log(max_ids, 16) + 1.5)
    seed = int(hexlify(seed.encode()), 16)  # For random.seed to work consistently regardless of platform
    random.seed(seed)


def _make_id(prefix, existing_ids=()):
    """Create a unique identifier with a given prefix."""
    while True:
        n = random.getrandbits(_ID_LENGTH * 4)
        ident = prefix + hex(n)[2:].zfill(_ID_LENGTH)
        if ident not in existing_ids:
            return ident
