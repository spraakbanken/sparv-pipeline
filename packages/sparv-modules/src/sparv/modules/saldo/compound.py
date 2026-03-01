"""Compound analysis."""

import itertools
import operator
import pathlib
import pickle
import re
import time
import xml.etree.ElementTree as etree  # noqa: N813
from collections.abc import Generator
from functools import reduce

import nltk

from sparv.api import Annotation, Config, Model, ModelOutput, Output, annotator, get_logger, modelbuilder, util
from sparv.api.util.tagsets import tagmappings

logger = get_logger(__name__)

MAX_WORD_LEN = 75  # Max length of a word to get a compound analysis
SPLIT_LIMIT = 200  # Max number of different ways to split a word
COMP_LIMIT = 100  # Max segments in a compound
INVALID_PREFIXES = ("http:", "https:", "www.")  # Skip words starting with these prefixes
INVALID_REGEX = re.compile(r"(..?)\1{3}")  # Skip words with more than 3 identical letters in a row
MAX_ITERATIONS = 250000  # Max iterations per word when performing compound analysis
MAX_TIME = 20  # Max time in seconds per word when performing compound analysis

# SALDO: Delimiters that hopefully are never found in an annotation or in a POS tag:
PART_DELIM = "^"
PART_DELIM1 = "^1"
PART_DELIM2 = "^2"
PART_DELIM3 = "^3"


def preloader(saldo_comp_model: Model, stats_model: Model) -> tuple:
    """Preload models for compound analysis.

    Args:
        saldo_comp_model: Path to SALDO compound model.
        stats_model: Path to statistics model.

    Returns:
        Preloaded models.
    """
    return SaldoCompLexicon(saldo_comp_model.path), StatsLexicon(stats_model.path)


