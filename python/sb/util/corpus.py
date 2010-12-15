# -*- coding: utf-8 -*-

import os.path

import log
import system
from constants import *

######################################################################
# Annotations

ANNOTATION_DELIM = " "

def annotation_exists(file):
    """Checks if an annotation file exists."""
    return os.path.exists(file)

def write_annotation(file, annotation, encode=None):
    """Writes an annotation to a file. The file is overwritten if it exists.
    The annotation can be a dictionary, or a sequence of (key,value) pairs.
    If specified, encode should be a function from values to unicode strings.
    """
    if isinstance(annotation, dict):
        annotation = annotation.iteritems()
    system.make_directory(os.path.dirname(file))
    with open(file, "w") as DB:
        ctr = 0
        for key, value in annotation:
            if value is None: value = ""
            if encode: value = encode(value)
            value = value.replace("\\", r"\\").replace("\n", r"\n")
            print >>DB, (key + ANNOTATION_DELIM + value).encode(UTF8)
            ctr += 1
    log.info("Wrote %d items: %s", ctr, file)

def read_annotation(file, decode=None):
    """Reads an annotation file into a dictionary.
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
            key, _, value = line.rstrip("\n\r").decode(UTF8).partition(ANNOTATION_DELIM)
            value = value.replace(r"\n", "\n").replace(r"\\", "\\")
            if decode: value = decode(value)
            yield key, value
            ctr += 1
    log.info("Read %d items: %s", ctr, file)

######################################################################
# Corpus text

ANCHOR_DELIM = "#"

def read_corpus_text(corpusfile):
    """Reads the anchored text of a corpus.
    Returns a tuple (text, anchor2pos, pos2anchor), where:
     - text is a unicode string,
     - anchor2pos is a dict from anchors to positions,
     - pos2anchor is a dict from positions to anchors.
    """
    with open(corpusfile, "r") as F:
        text = F.read().decode(UTF8)
    textbuffer = []
    position = 0
    anchor2pos = {}
    pos2anchor = {}
    end = -1
    while True: # The only way to exit this loop is when ANCHOR_DELIM is not found anymore
        start = text.find(ANCHOR_DELIM, end+1)
        if start < 0:
            textbuffer.append(text[end+1:len(text)])
            break
        textbuffer.append(text[end+1:start])
        position += start - end - 1
        end = text.find(ANCHOR_DELIM, start+1)
        if end < 0:
            raise IOError("Mismatched anchor delimiters in corpus file: %s" % ANCHOR_DELIM)
        elif end == start+1:
            textbuffer.append(ANCHOR_DELIM)
            position += 1
        else:
            anchor = text[start+1:end]
            anchor2pos[anchor] = position
            pos2anchor[position] = anchor
    text = "".join(textbuffer)
    log.info("Read %d chars, %d anchors: %s", len(text), len(anchor2pos), corpusfile)
    return text, anchor2pos, pos2anchor

def write_corpus_text(corpusfile, text, pos2anchor):
    """Writes anchored text to the designated file of a corpus.
    text is a unicode string, and pos2anchor is a dict from text
    positions to anchors.
    """
    with open(corpusfile, "w") as F:
        pos = 0
        for nextpos, anchor in sorted(pos2anchor.items()):
            out = (text[pos:nextpos].replace(ANCHOR_DELIM, ANCHOR_DELIM+ANCHOR_DELIM) +
                   ANCHOR_DELIM + anchor + ANCHOR_DELIM)
            F.write(out.encode(UTF8))
            pos = nextpos
        out = text[pos:len(text)].replace(ANCHOR_DELIM, ANCHOR_DELIM+ANCHOR_DELIM)
        F.write(out.encode(UTF8))
    log.info("Wrote %d chars, %d anchors: %s", len(text), len(pos2anchor), corpusfile)

