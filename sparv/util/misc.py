"""Misc util functions."""

import random
import math
from binascii import hexlify

_ANCHORLEN = 10
_EDGE_SEP = ":"
_SPAN_SEP = "-"


# Identifiers (e.g. anchors):

def resetIdent(seed, maxidents=None):
    if maxidents:
        global _ANCHORLEN
        _ANCHORLEN = int(math.log(maxidents, 16) + 1.5)
    seed = int(hexlify(seed.encode()), 16)  # For random.seed to work consistently regardless of platform
    random.seed(seed)


def mkIdent(prefix, identifiers=()):
    """Create a unique identifier with a given prefix.

    Note: the ident is NOT added to the collection of existing identifiers.
    """
    prefix = prefix.replace(_EDGE_SEP, "").replace(_SPAN_SEP, "")
    while True:
        n = random.getrandbits(_ANCHORLEN * 4)
        ident = prefix + hex(n)[2:].zfill(_ANCHORLEN)
        if ident not in identifiers:
            return ident


# Edges:

def mkEdge(name, *spans):
    """Create an edge from a name and a sequence of anchor spans.

    Return a string of the form 'name:anchorstart-anchorend:anchorstart-anchorend:...'
    """
    spans = [_safe_join(_SPAN_SEP, span) for span in spans]
    return _safe_join(_EDGE_SEP, [name] + spans)


def edgeName(edge):
    # These are equivalent, but .partition is faster:
    # return edge.split(_EDGE_SEP, 1)[0]
    return edge.partition(_EDGE_SEP)[0]


def edgeStart(edge):
    # These are equivalent, but .partition is faster:
    # return edge.split(_EDGE_SEP, 1)[1].split(_SPAN_SEP, 1)[0]
    return edge.partition(_EDGE_SEP)[2].partition(_SPAN_SEP)[0]


def edgeEnd(edge):
    # These are equivalent, but .rpartition is faster:
    # return edge.rsplit(_SPAN_SEP, 1)[1]
    return edge.rpartition(_SPAN_SEP)[2]


def _safe_join(sep, elems):
    """Join a list of strings (elems), using (sep) as separator.

    All occurrences of (sep) in (elems) are removed.
    """
    return sep.join(elem.replace(sep, "") for elem in elems)


def strtobool(value):
    """Convert possible string to boolean."""
    if isinstance(value, str):
        value = (value.lower() == "true")
    return value


def split(value):
    """If 'value' is a string, split and return a list, otherwise return as is."""
    if isinstance(value, str):
        value = value.split()
    return value


def single_true(iterable):
    """Return True if one and only one element in iterable evaluates to True."""
    i = iter(iterable)
    return any(i) and not any(i)


def cwbset(values, delimiter="|", affix="|", sort=False, maxlength=4095, encoding="UTF-8"):
    """Take an iterable object and return a set in the format used by Corpus Workbench."""
    values = list(values)
    if sort:
        values.sort()
    if maxlength:
        length = 1  # Including the last affix
        for i, value in enumerate(values):
            length += len(value.encode(encoding)) + 1
            if length > maxlength:
                values = values[:i]
                break
    return affix if not values else affix + delimiter.join(values) + affix


def truncateset(string, maxlength=4095, delimiter="|", affix="|", encoding="UTF-8"):
    """Truncate a Corpus Workbench set to a maximum length."""
    if len(string) <= maxlength or string == "|":
        return string
    else:
        length = 1  # Including the last affix
        values = string[1:-1].split("|")
        for i, value in enumerate(values):
            length += len(value.encode(encoding)) + 1
            if length > maxlength:
                return cwbset(values[:i], delimiter, affix)