@annotator(
    "Compound analysis",
    name="compound",
    config=[
        Config(
            "saldo.comp_model",
            default="saldo/saldo.compound.pickle",
            description="Path to SALDO compound model",
            datatype=str,
        ),
        Config(
            "saldo.comp_nst_model",
            default="saldo/nst_comp_pos.pickle",
            description="Path to NST part of speech compound model",
            datatype=str,
        ),
        Config(
            "saldo.comp_stats_model", default="saldo/stats.pickle", description="Path to statistics model", datatype=str
        ),
        Config(
            "saldo.comp_use_source",
            default=True,
            description="Also use source text as lexicon for compound analysis",
            datatype=bool,
        ),
    ],
    preloader=preloader,
    preloader_params=["saldo_comp_model", "stats_model"],
    preloader_target="preloaded_models",
)
def annotate(
    out_complemgrams: Output = Output("<token>:saldo.complemgram", description="Compound analysis using lemgrams"),
    out_compwf: Output = Output("<token>:saldo.compwf", description="Compound analysis using wordforms"),
    out_baseform: Output = Output(
        "<token>:saldo.baseform2", description="Baseform including baseforms derived from compounds"
    ),
    word_annotation: Annotation = Annotation("<token:word>"),
    msd_annotation: Annotation = Annotation("<token:msd>"),
    baseform_annotation: Annotation = Annotation("<token>:saldo.baseform"),
    saldo_comp_model: Model = Model("[saldo.comp_model]"),
    nst_model: Model = Model("[saldo.comp_nst_model]"),
    stats_model: Model = Model("[saldo.comp_stats_model]"),
    comp_use_source: bool = Config("saldo.comp_use_source"),
    complemgramfmt: str = util.constants.SCORESEP + "%.3e",
    delimiter: str = util.constants.DELIM,
    compdelim: str = util.constants.COMPSEP,
    affix: str = util.constants.AFFIX,
    cutoff: bool = True,
    preloaded_models: tuple | None = None,
) -> None:
    """Divide compound words into prefix(es) and suffix.

    Args:
        out_complemgrams: Output annotation for compound lemgrams.
        out_compwf: Output annotation for compound wordforms.
        out_baseform: Output annotation for baseforms (including baseforms for compounds).
        word_annotation: Existing annotation for wordforms.
        msd_annotation: Existing annotation for parts of speech.
        baseform_annotation: Existing SALDO annotation for baseforms (not including compounds).
        saldo_comp_model: Path to SALDO compound model.
        nst_model: Path to NST part of speech compound model.
        stats_model: Path to statistics model.
        comp_use_source: Use source text as lexicon for compound analysis.
        complemgramfmt: Format string for how to format the probability of the complemgram.
        delimiter: Delimiter used between values in the output annotations.
        compdelim: Delimiter used between parts of the compound in the output annotations.
        affix: Affix used in the output annotations.
        cutoff: Only keep analyses with the same length (or +1) as the most probable one.
        preloaded_models: Preloaded models for compound analysis, used by the preloader.
    """
    logger.progress()
    ##################
    # Load models
    ##################
    if preloaded_models:
        saldo_comp_lexicon, stats_lexicon = preloaded_models
    else:
        saldo_comp_lexicon = SaldoCompLexicon(saldo_comp_model.path)
        stats_lexicon = StatsLexicon(stats_model.path)

    with nst_model.path.open("rb") as f:
        nst_model = pickle.load(f)

    word_msd_baseform_annotations = list(
        word_annotation.read_attributes((word_annotation, msd_annotation, baseform_annotation))
    )
    logger.progress(total=103)
    per_percent = int(len(word_msd_baseform_annotations) / 100)

    # Create alternative lexicon (for words within the source file)
    altlexicon = InFileLexicon(word_msd_baseform_annotations if comp_use_source else [])

    ##################
    # Do annotation
    ##################
    complem_annotation = []
    compwf_annotation = []
    baseform_annotation = []

    previous_compounds = {}

    for counter, (word, msd, baseform_orig) in enumerate(word_msd_baseform_annotations):
        key = (word, msd)
        if key in previous_compounds:
            compounds = previous_compounds[key]
        else:
            compounds = compound(saldo_comp_lexicon, altlexicon, word, msd)

            if compounds:
                compounds = rank_compounds(compounds, nst_model, stats_lexicon)

                if cutoff:
                    # Only keep analyses with the same length (or +1) as the most probable one
                    best_length = len(compounds[0][1])
                    i = 0
                    for c in compounds:
                        if len(c[1]) > best_length + 1 or len(c[1]) < best_length:
                            break

                        i += 1
                    compounds = compounds[:i]

            previous_compounds[key] = compounds

        # Create complem and compwf annotations
        complem, compwf = make_complem_and_compwf(complemgramfmt, compounds, compdelim, delimiter, affix)
        complem_annotation.append(complem)
        compwf_annotation.append(compwf)

        # Create new baseform annotation if necessary
        if baseform_orig != affix:
            baseform_annotation.append(baseform_orig)
        else:
            baseform_annotation.append(make_new_baseforms(msd, compounds, stats_lexicon, altlexicon, delimiter, affix))

        if per_percent and counter % per_percent == 0:
            logger.progress()

    if per_percent == 0:
        logger.progress()

    out_complemgrams.write(complem_annotation)
    logger.progress()
    out_compwf.write(compwf_annotation)
    logger.progress()
    out_baseform.write(baseform_annotation)
    logger.progress()


@modelbuilder("SALDO compound model", order=1)
def download_saldo_comp(out: ModelOutput = ModelOutput("saldo/saldo.compound.pickle")) -> None:
    """Download SALDO compound model from sparv-models repo."""
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/saldo/saldo.compound.pickle")


@modelbuilder("SALDO compound model", order=2)
def build_saldo_comp(
    out: ModelOutput = ModelOutput("saldo/saldo.compound.pickle"), saldom: Model = Model("saldo/saldom.xml")
) -> None:
    """Extract compound info from saldom.xml and save as a pickle file."""
    xml_lexicon = read_lmf(saldom.path)
    save_to_picklefile(out.path, xml_lexicon)


