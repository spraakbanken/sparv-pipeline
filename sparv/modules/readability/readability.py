"""Calculate readability measures (läsbarhetsmått)."""

from math import log

import sparv.util as util
from sparv import Annotation, Document, Output, annotator


@annotator("Annotate text chunks with LIX values")
def lix(doc: str = Document,
        text: str = Annotation("<text>"),
        sentence: str = Annotation("<sentence>"),
        word: str = Annotation("<token:word>"),
        pos: str = Annotation("<token:pos>"),
        out: str = Output("<text>:readability.lix", description="LIX values for text chunks"),
        skip_pos: list = ["MAD", "MID", "PAD"],
        fmt: str = "%.2f"):
    """Create LIX annotation for text."""
    # Read annotation files and get parent_children relations
    text_children, _orphans = util.get_children(doc, text, sentence)
    word_pos = list(util.read_annotation_attributes(doc, (word, pos)))
    sentence_children, _orphans = util.get_children(doc, sentence, word)
    sentence_children = list(sentence_children)

    # Calculate LIX for every text element
    lix_annotation = []
    for text in text_children:
        in_sentences = []
        for sentence_index in text:
            s = sentence_children[sentence_index]
            in_sentences.append(list(actual_words([word_pos[token_index] for token_index in s], skip_pos)))
        lix_annotation.append(fmt % lix_calc(in_sentences))

    util.write_annotation(doc, out, lix_annotation)


def lix_calc(sentences):
    """
    Calculate LIX, assuming that all tokens are actual words, not punctuation or delimiters.

    >>> print("%.2f" % lix_calc(4*["a bc def ghij klmno pqrstu vxyzåäö".split()]))
    21.29
    """
    sentence_counter = 0.0
    word_counter = 0.0
    length_counter = 0.0
    for words in sentences:
        sentence_counter += 1
        for word in words:
            word_counter += 1
            length_counter += int(len(word) > 6)
    if word_counter == 0 and sentence_counter == 0:
        return float('NaN')
    elif word_counter == 0 or sentence_counter == 0:
        return float('inf')
    else:
        return word_counter / sentence_counter + 100 * length_counter / word_counter


@annotator("Annotate text chunks with OVIX values")
def ovix(doc: str = Document,
         text: str = Annotation("<text>"),
         word: str = Annotation("<token:word>"),
         pos: str = Annotation("<token:pos>"),
         out: str = Output("<text>:readability.ovix", description="OVIX values for text chunks"),
         skip_pos: list = ["MAD", "MID", "PAD"],
         fmt: str = "%.2f"):
    """Create OVIX annotation for text."""
    text_children, _orphans = util.get_children(doc, text, word)
    word_pos = list(util.read_annotation_attributes(doc, (word, pos)))

    # Calculate OVIX for every text element
    ovix_annotation = []
    for text in text_children:
        in_words = list(actual_words([word_pos[token_index] for token_index in text], skip_pos))
        ovix_annotation.append(fmt % ovix_calc(in_words))

    util.write_annotation(doc, out, ovix_annotation)


def ovix_calc(words):
    """
    Calculate OVIX, assuming that all tokens are actual words, not punctuation or delimiters.

    Words are compared ignoring case.

    >>> for i in range(5):
    ...     print("%.2f" % ovix_calc((i*"a bc def ghij klmno pqrstu vxyzåäö ").split()))
    nan
    inf
    11.32
    9.88
    9.58
    """
    seen = set()
    w = 0.0
    uw = 0.0
    for word in words:
        word = word.lower()
        w += 1
        if word not in seen:
            seen.add(word)
            uw += 1
    if w == 0:
        return float('NaN')
    elif uw == w:
        return float('inf')
    else:
        return log(w) / log(2 - log(uw) / log(w))


@annotator("Annotate text chunks with nominal ratios")
def nominal_ratio(doc: str = Document,
                  text: str = Annotation("<text>"),
                  pos: str = Annotation("<token:pos>"),
                  out: str = Output("<text>:readability.nk", description="Nominal ratios for text chunks"),
                  noun_pos: list = ["NN", "PP", "PC"],
                  verb_pos: list = ["PN", "AB", "VB"],
                  fmt: str = "%.2f"):
    """Create nominal ratio annotation for text."""
    text_children, _orphans = util.get_children(doc, text, pos)
    pos_annotation = list(util.read_annotation(doc, pos))

    # Calculate OVIX for every text element
    nk_annotation = []
    for text in text_children:
        in_pos = [pos_annotation[token_index] for token_index in text]
        nk_annotation.append(fmt % nominal_ratio_calc(in_pos, noun_pos, verb_pos))
    util.write_annotation(doc, out, nk_annotation)


def nominal_ratio_calc(pos, noun_pos, verb_pos):
    """
    Calculate nominal ratio (nominalkvot).

    >>> "%.1f" % nominal_ratio_calc('NN JJ'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    'inf'
    >>> "%.1f" % nominal_ratio_calc('NN NN VB'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    '2.0'
    >>> "%.1f" % nominal_ratio_calc('NN PP PC PN AB VB MAD MID'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    '1.0'
    >>> "%.1f" % nominal_ratio_calc('NN AB VB PP PN PN MAD'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    '0.5'
    >>> "%.1f" % nominal_ratio_calc('RG VB'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    '0.0'
    """
    # nouns prepositions participles
    nouns = sum(1 for p in pos if p in util.split(noun_pos))
    # pronouns adverbs verbs
    verbs = sum(1 for p in pos if p in util.split(verb_pos))
    try:
        nk = float(nouns) / float(verbs)
        return nk
    except ZeroDivisionError:
        return float('inf')


def actual_words(cols, skip_pos):
    """
    Remove words with punctuation and delimiter POS (provided by skip_pos).

    >>> ' '.join(actual_words(
    ...     [('Hej', 'IN'),
    ...      (',', 'MID'),
    ...      ('vad', 'HP'),
    ...      ('heter', 'VB'),
    ...      ('du', 'PN'),
    ...      ('?', 'MAD')], skip_pos="MAD MID PAD"))
    'Hej vad heter du'
    """
    skip_pos = util.split(skip_pos)
    for word, pos in cols:
        if pos not in skip_pos:
            yield word
