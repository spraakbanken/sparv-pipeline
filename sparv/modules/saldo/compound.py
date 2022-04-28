"""Compound analysis."""

import itertools
import pathlib
import pickle
import re
import time
import xml.etree.ElementTree as etree
from functools import reduce

from sparv.api import Annotation, Config, Model, ModelOutput, Output, annotator, get_logger, modelbuilder, util
from sparv.api.util.tagsets import tagmappings

logger = get_logger(__name__)

MAX_WORD_LEN = 75
SPLIT_LIMIT = 200
COMP_LIMIT = 100
INVALID_PREFIXES = ("http:", "https:", "www.")
INVALID_REGEX = re.compile(r"(..?)\1{3}")

# SALDO: Delimiters that hopefully are never found in an annotation or in a POS tag:
PART_DELIM = "^"
PART_DELIM1 = "^1"
PART_DELIM2 = "^2"
PART_DELIM3 = "^3"


def preloader(saldo_comp_model, stats_model):
    """Preload models."""
    return SaldoCompLexicon(saldo_comp_model.path), StatsLexicon(stats_model.path)


@annotator("Compound analysis", name="compound", language=["swe"], config=[
    Config("saldo.comp_model", default="saldo/saldo.compound.pickle", description="Path to SALDO compound model"),
    Config("saldo.comp_nst_model", default="saldo/nst_comp_pos.pickle",
           description="Path to NST part of speech compound model"),
    Config("saldo.comp_stats_model", default="saldo/stats.pickle", description="Path to statistics model"),
    Config("saldo.comp_use_source", default=True, description="Also use source text as lexicon for compound analysis")
], preloader=preloader, preloader_params=["saldo_comp_model", "stats_model"], preloader_target="preloaded_models")
def annotate(out_complemgrams: Output = Output("<token>:saldo.complemgram",
                                               description="Compound analysis using lemgrams"),
             out_compwf: Output = Output("<token>:saldo.compwf", description="Compound analysis using wordforms"),
             out_baseform: Output = Output("<token>:saldo.baseform2",
                                           description="Baseform including baseforms derived from compounds"),
             word: Annotation = Annotation("<token:word>"),
             msd: Annotation = Annotation("<token:msd>"),
             baseform_tmp: Annotation = Annotation("<token>:saldo.baseform"),
             saldo_comp_model: Model = Model("[saldo.comp_model]"),
             nst_model: Model = Model("[saldo.comp_nst_model]"),
             stats_model: Model = Model("[saldo.comp_stats_model]"),
             comp_use_source: bool = Config("saldo.comp_use_source"),
             complemgramfmt: str = util.constants.SCORESEP + "%.3e",
             delimiter: str = util.constants.DELIM,
             compdelim: str = util.constants.COMPSEP,
             affix: str = util.constants.AFFIX,
             cutoff: bool = True,
             preloaded_models=None):
    """Divide compound words into prefix(es) and suffix.

    - out_complemgram is the resulting annotation file for compound lemgrams
      and their probabilities
    - out_compwf is the resulting annotation file for compound wordforms
    - out_baseform is the resulting annotation file for baseforms (including baseforms for compounds)
    - word and msd are existing annotations for wordforms and MSDs
    - baseform_tmp is the existing temporary annotation file for baseforms (not including compounds)
    - saldo_comp_model is the Saldo compound model
    - nst_model is the NST part of speech compound model
    - stats_model is the statistics model (pickled file)
    - complemgramfmt is a format string for how to print the complemgram and its probability
      (use empty string to omit probablility)
    - preloaded_models: Preloaded models if using preloader
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

    with open(nst_model.path, "rb") as f:
        nst_model = pickle.load(f)

    word_msd_baseform_annotations = list(word.read_attributes((word, msd, baseform_tmp)))
    logger.progress(total=len(word_msd_baseform_annotations) + 3)

    # Create alternative lexicon (for words within the source file)
    altlexicon = InFileLexicon(word_msd_baseform_annotations if comp_use_source else [])

    ##################
    # Do annotation
    ##################
    complem_annotation = []
    compwf_annotation = []
    baseform_annotation = []

    previous_compounds = {}

    for word, msd, baseform_orig in word_msd_baseform_annotations:
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
        make_complem_and_compwf(complem_annotation, compwf_annotation, complemgramfmt, compounds, compdelim, delimiter,
                                affix)

        # Create new baseform annotation if necessary
        if baseform_orig != affix:
            baseform_annotation.append(baseform_orig)
        else:
            make_new_baseforms(baseform_annotation, msd, compounds, stats_lexicon, altlexicon, delimiter, affix)

        logger.progress()

    out_complemgrams.write(complem_annotation)
    logger.progress()
    out_compwf.write(compwf_annotation)
    logger.progress()
    out_baseform.write(baseform_annotation)
    logger.progress()


@modelbuilder("SALDO compound model", language=["swe"])
def build_saldo_comp(out: ModelOutput = ModelOutput("saldo/saldo.compound.pickle"),
                     saldom: Model = Model("saldo/saldom.xml")):
    """Extract compound info from saldom.xml and save as a pickle file."""
    xml_lexicon = read_lmf(saldom.path)
    save_to_picklefile(out.path, xml_lexicon)


class SaldoCompLexicon:
    """A lexicon for Saldo compound lookups.

    It is initialized from a Pickled file.
    """

    def __init__(self, saldofile: pathlib.Path, verbose=True):
        """Load lexicon."""
        if verbose:
            logger.info("Reading Saldo lexicon: %s", saldofile)
        with open(saldofile, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            logger.info("OK, read %d words", len(self.lexicon))

    def lookup(self, word):
        """Lookup a word in the lexicon."""
        if word.lower() == word:
            annotation_tag_pairs = self.lexicon.get(word, [])
        else:
            annotation_tag_pairs = self.lexicon.get(word, []) + self.lexicon.get(word.lower(), [])
        return list(map(self._split_triple, annotation_tag_pairs))

    def get_prefixes(self, prefix):
        """Get all possible prefixes."""
        return [(prefix, p[0], tuple(p[3])) for p in self.lookup(prefix) if
                set(p[1]).intersection({"c", "ci"})]

    def get_infixes(self, infix):
        """Get all possible infixes (= mid parts of a word)."""
        return [(infix, i[0], tuple(i[3])) for i in self.lookup(infix) if
                set(i[1]).intersection({"c", "cm"})]

    def get_suffixes(self, suffix, msd=None):
        """Get all possible suffixes."""
        return [(suffix, s[0], tuple(s[3])) for s in self.lookup(suffix)
                if (s[2] in ("nn", "vb", "av") or s[2][-1] == "h")
                and set(s[1]).difference({"c", "ci", "cm", "sms"})
                and (msd in s[3] or not msd or [partial for partial in s[3] if partial.startswith(msd[:msd.find(".")])])
                ]

    def _split_triple(self, annotation_tag_words):
        lemgram, msds, pos, tags = annotation_tag_words.split(PART_DELIM1)
        msds = msds.split(PART_DELIM2)
        tags = tags.split(PART_DELIM2)
        tags = list(set([t[:t.find(".")] if t.find(".") != -1 else t for t in tags]))
        return lemgram, msds, pos, tags


class StatsLexicon:
    """A lexicon for probabilities of word forms and their POS tags.

    It is initialized from a pickled file.
    """

    def __init__(self, stats_model: pathlib.Path, verbose=True):
        """Load lexicon."""
        if verbose:
            logger.info("Reading statistics model: %s", stats_model)
        with open(stats_model, "rb") as s:
            self.lexicon = pickle.load(s)
        if verbose:
            logger.info("Done")

    def lookup_prob(self, word):
        """Look up the probability of the word."""
        return self.lexicon.prob(word)

    def lookup_word_tag_freq(self, word, tag):
        """Look up frequency of this word-tag combination."""
        return self.lexicon.freqdist()[(word, tag)]


class InFileLexicon:
    """A dictionary of all words occurring in the input file.

    keys = words, values =  MSD tags
    """

    def __init__(self, annotations: list):
        """Create a lexicon for the words occurring in this file."""
        lex = {}
        for word, msd, _ in annotations:
            w = word.lower()
            # Skip words consisting of a single letter (SALDO should take care of these)
            # Also skip words consisting of two letters, to avoid an explosion of analyses
            if len(w) > 2:
                lex[w] = lex.get(w, set())
                pos = msd.split(".")[0]
                lex[w].add((w, pos))
        self.lexicon = lex

    def lookup(self, word):
        """Lookup a word in the lexicon."""
        return list(self.lexicon.get(word, []))

    def get_prefixes(self, prefix):
        """Get all possible prefixes."""
        return [(prefix, "0", (s[1],)) for s in self.lookup(prefix.lower())]

    def get_suffixes(self, suffix, msd=None):
        """Get all possible suffixes."""
        return [(suffix, "0", (s[1],)) for s in self.lookup(suffix.lower())
                if (s[1][0:2] in ("NN", "VB", "AV"))
                and (not msd or msd in s[1] or s[1].startswith(msd[:msd.find(".")]))
                ]


################################################################################
# Auxiliaries
################################################################################


def split_word(saldo_lexicon, altlexicon, w, msd):
    """Split word w into every possible combination of substrings."""
    MAX_ITERATIONS = 250000
    MAX_TIME = 20  # Seconds
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
                for i in reversed(list(range(n))):
                    if indices[i] != i + nn - n:
                        break
                else:
                    break
                indices[i] += 1
                for j in range(i + 1, n):
                    indices[j] = indices[j - 1] + 1

            splitpoint = tuple(i + 1 for i in indices)

            # Create list of affix spans
            spans = list(zip((0,) + splitpoint, splitpoint + (None,)))

            # Abort if current compound contains an affix known to be invalid
            abort = False
            for ii, s in enumerate(spans):
                if s in invalid_spans:
                    if not s[1] is None:
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
                    else:
                        if not (saldo_lexicon.get_prefixes(comp[0]) or altlexicon.get_prefixes(comp[0])):
                            invalid_spans.add(this_span)
                            if multicomp:
                                if all((spans[0], i) in invalid_spans for i in range(len(comps))):
                                    invalid_spans.add(spans[0])
                            continue
                        else:
                            valid_spans.add(this_span)

                # Check if suffix is valid
                this_span = (spans[-1], comp_i) if multicomp else spans[-1]
                if this_span not in valid_spans:
                    if this_span in invalid_spans:
                        continue
                    else:
                        # Is there a possible suffix analysis?
                        if exception(comp[-1]) or not (saldo_lexicon.get_suffixes(comp[-1], msd)
                                                       or altlexicon.get_suffixes(comp[-1], msd)):
                            invalid_spans.add(this_span)
                            if multicomp:
                                if all((spans[-1], i) in invalid_spans for i in range(len(comps))):
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
                        else:
                            if exception(infix) or not (saldo_lexicon.get_infixes(infix)
                                                        or altlexicon.get_prefixes(infix)):
                                invalid_spans.add(this_span)
                                if multicomp:
                                    if all((spans[k], i) in invalid_spans for i in range(len(comps))):
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
                    logger.info("Too many possible compounds for word '%s'" % w)
                    break
                yield comp

            if giveup:
                break
        if giveup:
            break


def exception(w):
    """Filter out unwanted suffixes."""
    return w.lower() in [
        "il", u"ör", "en", "ens", "ar", "ars",
        "or", "ors", "ur", "urs", u"lös", "tik", "bar",
        "lik", "het", "hets", "lig", "ligt", "te", "tet", "tets",
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l",
        "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x",
        "y", "z", u"ä"]


def three_consonant_rule(compound):
    """Expand each stem if its last letter equals the first letter of the following stem.

    ("glas", "skål") --> ("glas", "skål"), ("glass", "skål")
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