class SaldoCompLexicon:
    """A lexicon for Saldo compound lookups.

    It is initialized from a Pickled file.
    """

    def __init__(self, saldofile: pathlib.Path, verbose: bool = True) -> None:
        """Initialize the lexicon from a Pickled file."""
        if verbose:
            logger.info("Reading Saldo lexicon: %s", saldofile)
        with saldofile.open("rb") as f:
            self.lexicon = pickle.load(f)
        if verbose:
            logger.info("OK, read %d words", len(self.lexicon))

    def lookup(self, word: str) -> list:
        """Lookup a word in the lexicon.

        Args:
            word: The word to look up.

        Returns:
            The lexicon entry for the word, or an empty list if not found.
                The entry is a list of tuples, each containing the lemgram, SALDO MSD, SALDO POS, and list of SUC POS
                tags.
        """
        if word.lower() == word:
            annotation_tag_pairs = self.lexicon.get(word, [])
        else:
            annotation_tag_pairs = self.lexicon.get(word, []) + self.lexicon.get(word.lower(), [])
        return list(map(self._split_triple, annotation_tag_pairs))

    def get_prefixes(self, prefix: str) -> list:
        """Lookup a string and return possible analyses of that string as a prefix.

        Args:
            prefix: The prefix to look up.

        Returns:
            A list of tuples, each containing the prefix, lemgram, and list of SUC POS tags.
        """
        return [(prefix, p[0], tuple(p[3])) for p in self.lookup(prefix) if set(p[1]).intersection({"c", "ci"})]

    def get_infixes(self, infix: str) -> list:
        """Look up a string and return possible analyses of that string as an infix (middle part of a word).

        Args:
            infix: The infix to look up.

        Returns:
            A list of tuples, each containing the infix, lemgram, and list of SUC POS tags.
        """
        return [(infix, i[0], tuple(i[3])) for i in self.lookup(infix) if set(i[1]).intersection({"c", "cm"})]

    def get_suffixes(self, suffix: str, msd: str | None = None) -> list:
        """Look up a string and return possible analyses of that string as a suffix.

        Args:
            suffix: The suffix to look up.
            msd: Optional MSD tag to filter the results.

        Returns:
            A list of tuples, each containing the suffix, lemgram, and list of SUC POS tags.
        """
        return [
            (suffix, s[0], tuple(s[3]))
            for s in self.lookup(suffix)
            if (s[2] in {"nn", "vb", "av"} or s[2][-1] == "h")
            and set(s[1]).difference({"c", "ci", "cm", "sms"})
            and (msd in s[3] or not msd or [partial for partial in s[3] if partial.startswith(msd[: msd.find(".")])])
        ]

    @staticmethod
    def _split_triple(annotation_tag_words: str) -> tuple:
        """Split the annotation string into its components.

        Args:
            annotation_tag_words: The annotation string to split.

        Returns:
            A tuple containing the lemgram, SALDO MSD, SALDO POS, and list of SUC POS tags.
        """
        lemgram, msds, pos, tags = annotation_tag_words.split(PART_DELIM1)
        msds = msds.split(PART_DELIM2)
        tags = tags.split(PART_DELIM2)
        tags = list({t[: t.find(".")] if t.find(".") != -1 else t for t in tags})
        return lemgram, msds, pos, tags


class StatsLexicon:
    """A lexicon for probabilities of word forms and their POS tags.

    It is initialized from a pickled file.
    """

    def __init__(self, stats_model: pathlib.Path, verbose: bool = True) -> None:
        """Initialize the lexicon from a Pickled file."""
        if verbose:
            logger.info("Reading statistics model: %s", stats_model)
        with stats_model.open("rb") as s:
            self.lexicon = pickle.load(s)
        if verbose:
            logger.info("Done")

    def lookup_prob(self, word: str) -> float:
        """Look up the probability of the word.

        Args:
            word: The word to look up.

        Returns:
            The probability of the word.
        """
        return self.lexicon.prob(word)

    def lookup_word_tag_freq(self, word: str, tag: str) -> float:
        """Look up frequency of this word-tag combination.

        Args:
            word: The word to look up.
            tag: The tag to look up.

        Returns:
            The frequency of the word-tag combination.
        """
        return self.lexicon.freqdist()[word, tag]


