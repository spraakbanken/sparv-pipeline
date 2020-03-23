"""Calculate readability measures (läsbarhetsmått)."""

import sparv.util as util
from math import log


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
    skip_pos = skip_pos.split()
    for word, pos in cols:
        if pos not in skip_pos:
            yield word


def lix_annot(doc, text, sentence, word, pos, out, skip_pos="MAD MID PAD", fmt="%.2f"):
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
        lix_annotation.append(fmt % lix(in_sentences))

    util.write_annotation(doc, out, lix_annotation)


def lix(sentences):
    """
    Calculate LIX, assuming that all tokens are actual words, not punctuation or delimiters.

    >>> print("%.2f" % lix(4*["a bc def ghij klmno pqrstu vxyzåäö".split()]))
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


def ovix_annot(doc, text, word, pos, out, skip_pos="MAD MID PAD", fmt="%.2f"):
    """Create OVIX annotation for text."""
    text_children, _orphans = util.get_children(doc, text, word)
    word_pos = list(util.read_annotation_attributes(doc, (word, pos)))

    # Calculate OVIX for every text element
    ovix_annotation = []
    for text in text_children:
        in_words = list(actual_words([word_pos[token_index] for token_index in text], skip_pos))
        ovix_annotation.append(fmt % lix(in_words))

    util.write_annotation(doc, out, ovix_annotation)


def ovix(words):
    """
    Calculate OVIX, assuming that all tokens are actual words, not punctuation or delimiters.

    Words are compared ignoring case.

    >>> for i in range(5):
    ...     print("%.2f" % ovix((i*"a bc def ghij klmno pqrstu vxyzåäö ").split()))
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


def nominal_ratio_annot(doc, text, pos, out, noun_pos="NN PP PC", verb_pos="PN AB VB", fmt="%.2f"):
    """Creata nominal ratio annotation for text."""
    text_children, _orphans = util.get_children(doc, text, pos)
    pos_annotation = list(util.read_annotation(doc, pos))

    # Calculate OVIX for every text element
    nk_annotation = []
    for text in text_children:
        in_pos = [pos_annotation[token_index] for token_index in text]
        nk_annotation.append(fmt % nominal_ratio(in_pos, noun_pos, verb_pos))
    util.write_annotation(doc, out, nk_annotation)


def nominal_ratio(pos, noun_pos, verb_pos):
    """
    Calculate nominal ratio (nominalkvot).

    >>> "%.1f" % nominal_ratio('NN JJ'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    'inf'
    >>> "%.1f" % nominal_ratio('NN NN VB'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    '2.0'
    >>> "%.1f" % nominal_ratio('NN PP PC PN AB VB MAD MID'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    '1.0'
    >>> "%.1f" % nominal_ratio('NN AB VB PP PN PN MAD'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    '0.5'
    >>> "%.1f" % nominal_ratio('RG VB'.split(), noun_pos="NN PP PC", verb_pos="PN AB VB")
    '0.0'
    """
    # nouns prepositions participles
    nouns = sum(1 for p in pos if p in noun_pos.split())
    # pronouns adverbs verbs
    verbs = sum(1 for p in pos if p in verb_pos.split())
    try:
        nk = float(nouns) / float(verbs)
        return nk
    except ZeroDivisionError:
        return float('inf')


if __name__ == '__main__':
    util.run.main(lix=lix_annot,
                  ovix=ovix_annot,
                  nominal_ratio=nominal_ratio_annot)
