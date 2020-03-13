# -*- coding: utf-8 -*-
import pickle
import re
import sparv.util as util
from nltk import FreqDist, LidstoneProbDist


def make_model(nst_infile, picklefile, protocol=-1):
    """ Train a POS probability model on the NST lexicon and save it as a pickle file.
    The model is a LidstoneProbDist (NLTK) which has compounded POS tags (SUC set) as keys (e.g. "NN+NN")
    and smoothed probabilities as values."""
    # Collect all compounds from nst data
    nst_full_compounds = set()
    with open(nst_infile, encoding='UTF-8') as f:
        for line in f:
            fields = line[:-1].split('\t')
            word = fields[0]
            comp = fields[3].replace("!", "")
            pos = fields[4]
            if "+" in comp and "_" not in word and not (comp.startswith("+") or comp.startswith("-")):
                nst_full_compounds.add((word, comp, pos))

    # Build POS probability model
    pos_fdist = FreqDist()
    for _w, _c, pos in nst_full_compounds:
        if '+' in pos:
            pos = re.sub(r"\+LN", "", pos)
            pos_fdist[pos] += 1

    pd = LidstoneProbDist(pos_fdist, 0.001, pos_fdist.B())

    # Save probability model as pickle
    with open(picklefile, "wb") as f:
        pickle.dump(pd, f, protocol=protocol)


if __name__ == '__main__':
    util.run.main(make_model)
