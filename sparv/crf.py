# -*- coding: utf-8 -*-

"""
Tokenization based on Conditional Random Fields, implemented for Old Swedish.
Used by segment.CRFTokenizer.
Requires installation of crfpp (https://taku910.github.io/crfpp/).
"""

import CRFPP
from sparv.util.flat_txt2crf import normalize, features

""" Expects a model that operating on the tags
        SNG | LF0 (LF1 MID*)? RHT
        SNG = single word
        LF0 = first word
        LF1 = second word
        MID = middle word
        RHT = right most word
        """


def segment(sentence, model):
    try:
        tagger = CRFPP.Tagger("-m " + model)

        # clear internal context
        tagger.clear()

        l_features = features

        splitted = split_enumerate(sentence, '.')
        raws = [word for word, span in splitted]
        words = [(normalize(word), span) for word, span in splitted]
        words_length = len(words)

        raws = iter(raws)

        if words_length == 0:
            return [(0, 0)]
        else:
            lastword, last_span = words.pop()
            words = iter(words)
            last_span = str(last_span[0]), str(last_span[0])

            # add context
            for i, (w, span) in enumerate(words):
                nextline = '\t'.join((next(raws),) + l_features(w, u'LF%s' % (i,))).encode('utf-8')
                tagger.add(nextline)

                if i >= 1:
                    break

            for w, span in words:
                # s_span = (str(span[0]), str(span[1]))
                nextline = '\t'.join((next(raws),) + l_features(w, u'MID')).encode('utf-8')
                tagger.add(nextline)

            nextline = '\t'.join((next(raws),) + l_features(lastword, u'RHT')).encode('utf-8')
            tagger.add(nextline)

            # Parse and change internal stated as 'parsed'
            tagger.parse()
            anchors = crf_anchors(tagger, splitted)
            # print "Done tagging crf"
            return anchors

    except RuntimeError as e:
        print("RuntimeError: ", e, end=' ')


def crf_anchors(tagger, enumerated_sent):
    anchors = []
    last_start, last_stop = 0, -1
    size = tagger.size()
    # xsize = tagger.xsize()
    # ysize = tagger.ysize()

    # print enumerated_sent[25:]
    words = iter(enumerated_sent)

    for i in range(0, size):
        label = tagger.y2(i)
        w, span = next(words)
        # print w,span

        if label == 'SNG':
            # SNG (singleton) tag
            anchors.append((span[0], span[1]))
            last_stop = -1

        elif label == 'LF0':
            # Start new sentence on LF0 (first word in sentenceq)
            if last_stop:
                anchors.append((last_start, last_stop))
            last_start = span[0]
            last_stop = span[1]

        else:
            # Otherwise add token to current sentence
            last_stop = span[1]

    if last_stop != -1:
        anchors.append((int(last_start), int(span[1])))
    # print anchors
    return anchors


def split_enumerate(words, delimiters=[]):
    res = []
    tmp, tmp_i = '', -1

    for i, w in enumerate(words + ' '):
        if w in delimiters:
            if tmp:
                res.append((tmp, (tmp_i, i)))
            res.append((w, (i, i + 1)))
            tmp, tmp_i = '', -1

        elif not w.isspace():
            if tmp_i == -1:
                tmp_i = i
            tmp += w

        elif tmp:
            res.append((tmp, (tmp_i, i)))
            tmp, tmp_i = '', -1

    if tmp:
        res.append((tmp, (tmp_i, i)))
    return res