class InFileLexicon:
    """A dictionary of all words occurring in the source file.

    keys = words, values =  MSD tags
    """

    def __init__(self, annotations: list[tuple[str, str, str]]) -> None:
        """Create a lexicon for the words occurring in this file."""
        lex = {}
        for word, msd, _ in annotations:
            w = word.lower()
            # Skip words consisting of a single letter (SALDO should take care of these)
            # Also skip words consisting of two letters, to avoid an explosion of analyses
            if len(w) > 2:  # noqa: PLR2004
                lex.setdefault(w, set())
                pos = msd.split(".", 1)[0]
                lex[w].add((w, pos))
        self.lexicon = lex

    def lookup(self, word: str) -> list:
        """Lookup a word in the lexicon.

        Args:
            word: The word to look up.

        Returns:
            The lexicon entry for the word, or an empty list if not found.
                The entry is a list of tuples, each containing the word and its POS tag.
        """
        return list(self.lexicon.get(word, []))

    def get_prefixes(self, prefix: str) -> list:
        """Lookup a string and return possible analyses of that string as a prefix.

        Args:
            prefix: The prefix to look up.

        Returns:
            A list of tuples, each containing the prefix, "0" (instead of lemgram), and list of SUC POS tags.
        """
        return [(prefix, "0", (s[1],)) for s in self.lookup(prefix.lower())]

    def get_suffixes(self, suffix: str, msd: str | None = None) -> list:
        """Lookup a string and return possible analyses of that string as a suffix.

        Args:
            suffix: The suffix to look up.
            msd: Optional MSD tag to filter the results.

        Returns:
            A list of tuples, each containing the suffix, "0" (instead of lemgram), and list of SUC POS tags.
        """
        return [
            (suffix, "0", (s[1],))
            for s in self.lookup(suffix.lower())
            if (s[1][0:2] in {"NN", "VB", "AV"}) and (not msd or msd in s[1] or s[1].startswith(msd[: msd.find(".")]))
        ]


################################################################################
# Auxiliaries
################################################################################


def split_word(saldo_lexicon: SaldoCompLexicon, altlexicon: InFileLexicon, w: str, msd: str) -> Generator[list[str]]:
    """Split word w into every (linguistically) possible combination of substrings.

    Args:
        saldo_lexicon: The SALDO lexicon.
        altlexicon: The alternative lexicon to use for analysis.
        w: The word to split.
        msd: The part of speech tag for the word.

    Yields:
        The word split into a list of substrings.
    """
    invalid_spans = set()
    valid_spans = set()
    # Create list of possible splitpoint indices for w
    nsplits = list(range(1, len(w)))
    counter = 0
    giveup = False
    iterations = 0
    start_time = time.time()

    for n in nsplits:
        first = True
        nn = len(nsplits)
        indices = list(range(n))

        # Similar to itertools.combinations, but customized for our needs
        while True:
            iterations += 1
            if iterations > MAX_ITERATIONS:
                giveup = True
                logger.info("Too many iterations for word '%s'", w)
                break
            if time.time() - start_time > MAX_TIME:
                giveup = True
                logger.info("Compound analysis took to long for word '%s'", w)
                break

            if first:
                first = False
            else:
                for i in reversed(range(n)):
                    if indices[i] != i + nn - n:
                        break
                else:
                    break
                indices[i] += 1
                for j in range(i + 1, n):
                    indices[j] = indices[j - 1] + 1

            splitpoint = tuple(i + 1 for i in indices)

            # Create list of affix spans
            spans = list(zip((0, *splitpoint), (*splitpoint, None), strict=True))

            # Abort if current compound contains an affix known to be invalid
            abort = False
            for ii, s in enumerate(spans):
                if s in invalid_spans:
                    if s[1] is not None:
                        # Skip any combination of spans following the invalid span
                        for j in range(ii + 1, n):
                            indices[j] = j + nn - n
                    abort = True
                    break
            if abort:
                continue

            # Expand spans with additional consonants where possible
            comps = three_consonant_rule([w[i:j] for i, j in spans])
            for comp_i, comp in enumerate(comps):
                multicomp = len(comps) > 1
                # Check if prefix is valid
                this_span = (spans[0], comp_i) if multicomp else spans[0]
                if this_span not in valid_spans:
                    if this_span in invalid_spans:
                        continue
                    elif not (saldo_lexicon.get_prefixes(comp[0]) or altlexicon.get_prefixes(comp[0])):
                        invalid_spans.add(this_span)
                        if multicomp and all((spans[0], i) in invalid_spans for i in range(len(comps))):
                            invalid_spans.add(spans[0])
                        continue
                    else:
                        valid_spans.add(this_span)

                # Check if suffix is valid
                this_span = (spans[-1], comp_i) if multicomp else spans[-1]
                if this_span not in valid_spans:
                    if this_span in invalid_spans:
                        continue
                    # Is there a possible suffix analysis?
                    elif exception(comp[-1]) or not (
                        saldo_lexicon.get_suffixes(comp[-1], msd) or altlexicon.get_suffixes(comp[-1], msd)
                    ):
                        invalid_spans.add(this_span)
                        if multicomp and all((spans[-1], i) in invalid_spans for i in range(len(comps))):
                            invalid_spans.add(spans[-1])
                        continue
                    else:
                        valid_spans.add(this_span)

                # Check if other spans are valid
                abort = False
                for k, infix in enumerate(comp[1:-1], start=1):
                    this_span = (spans[k], comp_i) if multicomp else spans[k]
                    if this_span not in valid_spans:
                        if this_span in invalid_spans:
                            abort = True
                            break
                        elif exception(infix) or not (
                            saldo_lexicon.get_infixes(infix) or altlexicon.get_prefixes(infix)
                        ):
                            invalid_spans.add(this_span)
                            if multicomp and all((spans[k], i) in invalid_spans for i in range(len(comps))):
                                invalid_spans.add(spans[k])
                            abort = True
                            # Skip any combination of spans following the invalid span
                            for j in range(k + 1, n):
                                indices[j] = j + nn - n
                            break
                        else:
                            valid_spans.add(this_span)

                if abort:
                    continue

                counter += 1
                if counter > SPLIT_LIMIT:
                    giveup = True
                    logger.info("Too many possible compounds for word '%s'", w)
                    break
                yield comp

            if giveup:
                break
        if giveup:
            break


