# -*- coding: utf-8 -*-

"""
Common constants and constructors
"""

# Identifiers (e.g. anchors):

import random
import math
from binascii import hexlify


def resetIdent(seed, maxidents=None):
    if maxidents:
        global _ANCHORLEN
        _ANCHORLEN = int(math.log(maxidents, 16) + 1.5)
    seed = int(hexlify(seed.encode()), 16)  # For random.seed to work consistently regardless of platform
    random.seed(seed)

_ANCHORLEN = 10


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
    Returns a string of the form 'name:anchorstart-anchorend:anchorstart-anchorend:...'
    """
    spans = [_safe_join(_SPAN_SEP, span) for span in spans]
    return _safe_join(_EDGE_SEP, [name] + spans)


def edgeName(edge):
    # These are equivalent, but .partition is faster:
    # return edge.split(_EDGE_SEP, 1)[0]
    return edge.partition(_EDGE_SEP)[0]


def edgeSpans(edge):
    return [span.split(_SPAN_SEP) for span in edge.split(_EDGE_SEP)[1:]]


def edgeStart(edge):
    # These are equivalent, but .partition is faster:
    # return edgeSpans(edge)[0][0]
    # return edge.split(_EDGE_SEP, 1)[1].split(_SPAN_SEP, 1)[0]
    return edge.partition(_EDGE_SEP)[2].partition(_SPAN_SEP)[0]


def edgeEnd(edge):
    # These are equivalent, but .rpartition is faster:
    # return edgeSpans(edge)[-1][-1]
    # return edge.rsplit(_SPAN_SEP, 1)[1]
    return edge.rpartition(_SPAN_SEP)[2]


def _safe_join(sep, elems):
    """Joins a list of strings (elems), using (sep) as separator.
    All occurrences of (sep) in (elems) are removed.
    """
    return sep.join(elem.replace(sep, "") for elem in elems)

_EDGE_SEP = ":"
_SPAN_SEP = "-"

DELIM = "|"       # Delimiter char to put between ambiguous results
AFFIX = "|"       # Char to put before and after results to mark a set
SCORESEP = ":"    # Char that separates an annotation from a score
COMPSEP = "+"     # Char to separate compound parts


def strtobool(value):
    """Convert possible string to boolean"""
    if isinstance(value, str):
        value = (value.lower() == "true")
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

# Encodings:

UTF8 = 'UTF-8'
LATIN1 = 'ISO-8859-1'

# Corpus languages:

SWE = 'swe'
NLD = 'nld'

# Keys used in the annotations:

PARAGRAPH = 'paragraph'
SENTENCE = 'sentence'
TOKEN = 'token'
LINK = 'link'
MARKUP = 'markup'
METADATA = 'metadata'

N = 'n'
ID = 'id'
EDGE = 'edge'
ELEM = 'elem'
TEXT = 'text'
DIV = 'div'
WORD = 'word'
POS = 'pos'
MSD = 'msd'
STEM = 'stem'
LEMMA = 'lemma'
LEX = 'lex'
PRECISION = 'precision'

COLORS = {
    "default":      "\033[m",
    # Styles
    "bold":         "\033[1m",
    "underline":    "\033[4m",
    "blink":        "\033[5m",
    "reverse":      "\033[7m",
    "concealed":    "\033[8m",
    # Font colors
    "black":        "\033[30m",
    "red":          "\033[31m",
    "green":        "\033[32m",
    "yellow":       "\033[33m",
    "blue":         "\033[34m",
    "magenta":      "\033[35m",
    "cyan":         "\033[36m",
    "white":        "\033[37m",
    # Background colors
    "on_black":     "\033[40m",
    "on_red":       "\033[41m",
    "on_green":     "\033[42m",
    "on_yellow":    "\033[43m",
    "on_blue":      "\033[44m",
    "on_magenta":   "\033[45m",
    "on_cyan":      "\033[46m",
    "on_white":     "\033[47m"
}
