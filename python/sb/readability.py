# -*- coding: utf-8 -*-

"""
Readability measures (läsbarhetsmått).
"""

import util
import sb.cwb as cwb
from math import log
from collections import Counter


def actual_words(cols):
    """
    Removes words with punctuation and delimiter POS.

    >>> ' '.join(actual_words(
    ...     [('Hej', 'IN'),
    ...      (',', 'MID'),
    ...      ('vad', 'HP'),
    ...      ('heter', 'VB'),
    ...      ('du', 'PN'),
    ...      ('?', 'MAD')]))
    'Hej vad heter du'
    """
    skip = 'MAD MID PAD'.split()
    for word, pos in cols:
        if pos not in skip:
            yield word


def lix_annot(order, text, parent_text, sentence, parent_sentence, words, pos, out):
    structs = [(text, parent_text), (sentence, parent_sentence)]
    columns = [words, pos]
    texts = cwb.vrt_iterate(*cwb.tokens_and_vrt(order, structs, columns),
                            trail=[0,1])
    util.write_annotation(out, (
        (span, str(lix(actual_words(cols) for _, cols in sentences)))
        for (_, span), sentences in texts
    ))


def lix(sentences):
    """
    Calculates LIX, assuming that all tokens are actual words: not punctuation
    nor delimiters.

    >>> print('%.2f' % lix(4*["a bc def ghij klmno pqrstu vxyzåäö".split()]))
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
    return w/s + 100*l/w


def ovix_annot(order, text, parent_text, words, pos, out):
    structs = [(text, parent_text)]
    columns = [words, pos]
    texts = cwb.vrt_iterate(*cwb.tokens_and_vrt(order, structs, columns))
    util.write_annotation(out, (
        (span, str(ovix(actual_words(cols))))
        for (_, span), cols in texts
    ))


def ovix(words):
    """
    Calculates OVIX, assuming that all tokens are actual words: not punctuation
    nor delimiters.

    Words are compared ignoring case.

    >>> for i in range(5):
    ...     print('%.2f' % ovix((i*"a bc def ghij klmno pqrstu vxyzåäö ").split()))
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
        return log(w)/log(2-log(uw)/log(w))


def nominal_ratio_annot(order, text, parent_text, pos, out):
    structs = [(text, parent_text)]
    columns = [pos]
    texts = cwb.vrt_iterate(*cwb.tokens_and_vrt(order, structs, columns))
    util.write_annotation(out, (
        (span, str(nominal_ratio(col[0] for col in cols)))
        for (_, span), cols in texts
    ))


def nominal_ratio(pos):
    """
    Calculates nominal ratio (nominalkvot).

    >>> nominal_ratio('NN JJ'.split())
    inf
    >>> nominal_ratio('NN NN VB'.split())
    2.0
    >>> nominal_ratio('NN PP PC PN AB VB MAD MID'.split())
    1.0
    >>> nominal_ratio('NN AB VB PP PN PN MAD'.split())
    0.5
    >>> nominal_ratio('RG VB'.split())
    0.0
    """
    n = JavascriptStyleGetters(Counter(pos))
    try:
        return float(n.NN + n.PP + n.PC) / (n.PN + n.AB + n.VB)
        # nouns prepositions participles / pronouns adverbs verbs
    except ZeroDivisionError:
        return float('inf')


class JavascriptStyleGetters(object):
    """
    Wrap a dict d to make d.x mean d[x]:

    >>> JavascriptStyleGetters(dict(a = 5)).a
    5
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, x):
        return self.wrapped[x]


if __name__ == '__main__':
    util.run.main(lix=lix_annot,
                  ovix=ovix_annot,
                  nominal_ratio=nominal_ratio_annot)
