# -*- coding: utf-8 -*-
"""
Used by crf.py
"""
punctuation = frozenset([u',', u':', u'/', u'.', u'·', u'¶', u';', '°', '-', '—'])
vowels = frozenset(u'aeiouvöäåy')


def features(xxx_todo_changeme, tag):
    (word, lookslikeanumber) = xxx_todo_changeme
    return (word.lower(),
            'CAP' if word[0].isupper() else 'NOCAP',
            word.lower()[-2:],
            'NUMLIKE' if lookslikeanumber else 'PNCLIKE' if word in punctuation else 'WRDLIKE',
            tag)


def thousands(w):
    return w.lstrip('Mm')


def hundreds(w):
    if w.lower()[0:5] == u'dcccc':
        return w[5:]
    elif w.lower()[0:4] in (u'cccc', u'dccc'):
        return w[4:]
    elif w.lower()[0:3] in (u'ccc', u'dcc'):
        return w[3:]
    elif w.lower()[0:2] in (u'cc', 'cd', 'dc', 'cm'):
        return w[2:]
    elif w.lower()[0:1] in (u'c', 'd'):
        return w[1:]
    else:
        return w


def tens(w):
    if w.lower()[0:5] == u'lxxxx':
        return w[5:]
    elif w.lower()[0:4] in (u'xxxx', u'lxxx'):
        return w[4:]
    elif w.lower()[0:3] in (u'xxx', u'lxx'):
        return w[3:]
    elif w.lower()[0:2] in (u'xx', 'xl', 'lx', 'xc'):
        return w[2:]
    elif w.lower()[0:1] in (u'x', 'l'):
        return w[1:]
    else:
        return w


def ones(w):
    if w.lower()[0:5] == u'viiii':
        return w[5:]
    elif w.lower()[0:4] in (u'iiii', u'viii'):
        return w[4:]
    elif w.lower()[0:3] in (u'iii', u'vii'):
        return w[3:]
    elif w.lower()[0:2] in (u'ii', 'iv', 'vi', 'ix'):
        return w[2:]
    elif w.lower()[0:1] in (u'i', 'v'):
        return w[1:]
    else:
        return w


def lookslikearomananumber(w):
    return not ones(tens(hundreds(thousands(w))))


def lookslikeanarabicnumber(w):
    return any(c in '0123456789' for c in w)


def lookslikeanumber(w):
    return lookslikearomananumber(w) or lookslikeanarabicnumber(w)


# NB! normalize does a [jJ] -> [iI] conversion first...
twonormdict = dict([(u'AA', u'A'), (u'Aa', u'A'), (u'aa', u'a'),
                    (u'EE', u'E'), (u'Ee', u'E'), (u'ee', u'e'),
                    (u'II', u'I'), (u'Ii', u'I'), (u'ii', u'i'),
                    (u'OO', u'O'), (u'Oo', u'O'), (u'oo', u'o'),
                    (u'UU', u'V'), (u'Uu', u'V'), (u'uu', u'v'),
                    (u'WW', u'V'), (u'Ww', u'V'), (u'ww', u'v'),
                    (u'ÖÖ', u'Ö'), (u'Öö', u'Ö'), (u'öö', u'ö'),
                    (u'ÄÄ', u'Ä'), (u'Ää', u'Ä'), (u'ää', u'ä'),
                    (u'ÅÅ', u'a'), (u'Åå', u'a'), (u'åå', u'a'),
                    (u'YY', u'Y'), (u'Yy', u'Y'), (u'yy', u'y'),
                    (u'ØØ', u'Ö'), (u'Øø', u'Ö'), (u'øø', u'ö'),
                    (u'ÆÆ', u'Ä'), (u'Ææ', u'Ä'), (u'ææ', u'ä'),
                    (u'TH', u'T'), (u'Th', u'T'), (u'th', u't'),
                    (u'DH', u'D'), (u'Dh', u'D'), (u'dh', u'd'),
                    (u'GH', u'G'), (u'Gh', u'G'), (u'gh', u'g'),
                    (u'FF', u'F'), (u'Ff', u'F'), (u'ff', u'f'),
                    (u'ch', u'k')])

onenormdict = dict([(u'Ø', u'Ö'), (u'ø', u'ö'),
                    (u'Æ', u'Ä'), (u'æ', u'ä'),
                    (u'Å', u'a'), (u'å', u'a'),
                    (u'W', u'V'), (u'w', u'v'),
                    (u'U', u'V'), (u'u', u'v'),
                    (u'C', u'K'), (u'c', u'k'),
                    (u'Q', u'K'), (u'q', u'k'),
                    (u'Þ', u'D'), (u'þ', u'd'),
                    (u'Ð', u'D'), (u'ð', u'd')])


def normalize(word):
    word = word.replace(u'j', 'i').replace(u'J', u'I')
    if lookslikeanumber(word):
        return word, 1
    else:
        normword = []
        i = 0
        while i < len(word):
            if word[i:i + 2] in twonormdict:
                normword.append(twonormdict[word[i:i + 2]])
                i += 2
            elif word[i] in onenormdict:
                normword.append(onenormdict[word[i]])
                i += 1
            else:
                normword.append(word[i])
                i += 1

        return ''.join(normword), 0


def main(stream):
    newdiv = 1

    l_features = features

    for line in stream:
        raws = line.strip().split()
        words = [normalize(word) for word in raws]
        words_length = len(words)

        raws = iter(raws)

        print('words length %d' % words_length)
        if words_length == 0:
            if not newdiv:
                print()
                newdiv = 1
            else:
                pass
        elif words_length == 1:
            print('\t'.join((next(raws),) + l_features(words[0], u'SNG') + ('id', '52')))
            newdiv = 0
        else:
            lastword = words.pop()
            words = iter(words)
            for i, w in enumerate(words):
                print('\t'.join((next(raws), ) + l_features(w, u'LF%s' % (i,)) + ('id', '53')))
                if i >= 1:
                    break

            for w in words:
                print('\t'.join((next(raws),) + l_features(w, u'MID') + ('id', '54')))

            print('\t'.join((next(raws),) + l_features(lastword, u'RHT') + ('id', '54')))

            newdiv = 0

    if not newdiv:
        print()
