 # -*- coding: utf-8 -*-

import codecs
import cPickle as pickle
import re
from nltk import FreqDist, LidstoneProbDist


def make_model(nst_infile, picklefile):
    """ Train a POS probability model on the NST lexicon and save it as a pickle file.
    The model is a LidstoneProbabDist (NLTK) which has compounded POS tags (SUC set) as keys (e.g. "NN+NN")
    and smoothed probabilities as values."""
    # collect all compounds from nst data
    nst_full_compounds = set()
    with codecs.open(nst_infile, encoding='utf-8') as f:
        for line in f:
            fields = line[:-1].split('\t')
            word = fields[0]
            comp = fields[3].replace("!", "")
            pos = fields[4]
            if "+" in comp and not "_" in word and not (comp.startswith("+") or comp.startswith("-")):
                # glue filler morpheme to its preceding morpheme
                comp = re.sub(r'\+s\+', r's+', comp)
                comp = re.sub(r'\+e\+', r'e+', comp)
                comp = re.sub(r'\+a\+', r'a+', comp)
                comp = re.sub(r'\+-\+', r'-+', comp)
                nst_full_compounds.add((word, comp, pos))

    # build POS probability model
    pos_fdist = FreqDist()
    for _w, _c, pos in nst_full_compounds:
        if '+' in pos:
            pos = re.sub(r"\+LN", "", pos)
            pos_fdist.inc(pos)

    pd = LidstoneProbDist(pos_fdist, 0.001, pos_fdist.B())

    # save probability model as pickle
    with open(picklefile, "w") as f:
        pickle.dump(pd, f)


# if __name__ == '__main__':
#     make_model('nst_utf8.txt', 'nst.comp.pos.pickle')