def rank_compounds(compounds, nst_model, stats_lexicon):
    """Return a list of compounds, ordered according to their ranks.

    Ranking is being done according to the amount of affixes (the fewer the higher)
    and the compound probability which is calculated as follows:

    p((w1, tag1)..(wn, tag1)) = p(w1, tag1) ... * p(wn, tagn) * p(tag1, ...tagn)
    e.g. p(clown+bil) = p(clown, NN) * p(bil, NN) * p(NN,NN)
    """
    ranklist = []
    for clist in compounds:
        affixes = [affix[0] for affix in clist[0]]
        for c in clist:
            tags = list(itertools.product(*[affix[2] for affix in c]))
            # Calculate probability score
            word_probs = max(
                reduce(lambda x, y: x * y, [(stats_lexicon.lookup_prob(i)) for i in zip(affixes, t)]) for t in tags)
            tag_prob = max(nst_model.prob("+".join(t)) for t in tags)
            score = word_probs * tag_prob
            ranklist.append((score, c))
    # Sort according to length and probability
    ranklist.sort(key=lambda x: (len(x[1]), -x[0], x[1]))
    return ranklist


def deep_len(lst):
    """Return the depth of a list."""
    return sum(deep_len(el) if isinstance(el, (list, tuple)) else 1 for el in lst)


