# -*- coding: utf-8 -*-
import sparv.util as util
import re

# Constants
SALDO_TO_SUC = util.tagsets.saldo_to_suc
SALDO_TO_SUC['pm'] = {'PM.NOM'}
SALDO_TO_SUC['nl invar'] = {'NL.NOM'}


def make_table(out, files, saldosuc_morphtable):
    """ Read files and make a morphtable of the information in them
    together with the information from SALDO (saldosuc_morphtable).
    Used by SB_MODELS/Makefile
    - out specifies the resulting morphtable file to be written
    - files is a string of files containing wordlists and SALDO MSD-tags
    - saldosuc_morphtable is the SALDO Hunpos morphtable
    """

    files = files.split()
    words = {}
    read_saldosuc(words, saldosuc_morphtable)
    for fil in files:
        for line in open(fil, 'r', encoding='utf-8').readlines():
            if not line.strip():
                continue
            xs = line.split('\t')
            word, msd = xs[0].strip(), xs[1].strip()
            if ' ' in word:
                if msd.startswith('nn'):  # We assume that the head of a noun mwe is the last word
                    word = word.split()[-1]
                if msd.startswith('vb'):  # We assume that the head of a verbal mwe is the first word
                    word = word.split()[0]

            # If the tag is not present, we try to translate it anyway
            suc = SALDO_TO_SUC.get(msd, '')
            if not suc:
                suc = force_parse(msd)
            if suc:
                words.setdefault(word.lower(), set()).update(suc)
                words.setdefault(word.title(), set()).update(suc)
    with open(out, encoding="UTF-8", mode="w") as out:
        for w, ts in list(words.items()):
            line = ('\t'.join([w] + list(ts)) + "\n")
            out.write(line)


def read_saldosuc(words, saldosuc_morphtable):
    for line in open(saldosuc_morphtable, 'r', encoding='utf-8').readlines():
        xs = line.strip().split('\t')
        words.setdefault(xs[0], set()).update(set(xs[1:]))


def force_parse(msd):
    # This is a modifcation of _make_saldo_to_suc in utils.tagsets.py
    params = msd.split()

    # try ignoring gender, m/f => u
    for i, param in enumerate(params):
        if param.strip() in ['m', 'f']:
            params[i] = 'u'
    new_suc = SALDO_TO_SUC.get(' '.join(params), '')

    if new_suc:
        # print 'Add translation', msd,new_suc
        SALDO_TO_SUC[msd] = new_suc
        return new_suc

    # try changing place: nn sg n indef nom => nn n sg indef nom
    if params[0] == 'nn':
        new_suc = SALDO_TO_SUC.get(' '.join([params[0], params[2], params[1], params[3], params[4]]), '')

    if new_suc:
        # print 'Add translation', msd,new_suc
        SALDO_TO_SUC[msd] = new_suc
        return new_suc

    # try adding case info: av pos def pl => av pos def pl nom/gen
    if params[0] == 'av':
        new_suc = SALDO_TO_SUC.get(' '.join(params + ['nom']), set())
        new_suc.update(SALDO_TO_SUC.get(' '.join(params + ['gen']), set()))

    if new_suc:
        # print 'Add translation', msd,new_suc
        SALDO_TO_SUC[msd] = new_suc
        return new_suc

    paramstr = " ".join(util.tagsets._translate_saldo_parameters.get(prm, prm.upper()) for prm in params)
    for (pre, post) in util.tagsets._suc_tag_replacements:
        m = re.match(pre, paramstr)
        if m:
            break
    if m is None:
        return set()
    sucfilter = m.expand(post).replace(" ", r"\.").replace("+", r"\+")
    new_suc = set(suctag for suctag in util.tagsets.suc_tags if re.match(sucfilter, suctag))
    SALDO_TO_SUC[msd] = new_suc
    return new_suc


if __name__ == "__main__":
    util.run.main(make_table)
