# -*- coding: utf-8 -*-
import sparv.util as util
import sparv.saldo as saldo
from collections import defaultdict


def make_morphtable(out, saldo_model, suc, morphtable_base="", morphtable_patterns="", add_capitalized=True, add_lowercase=False):
    """ Creates a morphtable file for use with Hunpos, containing wordforms
    from SALDO's morphology (with accompanying tags) which are missing in SUC3.
    Since the morphtable is case sensitive, both the original form and a capitalized form
    is saved.
    - out specifies the resulting morphtable file to be written
    - saldo_model is the path to a pickled SALDO model
    - suc is a tab separated file with wordforms from SUC, containing: frequency, wordform, tag
    - morphtable_base is an existing morphtable file, whose contents will be included in the new one
    - morphtable_patterns is an optional file with regular expressions
    """

    l = saldo.SaldoLexicon(saldo_model)
    tags = defaultdict(set)

    # Get all wordforms from SALDO
    for word in list(l.lexicon.keys()):
        words = l.lookup(word)
        # Filter out multi word expressions
        words = [x for x in words if len(x[2]) == 0]
        if words:
            # Only use MSD not containing "-"
            for w in words:
                for msd in w[1]:
                    if "-" not in msd:
                        tags[word].add(msd)
                        if add_capitalized:
                            # Add a capitalized form of the word
                            capitalized = word[0].upper() + word[1:]
                            if not word == capitalized:
                                tags[capitalized].add(msd)
                        if add_lowercase:
                            # Add a lower case form of the word
                            lower = word.lower()
                            if not word == lower:
                                tags[lower].add(msd)

    # Read SUC words
    with open(suc, encoding="UTF-8") as suctags:
        for line in suctags:
            _, word, msd = line.strip("\n").split("\t")

            # Don't keep SALDO words already in SUC
            if word in tags:
                del tags[word]
            # If the word is not a name, and exists as lowercase in SALDO, remove it
            elif not msd.startswith("PM") and not word.lower() == word and word.lower() in tags:
                del tags[word.lower()]

    # Read regular expressions from pattern file
    pattern_list = []
    if morphtable_patterns:
        with open(morphtable_patterns, mode="r", encoding="UTF-8") as pat:
            for line in pat:
                if line.strip() and not line.startswith("#"):
                    pattern_name, _, pattern_tags = line.strip().split("\t", 2)
                    pattern_list.append("[[%s]]\t%s\n" % (pattern_name, pattern_tags))

    with open(out, encoding="UTF-8", mode="w") as out:
        if morphtable_base:
            with open(morphtable_base, encoding="UTF-8") as base:
                for line in base:
                    out.write(line)

        for pattern in pattern_list:
            out.write(pattern)

        for word in sorted(tags):
            out.write("%s\t%s\n" % (word, "\t".join(tags[word])))

if __name__ == '__main__':
    util.run.main(make_morphtable)
