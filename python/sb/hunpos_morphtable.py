# -*- coding: utf-8 -*-

import util
import saldo
import codecs
from collections import defaultdict

def make_morphtable(out, saldo_model, suc, morphtable_base=""):
    """ Creates a morphtable file for use with Hunpos, containing wordforms
    from SALDO's morphology (with accompanying tags) which are missing in SUC3.
    - out specifies the resulting morphtable file to be written
    - saldo_model is the path to a pickled SALDO model
    - suc is a tab separated file with wordforms from SUC, containing: frequency, wordform, tag
    - morphtable_base is an existing morphtable file, chose contents will be added to the new one
    """
    
    l = saldo.SaldoLexicon(saldo_model)
    tags = defaultdict(set)
    
    # Get all wordforms from SALDO
    for word in l.lexicon.iterkeys():
        words = l.lookup(word)
        # Filter out multi word expressions
        words = filter(lambda x: len(x[2]) == 0, words)
        if words:
            # Only use MSD not containing "-"
            for w in words:
                for msd in w[1]:
                    if not "-" in msd:
                        tags[word].add(msd)
                        # Add a capitalized form of the word
                        capitalized = word[0].upper() + word[1:]
                        if not word == capitalized:
                            tags[capitalized].add(msd)
            
    
    # Read SUC words
    with codecs.open(suc, encoding="UTF-8") as suctags:
        for line in suctags:
            _, word, msd = line.strip("\n").split("\t")
            
            # Don't keep SALDO words already in SUC
            if word in tags:
                del tags[word]
            # If the word is not a name, and exists as lowercase in SALDO, remote it
            elif not msd.startswith("PM") and not word.lower() == word and word.lower() in tags:
                del tags[word.lower()]
    
    with codecs.open(out, encoding="UTF-8", mode="w") as out:
        if morphtable_base:
            with codecs.open(morphtable_base, encoding="UTF-8") as base:
                for line in base:
                    out.write(line)
    
        for word in sorted(tags):
                out.write("%s\t%s\n" % (word, "\t".join(tags[word])))

if __name__ == '__main__':
    util.run.main(make_morphtable)
