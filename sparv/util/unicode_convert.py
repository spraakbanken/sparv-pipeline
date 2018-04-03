# -*- coding: utf-8 -*-

"""
Safe unicode conversions
"""


def utf8(u):
    return str(u).encode("utf8")


def latin1(u):
    return encode(u, "latin1")


def latin9(u):
    return encode(u, "latin9")


def cp1252(u):
    return encode(u, "cp1252")


def ascii(u):
    return encode(u, "ascii")


def latin1plus(u):
    """CP-1252 encoding, but where letters are replaced by Latin-1 letters:
     * Š->S, š->s, Ž->Z, ž->z, Œ->OE, œ->oe, Ÿ->Y, ƒ->f
     * CP-1252 symbols are not replaced"""
    replacements = u"ŠS šs ŽZ žz ŒOE œoe ŸY ƒf"
    replacements = dict((ord(r[0]), r[1:]) for r in replacements.split())
    u = str(u).translate(replacements)
    return cp1252(u)


def encode(u, encoding):
    if encoding == "latin1+":
        return latin1plus(u)
    u = str(u)
    try:
        return u.encode(encoding)
    except UnicodeEncodeError:
        return "".join(_encode_unichar(c, encoding) for c in u)


def _encode_unichar(c, encoding):
    try:
        return c.encode(encoding)
    except UnicodeEncodeError:
        return remove_diacritics(c).encode(encoding, "replace")


######################################################################
# Private functions

import unicodedata as _U


def remove_diacritics(u):
    nfkc = _U.normalize("NFKC", u)
    return u"".join(_remove_diacritics_unichar(c) for c in nfkc)


def _remove_diacritics_unichar(c):
    try:
        return _DIACRITIC_REPLACEMENTS[c]
    except KeyError:
        return _U.normalize("NFD", c)[0]

_DIACRITIC_REPLACEMENTS = {
    u"å": u"å",
    u"ä": u"ä",
    u"ö": u"ö",
    u"ü": u"ü",
    u"Å": u"Å",
    u"Ä": u"Ä",
    u"Ö": u"Ö",
    u"Ü": u"Ü",
    u"ß": u"ss",
    u"ƒ": u"f",
    u"Æ": u"AE",  # Ä ?
    u"æ": u"ae",  # ä ?
    u"Œ": u"OE",  # Ö ?
    u"œ": u"oe",  # ö ?
    u"Ø": u"Ö",
    u"ø": u"ö",
    u"Ð": u"DH",
    u"ð": u"dh",
    u"Þ": u"TH",
    u"þ": u"th",
    u"©": u"(C)",
    u"®": u"(R)",
    u"…": u"...",
    u"ˆ": u"^",
    u"‹": u"<",
    u"«": u"<<",
    u"»": u">>",
    u"¼": u"1/4",
    u"½": u"1/2",
    u"¾": u"3/4",
    u"¦": u"|",
    u"\u2044": u"/",
}
