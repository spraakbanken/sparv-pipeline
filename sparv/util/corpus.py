# -*- coding: utf-8 -*-

import os
from . import log
from . import system
from .constants import *

######################################################################
# Annotations

ANNOTATION_DELIM = " "


def annotation_exists(file):
    """Check if an annotation file exists."""
    return os.path.exists(file)


def clear_annotation(file):
    """Remove an annotation file if it exists."""
    if os.path.exists(file):
        os.remove(file)


def write_annotation(file, annotation, transform=None, append=False):
    """Write an annotation to a file. The file is overwritten if it exists.
    The annotation can be a dictionary, or a sequence of (key,value) pairs.
    If specified, transform should be a function from values to unicode strings.
    """
    if isinstance(annotation, dict):
        annotation = iter(annotation.items())
    system.make_directory(os.path.dirname(file))
    mode = "a" if append else "w"
    with open(file, mode) as DB:
        ctr = 0
        for key, value in annotation:
            if value is None:
                value = ""
            if transform:
                value = transform(value)
            # value = value.replace("\\", r"\\").replace("\n", r"\n").replace("\r", "")  # Use if we allow linebreaks in tokens
            value = value.replace("\n", "").replace("\r", "")  # Don't allow linebreaks in tokens
            print((key + ANNOTATION_DELIM + value), file=DB)
            ctr += 1
    # Update file modification time even if nothing was written
    os.utime(file, None)
    log.info("Wrote %d items: %s", ctr, file)


def read_annotation(file, decode=None):
    """Read an annotation file into a dictionary.
    If specified, decode should be a function from unicode strings to values.
    """
    return dict(read_annotation_iteritems(file, decode))


def read_annotation_iterkeys(file):
    """An iterator that yields each key in an annotation file."""
    for key, _value in read_annotation_iteritems(file):
        yield key


def read_annotation_iteritems(file, decode=None):
    """An iterator that yields each (key,value) pair in an annotation file.
    If specified, decode should be a function from unicode strings to values.
    """
    ctr = 0
    with open(file, "r") as DB:
        for line in DB:
            key, _, value = line.rstrip("\n\r").partition(ANNOTATION_DELIM)
            # value = re.sub(r"((?<!\\)(?:\\\\)*)\\n", "\1\n", value).replace(r"\\", "\\")  # Replace literal "\n" with linebreak (only needed if we allow "\n" in tokens)
            if decode:
                value = decode(value)
            yield key, value
            ctr += 1
    log.info("Read %d items: %s", ctr, file)


def chain(annotations, default=None):
    """Create a functional composition of a list of annotations.
    E.g., token.sentence + sentence.id -> token.sentence-id

    >>> from pprint import pprint
    >>> pprint(dict(
    ...   chain([{"w:1": "s:A",
    ...           "w:2": "s:A",
    ...           "w:3": "s:B",
    ...           "w:4": "s:C",
    ...           "w:5": "s:missing"},
    ...          {"s:A": "text:I",
    ...           "s:B": "text:II",
    ...           "s:C": "text:mystery"},
    ...          {"text:I": "The Bible",
    ...           "text:II": "The Samannaphala Sutta"}],
    ...         default="The Principia Discordia")))
    {'w:1': 'The Bible',
     'w:2': 'The Bible',
     'w:3': 'The Samannaphala Sutta',
     'w:4': 'The Principia Discordia',
     'w:5': 'The Principia Discordia'}
    """
    def follow(key):
        for annot in annotations:
            try:
                key = annot[key]
            except KeyError:
                return default
        return key
    return ((key, follow(key)) for key in annotations[0])


def lexicon_to_pickle(lexicon, filename, protocol=-1, verbose=True):
    """Save lexicon as a pickle file."""
    import pickle
    if verbose:
        log.info("Saving lexicon in pickle format")
    with open(filename, "wb") as F:
        pickle.dump(lexicon, F, protocol=protocol)
    if verbose:
        log.info("OK, saved")


def test_annotations(lexicon, testwords):
    """
    For testing the validity of a lexicon.
    Takes a dictionary (lexicon) and a list of test words.
    Prints the value for each test word.
    """
    log.info("Testing annotations...")
    for key in testwords:
        log.output("  %s = %s", key, lexicon.get(key))


class PickledLexicon(object):
    """Read basic pickled lexicon and look up keys."""
    def __init__(self, picklefile, verbose=True):
        import pickle
        if verbose:
            log.info("Reading lexicon: %s", picklefile)
        with open(picklefile, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, key, default=set()):
        """Lookup a key in the lexicon."""
        return self.lexicon.get(key, default)


######################################################################
# Corpus text

ANCHOR_DELIM = "#"


def read_corpus_text(corpusfile):
    """Read the anchored text of a corpus.
    Return a tuple (text, anchor2pos, pos2anchor), where:
     - text is a unicode string,
     - anchor2pos is a dict from anchors to positions,
     - pos2anchor is a dict from positions to anchors.
    """
    with open(corpusfile, "r") as F:
        text = F.read()
    textbuffer = []
    position = 0
    anchor2pos = {}
    pos2anchor = {}
    end = -1
    while True:  # The only way to exit this loop is when ANCHOR_DELIM is not found anymore
        start = text.find(ANCHOR_DELIM, end + 1)
        if start < 0:
            textbuffer.append(text[end + 1:len(text)])
            break
        textbuffer.append(text[end + 1:start])
        position += start - end - 1
        end = text.find(ANCHOR_DELIM, start + 1)
        if end < 0:
            raise IOError("Mismatched anchor delimiters in corpus file: %s" % ANCHOR_DELIM)
        elif end == start + 1:
            textbuffer.append(ANCHOR_DELIM)
            position += 1
        else:
            anchor = text[start + 1:end]
            anchor2pos[anchor] = position
            pos2anchor[position] = anchor
    text = "".join(textbuffer)
    log.info("Read %d chars, %d anchors: %s", len(text), len(anchor2pos), corpusfile)
    return text, anchor2pos, pos2anchor


def write_corpus_text(corpusfile, text, pos2anchor):
    """Write anchored text to the designated file of a corpus.
    text is a unicode string, and pos2anchor is a dict from text
    positions to anchors.
    """
    with open(corpusfile, "w") as F:
        pos = 0
        for nextpos, anchor in sorted(pos2anchor.items()):
            out = (text[pos:nextpos].replace(ANCHOR_DELIM, ANCHOR_DELIM + ANCHOR_DELIM) +
                   ANCHOR_DELIM + anchor + ANCHOR_DELIM)
            F.write(out)
            pos = nextpos
        out = text[pos:len(text)].replace(ANCHOR_DELIM, ANCHOR_DELIM + ANCHOR_DELIM)
        F.write(out)
    log.info("Wrote %d chars, %d anchors: %s", len(text), len(pos2anchor), corpusfile)
