"""Create morphtable files for use with Hunpos."""

from collections import defaultdict

from sparv.api import Model, ModelOutput, modelbuilder
from sparv.modules.saldo import saldo


@modelbuilder("Hunpos morphtable input files", language=["swe"])
def morphtable_inputs(
    suc: ModelOutput = ModelOutput("hunpos/suc3_morphtable.words"),
    morphtable_base: ModelOutput = ModelOutput("hunpos/suc.morphtable"),
    morphtable_patterns: ModelOutput = ModelOutput("hunpos/suc.patterns"),
) -> None:
    """Download the files needed to build the SALDO morphtable.

    Args:
        suc: Output file for SUC morphtable words.
        morphtable_base: Output file for base morphtable.
        morphtable_patterns: Output file for morphtable patterns.
    """
    suc.download("https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc3_morphtable.words")

    morphtable_base.download("https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc.morphtable")

    morphtable_patterns.download("https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc.patterns")


@modelbuilder("Hunpos-SALDO morphtable", language=["swe"])
def saldo_morphtable(
    out: ModelOutput = ModelOutput("hunpos/saldo_suc-tags.morphtable"),
    saldo_model: Model = Model("saldo/saldo.pickle"),
    suc: Model = Model("hunpos/suc3_morphtable.words"),
    morphtable_base: Model = Model("hunpos/suc.morphtable"),
    morphtable_patterns: Model = Model("hunpos/suc.patterns"),
    add_capitalized: bool = True,
    add_lowercase: bool = False,
) -> None:
    """Create a morphtable file for use with Hunpos.

    A morphtable contains word forms from SALDO's morphology (with accompanying tags) which are missing in SUC3.
    Since the morphtable is case-sensitive, both the original form and a capitalized form
    is saved.

    Args:
        out: Resulting morphtable file to be written.
        saldo_model: Path to a pickled SALDO model.
        suc: Tab-separated file with word forms from SUC, containing: frequency, word form, tag.
        morphtable_base: Existing morphtable file, whose contents will be included in the new one.
        morphtable_patterns: Optional file with regular expressions.
        add_capitalized: Whether capitalized word forms should be added.
        add_lowercase: Whether lower case word forms should be added.
    """
    lex = saldo.SaldoLexicon(saldo_model.path)
    tags = defaultdict(set)

    # Get all word forms from SALDO
    for word in lex.lexicon:
        words = lex.lookup(word)
        # Filter out multi-word expressions
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
                            if word != capitalized:
                                tags[capitalized].add(msd)
                        if add_lowercase:
                            # Add a lower case form of the word
                            lower = word.lower()
                            if word != lower:
                                tags[lower].add(msd)

    # Read SUC words
    with suc.path.open(encoding="UTF-8") as suctags:
        for line in suctags:
            _, word, msd = line.strip("\n").split("\t")

            # Don't keep SALDO words already in SUC
            if word in tags:
                del tags[word]
            # If the word is not a name, and exists as lowercase in SALDO, remove it
            elif not msd.startswith("PM") and word.lower() != word and word.lower() in tags:
                del tags[word.lower()]

    # Read regular expressions from pattern file
    pattern_list = []
    if morphtable_patterns:
        with morphtable_patterns.path.open(encoding="UTF-8") as pat:
            for line in pat:
                if line.strip() and not line.startswith("#"):
                    pattern_name, _, pattern_tags = line.strip().split("\t", 2)
                    pattern_list.append(f"[[{pattern_name}]]\t{pattern_tags}\n")

    with out.path.open(encoding="UTF-8", mode="w") as out_file:
        if morphtable_base:
            with morphtable_base.path.open(encoding="UTF-8") as base:
                for line in base:
                    out_file.write(line)

        for pattern in pattern_list:
            out_file.write(pattern)

        for word in sorted(tags):
            out_file.write("{}\n".format("\t".join([word, *tags[word]])))