def exception(w: str) -> bool:
    """Filter out unwanted suffixes.

    Args:
        w: The word to check.

    Returns:
        True if the word is an unwanted suffix, False otherwise.
    """
    return w.lower() in {
        "il",
        "ör",
        "en",
        "ens",
        "ar",
        "ars",
        "or",
        "ors",
        "ur",
        "urs",
        "lös",
        "tik",
        "bar",
        "lik",
        "het",
        "hets",
        "lig",
        "ligt",
        "te",
        "tet",
        "tets",
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "o",
        "p",
        "q",
        "r",
        "s",
        "t",
        "u",
        "v",
        "w",
        "x",
        "y",
        "z",
        "ä",
    }


def three_consonant_rule(compound: list[str]) -> list[list[str]]:
    """Expand each stem if its last letter equals the first letter of the following stem.

    Args:
        compound: The split compound to check.

    Returns:
        A list of expanded compounds.
            e.g. ["glas", "skål"] --> [["glas", "skål"], ["glass", "skål"]]
    """
    combinations = []
    suffix = compound[-1]
    for index in range(len(compound) - 1):
        current_prefix = compound[index]
        current_suffix = compound[index + 1]
        # Last prefix letter == first suffix letter; and prefix ends in one of "bdfgjlmnprstv"
        if current_prefix[-1].lower() in "bdfgjlmnprstv" and current_prefix[-1] == current_suffix[0]:
            combinations.append((current_prefix, current_prefix + current_prefix[-1]))
        else:
            combinations.append((current_prefix, current_prefix))
    combinations.append((suffix, suffix))
    return [list(i) for i in sorted(set(itertools.product(*combinations)))]


def rank_compounds(
    compounds: list[list[tuple[tuple, ...]]], nst_model: nltk.LidstoneProbDist, stats_lexicon: StatsLexicon
) -> list[tuple[float, tuple[tuple, ...]]]:
    """Return a list of compounds, ordered according to their ranks.

    Ranking is being done according to the amount of affixes (the fewer, the higher)
    and the compound probability which is calculated as follows:

    p((w1, tag1)..(wn, tag1)) = p(w1, tag1) ... * p(wn, tagn) * p(tag1, ...tagn)
    e.g. p(clown+bil) = p(clown, NN) * p(bil, NN) * p(NN,NN)

    Args:
        compounds: A list of compounds to rank.
        nst_model: The NST model to use for ranking.
        stats_lexicon: The statistics lexicon to use for ranking.

    Returns:
        A list of tuples, each containing the score and the compound.
            The list is sorted according to the length of the compound, the probability score, and the compound itself.
    """
    ranklist = []
    for clist in compounds:
        affixes = [affix[0] for affix in clist[0]]
        for c in clist:
            tags = list(itertools.product(*[affix[2] for affix in c]))
            # Calculate probability score
            word_probs = max(
                reduce(operator.mul, [(stats_lexicon.lookup_prob(i)) for i in zip(affixes, t, strict=True)])
                for t in tags
            )
            tag_prob = max(nst_model.prob("+".join(t)) for t in tags)
            score = word_probs * tag_prob
            ranklist.append((score, c))
    # Sort according to length and probability
    ranklist.sort(key=lambda x: (len(x[1]), -x[0], x[1]))
    return ranklist


