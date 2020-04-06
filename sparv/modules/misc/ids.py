"""Generate unique IDs for corpus files."""
import math
import random
from binascii import hexlify

import sparv.util as util
from sparv import annotator
from sparv.util.classes import *

_ID_LENGTH = 10


@annotator("Give every document a unique ID.")
def doc_id(out: str = Output("misc.docid", cls="docid", data=True),
           docs: Optional[list] = AllDocuments,
           doclist: Optional[str] = None,
           prefix: str = "",
           add: bool = False):
    """Create unique IDs for every document in a list, using the document names as seed.
    The resulting IDs are written to the annotation specified by 'out'.
    If 'add' is True, existing IDs will not be overwritten."""

    assert docs or doclist, "docs or doclist must be specified"
    add = util.strtobool(add)

    if doclist:
        with open(doclist, "r") as f:
            docs = f.read().strip()

    docs = util.split(docs)
    docs.sort()

    numdocs = len(docs) * 2
    used_ids = set()
    docs_with_ids = set()

    if add:
        for doc in docs:
            if util.data_exists(doc, out):
                used_ids.add(util.read_data(doc, out))
                docs_with_ids.add(doc)

    for doc in docs:
        if add and doc in docs_with_ids:
            print("skipping", doc)
            continue
        _reset_id(doc, numdocs)
        new_id = _make_id(prefix, used_ids)
        used_ids.add(new_id)
        util.write_data(doc, out, new_id)


@annotator("Unique IDs for annotations.")
def ids(doc: str = Document,
        annotation: str = Annotation("{annotation}"),
        out: str = Output("{annotation}:misc.id", description="Unique ID for {annotation}"),
        docid: str = Annotation("<docid>", data=True),
        prefix: str = ""):
    """Create unique IDs for every span of an existing annotation."""
    docid = util.read_data(doc, docid)
    prefix = prefix + docid

    ann = list(util.read_annotation(doc, annotation))
    out_annotation = []
    # Use doc name and annotation name as seed for the IDs
    _reset_id("{}/{}".format(doc, annotation), len(ann))
    for _ in ann:
        new_id = _make_id(prefix, out_annotation)
        out_annotation.append(new_id)
    util.write_annotation(doc, out, out_annotation)


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


if __name__ == "__main__":
    util.run.main(doc_id=doc_id,
                  id=ids)
