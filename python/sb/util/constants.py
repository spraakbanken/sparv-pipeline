# -*- coding: utf-8 -*-

"""
Common constants and constructors
"""

# Identifiers (e.g. anchors):

import random
import math

def resetIdent(seed, maxidents=None):
    if maxidents:
        global _ANCHORLEN
        _ANCHORLEN = int(math.log(maxidents, 16) + 1.5)
    random.seed(seed)

_ANCHORLEN = 10

def mkIdent(prefix, identifiers=()):
    """Create a unique identifier with a given prefix.
    Note: the ident is NOT added to the collection of existing identifiers.
    """
    prefix = prefix.replace(_EDGE_SEP, "").replace(_SPAN_SEP, "")
    while True:
        ident = prefix
        n = random.getrandbits(_ANCHORLEN * 4)
        ident = prefix + hex(n)[2:-1].zfill(_ANCHORLEN)
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
    return sep.join(elem.replace(sep,"") for elem in elems)

_EDGE_SEP = ":"
_SPAN_SEP = "-"


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