def deep_len(lst: list) -> int:
    """Return the length of a list, including the length of nested lists.

    >>> deep_len([1, 2, [3, [4, 5]], 6, 7])
    7
    """
    return sum(deep_len(el) if isinstance(el, (list, tuple)) else 1 for el in lst)


def compound(
    saldo_lexicon: SaldoCompLexicon, altlexicon: InFileLexicon, w: str, msd: str | None = None
) -> list[list[tuple[tuple, ...]]]:
    """Create a list of compound analyses for word w.

    Args:
        w: The word to analyze.
        msd: The part of speech tag for the word.
        saldo_lexicon: The SALDO lexicon.
        altlexicon: The alternative lexicon to use for analysis.

    Returns:
        A list of lists of tuples, with possible compound analyses for the word.
            Each inner list represents a possible segmentation of the word, and each tuple contains the analysis of the
            different segments. Each segment is represented as a tuple of (string, lemgram, list of SUC POS tags).
    """
    if len(w) > MAX_WORD_LEN or INVALID_REGEX.search(w) or any(w.startswith(p) for p in INVALID_PREFIXES):
        return []

    in_compounds = list(split_word(saldo_lexicon, altlexicon, w, msd))

    if len(in_compounds) > SPLIT_LIMIT:
        return []

    out_compounds = []
    for comp in in_compounds:
        current_combinations = []

        # Get prefix analysis
        anap = saldo_lexicon.get_prefixes(comp[0])
        if not anap:
            anap = altlexicon.get_prefixes(comp[0])
        # Needs to be checked because of the three consonant rule
        if not anap:
            continue
        current_combinations.append(anap)

        # Get infix analyses
        for infix in comp[1:-1]:
            anai = saldo_lexicon.get_infixes(infix)
            if not anai:
                anai = altlexicon.get_prefixes(infix)
            if not anai:
                continue
            current_combinations.append(anai)

        # Get suffix analysis
        anas = saldo_lexicon.get_suffixes(comp[-1], msd)
        if not anas:
            anas = altlexicon.get_suffixes(comp[-1], msd)
        if not anas:
            continue
        current_combinations.append(anas)

        if deep_len(current_combinations) > COMP_LIMIT:
            continue

        # Check if all parts got an analysis
        if len(current_combinations) == len(comp):
            out_compounds.append(list(set(itertools.product(*current_combinations))))

    return out_compounds


def make_complem_and_compwf(
    complemgramfmt: str, compounds: list[tuple[float, tuple[tuple, ...]]], compdelim: str, delimiter: str, affix: str
) -> tuple[str, str]:
    """Return a list of compound lemgrams and a list of compound wordforms.

    Args:
        complemgramfmt: Format string for how to format the probability of the complemgram.
        compounds: A list of compounds to process.
        compdelim: Delimiter used between parts of the compound in the output annotations.
        delimiter: Delimiter used between values in the output annotations.
        affix: Affix used in the output annotations.

    Returns:
        A tuple containing the list of compound lemgrams and the list of compound wordforms, both in the form of a
            CWB set.
    """
    complem_list = []
    compwf_list = []
    for probcomp in compounds:
        prob, comp = probcomp
        complems = True
        for a in comp:
            if a[1] == "0":  # This part of the compound comes from the source text and has no lemgram
                complems = False
                break
        if complems:
            if complemgramfmt:
                # Construct complemgram + lemprob
                complem_list.append(compdelim.join(affix[1] for affix in comp) + complemgramfmt % prob)
            else:
                complem_list.append(compdelim.join(affix[1] for affix in comp))

        # If the first letter is uppercase, check if one of the affixes may be a name
        if comp[0][0][0].isupper():
            if not any([True for a in comp if "pm" in a[1][a[1].find(".") :]] + [True for a in comp if "PM" in a[2]]):
                wf = compdelim.join(affix[0].lower() for affix in comp)
            else:
                wf = compdelim.join(affix[0] for affix in comp)
        else:
            wf = compdelim.join(affix[0] for affix in comp)

        if wf not in compwf_list:
            compwf_list.append(wf)

    return (
        util.misc.cwbset(complem_list, delimiter, affix) if compounds and complem_list else affix,
        util.misc.cwbset(compwf_list, delimiter, affix) if compounds else affix,
    )