def compound(saldo_lexicon, altlexicon, w, msd=None):
    """Create a list of compound analyses for word w."""
    if len(w) > MAX_WORD_LEN or INVALID_REGEX.search(w) or any(w.startswith(p) for p in INVALID_PREFIXES):
        return []

    in_compounds = list(split_word(saldo_lexicon, altlexicon, w, msd))

    if len(in_compounds) >= SPLIT_LIMIT:
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


def make_complem_and_compwf(out_complem, out_compwf, complemgramfmt, compounds, compdelim, delimiter, affix):
    """Add a list of compound lemgrams to out_complem and a list of compound wordforms to out_compwf."""
    complem_list = []
    compwf_list = []
    for comp in compounds:
        prob = comp[0]
        comp = comp[1]
        complems = True
        for a in comp:
            if a[1] == "0":
                complems = False
                break
        if complems:
            if complemgramfmt:
                # Construct complemgram + lemprob
                complem_list.append(compdelim.join(affix[1] for affix in comp) + complemgramfmt % prob)
            else:
                complem_list.append(compdelim.join(affix[1] for affix in comp))

        # If first letter has upper case, check if one of the affixes may be a name:
        if comp[0][0][0] == comp[0][0][0].upper():
            if not any([True for a in comp if "pm" in a[1][a[1].find("."):]] + [True for a in comp if "PM" in a[2]]):
                wf = compdelim.join(affix[0].lower() for affix in comp)
            else:
                wf = compdelim.join(affix[0] for affix in comp)
        else:
            wf = compdelim.join(affix[0] for affix in comp)

        if wf not in compwf_list:
            compwf_list.append(wf)

    # Add to annotations
    out_complem.append(util.misc.cwbset(complem_list, delimiter, affix) if compounds and complem_list else affix)
    out_compwf.append(util.misc.cwbset(compwf_list, delimiter, affix) if compounds else affix)


