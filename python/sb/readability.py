# -*- coding: utf-8 -*-

"""
Readability measures (läsbarhetsmått).
"""

import util
import sb.cwb as cwb
from math import log


def actual_words(cols, skip_pos):
    """
    Removes words with punctuation and delimiter POS (provided by skip_pos).

    >>> ' '.join(actual_words(
    ...     [('Hej', 'IN'),
    ...      (',', 'MID'),
    ...      ('vad', 'HP'),
    ...      ('heter', 'VB'),
    ...      ('du', 'PN'),
    ...      ('?', 'MAD')], skip_pos="MAD MID PAD"))
    'Hej vad heter du'
    """
    skip_pos = skip_pos.split()
    for word, pos in cols:
        if pos not in skip_pos:
            yield word


def lix_annot(order, text, parent_text, sentence, parent_sentence, words, pos, out, skip_pos="MAD MID PAD", fmt="%.2f"):
    structs = [(text, parent_text), (sentence, parent_sentence)]
    columns = [words, pos]
    texts = cwb.vrt_iterate(*cwb.tokens_and_vrt(order, structs, columns),
                            trail=[0, 1])

    util.write_annotation(out, (
        (span, str(lix((actual_words(cols, skip_pos) for _, cols in sentences), fmt)))
        for (_, span), sentences in texts
    ))


def lix(sentences, fmt):
    """
    Calculates LIX, assuming that all tokens are actual words: not punctuation
    nor delimiters.

    >>> print(lix(4*["a bc def ghij klmno pqrstu vxyzåäö".split()], "%.2f"))
    21.29
    """
    s = 0.0
    w = 0.0
    l = 0.0
    for words in sentences:
        s += 1
        for word in words:
            w += 1
            l += int(len(word) > 6)
    lix = w / s + 100 * l / w
    return fmt % lix


def ovix_annot(order, text, parent_text, words, pos, out, skip_pos="MAD MID PAD", fmt="%.2f"):
    structs = [(text, parent_text)]
    columns = [words, pos]
    texts = cwb.vrt_iterate(*cwb.tokens_and_vrt(order, structs, columns))
    util.write_annotation(out, (
        (span, str(ovix(actual_words(cols, skip_pos), fmt)))
        for (_, span), cols in texts
    ))


def ovix(words, fmt):
    """
    Calculates OVIX, assuming that all tokens are actual words: not punctuation
    nor delimiters.

    Words are compared ignoring case.

    >>> for i in range(5):
    ...     print(ovix((i*"a bc def ghij klmno pqrstu vxyzåäö ").split(), "%.2f"))
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
        ovix = log(w) / log(2 - log(uw) / log(w))
        return fmt % ovix


def nominal_ratio_annot(order, text, parent_text, pos, out, noun_pos="NN PP PC", verb_pos="PN AB VB", fmt="%.2f"):
    structs = [(text, parent_text)]
    columns = [pos]
    texts = cwb.vrt_iterate(*cwb.tokens_and_vrt(order, structs, columns))
    util.write_annotation(out, (
        (span, str(nominal_ratio([col[0] for col in cols], noun_pos, verb_pos, fmt)))
        for (_, span), cols in texts
    ))


def nominal_ratio(pos, noun_pos, verb_pos, fmt):
    """
    Calculates nominal ratio (nominalkvot).

    >>> nominal_ratio('NN JJ'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB", fmt="%.1f")
    'inf'
    >>> nominal_ratio('NN NN VB'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB", fmt="%.1f")
    '2.0'
    >>> nominal_ratio('NN PP PC PN AB VB MAD MID'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB", fmt="%.1f")
    '1.0'
    >>> nominal_ratio('NN AB VB PP PN PN MAD'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB", fmt="%.1f")
    '0.5'
    >>> nominal_ratio('RG VB'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB", fmt="%.1f")
    '0.0'
    """
    # nouns prepositions participles
    nouns = sum(1 for p in pos if p in noun_pos.split())
    # pronouns adverbs verbs
    verbs = sum(1 for p in pos if p in verb_pos.split())
    try:
        nk = float(nouns) / float(verbs)
        return fmt % nk
    except ZeroDivisionError:
        return 'inf'


if __name__ == '__main__':
    util.run.main(lix=lix_annot,
                  ovix=ovix_annot,
                  nominal_ratio=nominal_ratio_annot)