def make_new_baseforms(
    msd_tag: str,
    compounds: list[tuple],
    stats_lexicon: StatsLexicon,
    altlexicon: InFileLexicon,
    delimiter: str,
    affix: str,
) -> str:
    """Return a list of baseforms based on the compounds.

    Args:
        msd_tag: The MSD tag for the word.
        compounds: A list of compounds to process.
        stats_lexicon: The statistics lexicon to use for baseform lookup.
        altlexicon: Lexicon for words within the source file.
        delimiter: Delimiter used between values in the result.
        affix: Affix used in the result.

    Returns:
        A list of baseforms derived from the compounds, in the form string delimited by the specified delimiter.
    """
    baseform_list = []
    msd_tag = msd_tag[: msd_tag.find(".")]
    for probcomp in compounds:
        comp = probcomp[1]

        base_suffix = comp[-1][0] if comp[-1][1] == "0" else comp[-1][1][: comp[-1][1].find(".")]
        prefix = comp[0][0]
        # If first letter has upper case, check if one of the affixes is a name:
        if prefix[0] == prefix[0].upper():
            if not any(True for a in comp if "pm" in a[1][a[1].find(".") :]):
                baseform = "".join(affix[0].lower() for affix in comp[:-1]) + base_suffix
            else:
                baseform = "".join(affix[0] for affix in comp[:-1]) + base_suffix
        else:
            baseform = "".join(affix[0] for affix in comp[:-1]) + base_suffix

        # Check if this baseform with the MSD tag occurs in stats_lexicon
        if baseform not in baseform_list and (
            stats_lexicon.lookup_word_tag_freq(baseform, msd_tag) > 0 or altlexicon.lookup(baseform.lower()) != []
        ):
            baseform_list.append(baseform)

    return util.misc.cwbset(baseform_list, delimiter, affix) if (compounds and baseform_list) else affix


def read_lmf(xml: pathlib.Path, tagset: str = "SUC") -> dict:
    """Read the XML version of SALDO's morphological lexicon (saldom.xml).

    Args:
        xml: Path to the XML file.
        tagset: The tagset to use for mapping.

    Returns:
        A dictionary containing the lexicon entries.
    """
    tagmap = tagmappings.mappings["saldo_to_" + tagset.lower() + "_compound"]
    logger.info("Reading XML lexicon")
    lexicon = {}

    context = etree.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == "LexicalEntry":
                pos = elem.findtext("pos")
                lem = elem.findtext("lem")
                table = elem.find("table")
                inhs = elem.findtext("inhs")
                if inhs == "-":
                    inhs = ""
                inhs = inhs.split()

                for form in list(table):
                    word = form.findtext("wf")
                    param = form.findtext("param")

                    if not param[-1].isdigit() and param != "frag":
                        # and (param in ("c", "ci") or (pos in ("nn", "vb", "av", "ab") or pos[-1] == "h")):
                        saldotag = " ".join([pos, *inhs, param])
                        tags = tagmap.get(saldotag)

                        lexicon.setdefault(word, {}).setdefault(lem, {"msd": set()})["msd"].add(param)
                        lexicon[word][lem]["pos"] = pos
                        if tags:
                            lexicon[word][lem].setdefault("tags", set()).update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in {"LexicalEntry", "frame", "resFrame"}:
                root.clear()

    logger.info("OK, read")
    return lexicon


def save_to_picklefile(saldofile: pathlib.Path, lexicon: dict, protocol: int = -1, verbose: bool = True) -> None:
    """Save a Saldo lexicon to a Pickled file.

    The input lexicon should be a dict:
      - lexicon = {wordform: {lemgram: {"msd": set(), "pos": str}}}

    Args:
        saldofile: Path to the output Pickle file.
        lexicon: The lexicon to save.
        protocol: Pickle protocol version (default is -1, which uses the highest available).
        verbose: Whether to print progress messages.
    """
    if verbose:
        logger.info("Saving Saldo lexicon in Pickle format")

    picklex = {}
    for word in lexicon:  # noqa: PLC0206
        lemgrams = []

        for lemgram, annotation in lexicon[word].items():
            msds = PART_DELIM2.join(annotation["msd"])
            tags = PART_DELIM2.join(annotation.get("tags", []))
            lemgrams.append(PART_DELIM1.join([lemgram, msds, annotation["pos"], tags]))

        picklex[word] = sorted(lemgrams)

    with saldofile.open("wb") as f:
        pickle.dump(picklex, f, protocol=protocol)
    if verbose:
        logger.info("OK, saved")