def make_new_baseforms(out_baseform, msd_tag, compounds, stats_lexicon, altlexicon, delimiter, affix):
    """Add a list of baseforms to the out_baseform."""
    baseform_list = []
    msd_tag = msd_tag[:msd_tag.find(".")]
    for comp in compounds:
        comp = comp[1]

        if comp[-1][1] == "0":
            base_suffix = comp[-1][0]
        else:
            base_suffix = comp[-1][1][:comp[-1][1].find(".")]
        prefix = comp[0][0]
        # If first letter has upper case, check if one of the affixes is a name:
        if prefix[0] == prefix[0].upper():
            if not any(True for a in comp if "pm" in a[1][a[1].find("."):]):
                baseform = "".join(affix[0].lower() for affix in comp[:-1]) + base_suffix
            else:
                baseform = "".join(affix[0] for affix in comp[:-1]) + base_suffix
        else:
            baseform = "".join(affix[0] for affix in comp[:-1]) + base_suffix

        # Check if this baseform with the MSD tag occurs in stats_lexicon
        if baseform not in baseform_list:
            if stats_lexicon.lookup_word_tag_freq(baseform, msd_tag) > 0 or altlexicon.lookup(baseform.lower()) != []:
                baseform_list.append(baseform)

    # Add to annotation
    out_baseform.append(util.misc.cwbset(baseform_list, delimiter, affix) if (compounds and baseform_list) else affix)


def read_lmf(xml: pathlib.Path, tagset: str = "SUC"):
    """Read the XML version of SALDO's morphological lexicon (saldom.xml)."""
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

                    if not param[-1].isdigit() and not param == "frag":  # and (param in ("c", "ci") or (pos in ("nn", "vb", "av", "ab") or pos[-1] == "h")):
                        saldotag = " ".join([pos] + inhs + [param])
                        tags = tagmap.get(saldotag)

                        lexicon.setdefault(word, {}).setdefault(lem, {"msd": set()})["msd"].add(param)
                        lexicon[word][lem]["pos"] = pos
                        if tags:
                            lexicon[word][lem].setdefault("tags", set()).update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ["LexicalEntry", "frame", "resFrame"]:
                root.clear()

    logger.info("OK, read")
    return lexicon


def save_to_picklefile(saldofile, lexicon, protocol=-1, verbose=True):
    """Save a Saldo lexicon to a Pickled file.

    The input lexicon should be a dict:
      - lexicon = {wordform: {lemgram: {"msd": set(), "pos": str}}}
    """
    if verbose:
        logger.info("Saving Saldo lexicon in Pickle format")

    picklex = {}
    for word in lexicon:
        lemgrams = []

        for lemgram, annotation in list(lexicon[word].items()):
            msds = PART_DELIM2.join(annotation["msd"])
            tags = PART_DELIM2.join(annotation.get("tags", []))
            lemgrams.append(PART_DELIM1.join([lemgram, msds, annotation["pos"], tags]))

        picklex[word] = sorted(lemgrams)

    with open(saldofile, "wb") as F:
        pickle.dump(picklex, F, protocol=protocol)
    if verbose:
        logger.info("OK, saved")
