"""Create morphtable files for use with Hunpos."""

from collections import defaultdict

from sparv.api import Model, ModelOutput, modelbuilder
from sparv.modules.saldo import saldo


@modelbuilder("Hunpos morphtable input files", language=["swe"])
def morphtable_inputs(suc: ModelOutput = ModelOutput("hunpos/suc3_morphtable.words"),
                      morphtable_base: ModelOutput = ModelOutput("hunpos/suc.morphtable"),
                      morphtable_patterns: ModelOutput = ModelOutput("hunpos/suc.patterns")):
    """Download the files needed to build the SALDO morphtable."""
    suc.download("https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc3_morphtable.words")

    morphtable_base.download("https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc.morphtable")

    morphtable_patterns.download("https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc.patterns")


@modelbuilder("Hunpos-SALDO morphtable", language=["swe"])
def saldo_morphtable(out: ModelOutput = ModelOutput("hunpos/saldo_suc-tags.morphtable"),
                     saldo_model: Model = Model("saldo/saldo.pickle"),
                     suc: Model = Model("hunpos/suc3_morphtable.words"),
                     morphtable_base: Model = Model("hunpos/suc.morphtable"),
                     morphtable_patterns: Model = Model("hunpos/suc.patterns"),
                     add_capitalized: bool = True,
                     add_lowercase: bool = False):
    """Create a morphtable file for use with Hunpos.

    A morphtable contains wordforms from SALDO's morphology (with accompanying tags) which are missing in SUC3.
    Since the morphtable is case sensitive, both the original form and a capitalized form
    is saved.

    Args:
        out (str, optional): Resulting morphtable file to be written.
            Defaults to ModelOutput("hunpos/saldo_suc-tags.morphtable").
        saldo_model (str, optional): Path to a pickled SALDO model.
            Defaults to Model("saldo/saldo.pickle").
        suc (str, optional): Tab-separated file with wordforms from SUC, containing: frequency, wordform, tag.
            Defaults to Model("hunpos/suc3_morphtable.words").
        morphtable_base (str, optional): Existing morphtable file, whose contents will be included in the new one.
            Defaults to Model("hunpos/suc.morphtable").
        morphtable_patterns (str, optional): Optional file with regular expressions.
            Defaults to Model("hunpos/suc.patterns").
        add_capitalized (bool, optional): Whether or not capitalized word forms should be added. Defaults to True.
        add_lowercase (bool, optional): Whether or not lower case word forms should be added. Defaults to False.
    """
    lex = saldo.SaldoLexicon(saldo_model.path)
    tags = defaultdict(set)

    # Get all wordforms from SALDO
    for word in list(lex.lexicon.keys()):
        words = lex.lookup(word)
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
    with open(suc.path, encoding="UTF-8") as suctags:
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
        with open(morphtable_patterns.path, encoding="UTF-8") as pat:
            for line in pat:
                if line.strip() and not line.startswith("#"):
                    pattern_name, _, pattern_tags = line.strip().split("\t", 2)
                    pattern_list.append("[[%s]]\t%s\n" % (pattern_name, pattern_tags))

    with open(out.path, encoding="UTF-8", mode="w") as out:
        if morphtable_base:
            with open(morphtable_base.path, encoding="UTF-8") as base:
                for line in base:
                    out.write(line)

        for pattern in pattern_list:
            out.write(pattern)

        for word in sorted(tags):
            out.write("%s\t%s\n" % (word, "\t".join(tags[word])))
