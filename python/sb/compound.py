# -*- coding: utf-8 -*-

import cPickle as pickle
import util
import itertools
from math import log


def annotate(out_complemgrams, out_compwf, out_baseform, word, msd, baseform_tmp, saldo_comp_model, nst_model, stats_model, delimiter="|", compdelim="+", affix="|", lexicon=None, stats_lexicon=None):
    """Divides compound words into prefix(es) and suffix.
    - out_complemgram is the resulting annotation file for compound lemgrams
    - out_compwf is the resulting annotation file for compound wordforms
    - out_baseform is the resulting annotation file for baseforms (including baseforms for compounds)
    - word and msd are existing annotations for wordforms and MSDs
    - baseform_tmp is the existing temporary annotation file for baseforms (not including compounds)
    - saldo_comp_model is the Saldo compound model
    - nst_model is the NST part of speech compound model
    - stats_model is the statistics model (pickled file)
    - lexicon, stats_lexicon: these argument cannot be set from the command line,
      but are used in the catapult. These arguments must be last.
    """

    ## load models ##
    if not lexicon:
        saldo_comp_lexicon = SaldoCompLexicon(saldo_comp_model)

    with open(nst_model, "r") as f:
        nst_model = pickle.load(f)

    if not stats_lexicon:
        stats_lexicon = StatsLexicon(stats_model)

    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)

    # create alternative lexicon (for words within the file)
    altlexicon = InFileLexicon(WORD, MSD)

    ## do annotation ##
    OUT_complem = {}
    OUT_compwf = {}
    OUT_baseform = {}
    IN_baseform = util.read_annotation(baseform_tmp)

    for tokid in WORD:
        compounds = compound(saldo_comp_lexicon, altlexicon, WORD[tokid], MSD[tokid])

        if compounds:
            compounds = rank_compounds(compounds, nst_model, stats_lexicon)

        # create complem and compwf annotations
        make_complem_and_compwf(OUT_complem, OUT_compwf, tokid, compounds, compdelim, delimiter, affix)
        
        # create new baseform annotation if necessary
        if IN_baseform[tokid] != affix:
            OUT_baseform[tokid] = IN_baseform[tokid]
        else:
            make_new_baseforms(OUT_baseform, tokid, MSD[tokid], compounds, stats_lexicon, altlexicon, delimiter, affix)


    util.write_annotation(out_complemgrams, OUT_complem)
    util.write_annotation(out_compwf, OUT_compwf)
    util.write_annotation(out_baseform, OUT_baseform)


class StatsLexicon(object):
    """A lexicon for probabilities of word forms and their POS tags.
    It is initialized from a pickled file.
    """
    def __init__(self, stats_model, verbose=True):
        if verbose:
            util.log.info("Reading statistics model: %s", stats_model)
        with open(stats_model, "r") as s:
            self.lexicon = pickle.load(s)
        if verbose:
            util.log.info("Done")

    def lookup_prob(self, word):
        return self.lexicon.prob(word)

    def lookup_word_tag_freq(self, word, tag):
        return self.lexicon.freqdist()[(word, tag)]


class SaldoCompLexicon(object):
    """A lexicon for Saldo compound lookups.
    It is initialized from a Pickled file.
    """
    def __init__(self, saldofile, verbose=True):
        if verbose:
            util.log.info("Reading Saldo lexicon: %s", saldofile)
        with open(saldofile, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            util.log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, word):
        """Lookup a word in the lexicon."""
        if word.lower() == word:
            annotation_tag_pairs = self.lexicon.get(word, [])
        else:
            annotation_tag_pairs = self.lexicon.get(word, []) + self.lexicon.get(word.lower(), [])
        return map(_split_triple, annotation_tag_pairs)

    def get_prefixes(self, prefix):
        return [(prefix, p[0], tuple(p[3])) for p in self.lookup(prefix) if 
            set(p[1]).intersection(set(["c", "ci", "cm"])) and p[2] != "ppa"]

    def get_suffixes(self, suffix, msd=None):
        return [(suffix, s[0], tuple(s[3])) for s in self.lookup(suffix)
                if (s[2] in ("nn", "vb", "av") or s[2][-1] == "h")
                and set(s[1]).difference(set(["c", "ci", "cm", "sms"]))
                and (msd in s[3] or not msd or [partial for partial in s[3] if partial.startswith(msd[:msd.find(".")])])
                ]


class InFileLexicon(object):
    """A dictionary of all words occuring in the input file.
    keys = words, values =  MSD tags
    """
    def __init__(self, word, msd):
        lex = {}
        for tokid in word:
            w = word[tokid].lower()
            # skip words consisting of a single letter (saldo should take care of these)
            if len(w) > 1:
                lex[w] = lex.get(w, set())
                pos = msd[tokid][:msd[tokid].find(".")] if msd[tokid][:msd[tokid].find(".")] != -1 else msd[tokid]
                lex[w].add((w, pos))
        self.lexicon = lex

    def lookup(self, word):
        """Lookup a word in the lexicon."""
        return list(self.lexicon.get(word, []))

    def get_prefixes(self, prefix):
        return [(prefix, '0', (s[1],)) for s in self.lookup(prefix.lower())]

    def get_suffixes(self, suffix, msd=None):
        return [(suffix, '0', (s[1],)) for s in self.lookup(suffix.lower())
                if (s[1][0:2] in ("NN", "VB", "AV", "AB"))
                and (not msd or msd in s[1] or s[1].startswith(msd[:msd.find(".")]))
                ]


def split_word(saldo_lexicon, altlexicon, w):
    """Split word w into every possible combination of substrings."""
    invalid_spans = set()
    valid_spans = set()
    # Create list of possible splitpoint indices for w
    nsplits = range(1, len(w))

    for n in nsplits:
        first = True
        nn = len(nsplits)
        indices = range(n)

        # Similar to itertools.combinations, but customized for our needs
        while True:
            if first:
                first = False
            else:
                for i in reversed(range(n)):
                    if indices[i] != i + nn - n:
                        break
                else:
                    break
                indices[i] += 1
                for j in range(i+1, n):
                    indices[j] = indices[j-1] + 1

            splitpoint = tuple(i+1 for i in indices)

            # Create list of affix spans
            spans = zip((0,) + splitpoint, splitpoint + (None,))

            # Abort if current compound contains an affix known to be invalid
            abort = False
            for ii, s in enumerate(spans):
                if s in invalid_spans:
                    if not s[1] is None:
                        # Skip any combination of spans following the invalid span
                        for j in range(ii+1, n):
                            indices[j] = j + nn - n
                    abort = True
                    break
            if abort:
                continue

            # expand prefixes if possible
            comps = three_consonant_rule([w[i:j] for i, j in spans])
            for comp in comps:
                # Have we analyzed this suffix yet?
                if not spans[-1] in valid_spans:
                    # Is there a possible suffix analysis?
                    if exception(comp[-1]) or not (saldo_lexicon.get_suffixes(comp[-1]) or altlexicon.get_suffixes(comp[-1])):
                        invalid_spans.add(spans[-1])
                        continue
                    else:
                        valid_spans.add(spans[-1])

                for k, affix in enumerate(comp[:-1]):
                    # Have we analyzed this affix yet?
                    if not spans[k] in valid_spans:
                        if not (saldo_lexicon.get_prefixes(affix) or altlexicon.get_prefixes(affix)):
                            invalid_spans.add(spans[k])
                            comp = None
                            # Skip any combination of spans following the invalid span
                            for j in range(k+1, n):
                                indices[j] = j + nn - n
                            break
                        else:
                            valid_spans.add(spans[k])

                if comp:
                    yield comp


def exception(w):
    """ Filter out unwanted suffixes. """
    return w in [
        "il", u"ör", "en", "ens", "ar", "ars",
        "or", "ors", "ur", "urs", u"lös", "tik", "bar",
        "lik", "het", "hets", "lig", "ligt", "te", "tet", "tets",
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l",
        "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x",
        "y", "z", u"ä"]


def three_consonant_rule(compound):
    """ Expand prefix if its last letter == first letter of suffix.
    ("glas", "skål") --> ("glas", "skål"), ("glass", "skål") """
    combinations = []
    suffix = compound[len(compound)-1]
    for index in range(len(compound)-1):
        current_prefix = compound[index]
        current_suffix = compound[index+1]
        # last prefix letter == first suffix letter; and prefix ends in one of "bdfgjlmnprstv"
        if current_prefix[-1] in "bdfgjlmnprstv" and current_prefix[-1] == current_suffix[0]:
            combinations.append((current_prefix, current_prefix + current_prefix[-1]))
        else:
            combinations.append((current_prefix, current_prefix))
    combinations.append((suffix, suffix))
    return [list(i) for i in list(set(itertools.product(*combinations)))]


def rank_compounds(compounds, nst_model, stats_lexicon):
    """Return a list of compounds, ordered according to their ranks.
    Ranking is being done according to the amount of affixes (the fewer the higher)
    and the compound probability which is calculated as follows:
    p((w1,tag1)..(wn,tag1)) = p(w1,tag1) ... * p(wn,tagn) * p(tag1, ...tagn)
    t.ex. p(clown+bil) = p(clown, NN) * p(bil, NN) * p(NN,NN) 
    """
    ranklist = []
    for clist in compounds:
        affixes = [affix[0] for affix in clist[0]]
        for c in clist:
            tags = list(itertools.product(*[affix[2] for affix in c]))
            # calculate log probability score
            word_probs = max(sum([log(stats_lexicon.lookup_prob(i)) for i in zip(affixes, t)]) for t in tags)
            tag_prob = max(log(nst_model.prob('+'.join(t))) for t in tags)
            score = word_probs + tag_prob
            ranklist.append((score, c))
    ranklist = sorted(ranklist, key=lambda x: x[0], reverse=True)
    # sort according to length
    ranklist = sorted(ranklist, key=lambda x: len(x[1]))
    ranklist = [c for _r, c in ranklist]
    return ranklist


def compound(saldo_lexicon, altlexicon, w, msd=None):
    """Create a list of compound analyses for word w."""
    in_compounds = [i for i in split_word(saldo_lexicon, altlexicon, w)]
    out_compounds = []
    for comp in in_compounds:
        current_combinations = []
        # get prefix analysis for every affix
        for affix in comp[:len(comp)-1]:
            anap = saldo_lexicon.get_prefixes(affix)
            if not anap:
                anap = altlexicon.get_prefixes(affix)
            if len(anap) == 0:
                break
            current_combinations.append(anap)
        # get suffix analysis for suffix
        anas = saldo_lexicon.get_suffixes(comp[len(comp)-1], msd)
        if not anas:
            anas = altlexicon.get_suffixes(comp[len(comp)-1], msd)
        # check if every affix in comp has an analysis
        if len(current_combinations) == len(comp)-1 and len(anas) > 0:
            current_combinations.append(anas)
            out_compounds.append(list(set(itertools.product(*current_combinations))))
    return out_compounds


def make_complem_and_compwf(OUT_complem, OUT_compwf, tokid, compounds, compdelim, delimiter, affix):
    """Add a list of compound lemgrams to the dictionary OUT_complem[tokid]
    and a list of compound wordforms to OUT_compwf."""
    complem_list = []
    compwf_list = []
    complems = True
    for comp in compounds:
        for a in comp:
            if a[1] == '0':
                complems = False
                break
        if complems:
            complem_list.append(compdelim.join(affix[1] for affix in comp))

        # if first letter has upper case, check if one of the affixes may be a name:
        first_letter = comp[0][0][0]
        if first_letter == first_letter.upper():
            if sum(1 for a in comp if "pm" in a[1][a[1].find('.'):]) + sum(1 for a in comp if "PM" in a[2]) == 0:
                first_letter = first_letter.lower()
        prefix = first_letter + comp[0][0][1:]
        wf = prefix + compdelim + compdelim.join(affix[0] for affix in comp[1:])
        if wf not in compwf_list:
            compwf_list.append(wf)

    # update dictionaries
    OUT_complem[tokid] = affix + delimiter.join(complem_list) + affix if compounds and complem_list else affix
    OUT_compwf[tokid] = affix + delimiter.join(compwf_list) + affix if compounds else affix


def make_new_baseforms(OUT_baseform, tokid, msd_tag, compounds, stats_lexicon, altlexicon, delimiter, affix):
    """Add a list of baseforms to the dictionary OUT_baseform[tokid]."""
    baseform_list = []
    msd_tag = msd_tag[:msd_tag.find('.')]
    for comp in compounds:
        base_suffix = comp[-1][1][:comp[-1][1].find('.')]
        prefix = comp[0][0]
        # if first letter has upper case, check if one of the affixes is a name:
        if prefix[0] == prefix[0].upper():
            if sum([1 for a in comp if "pm" in a[1][a[1].find('.'):]]) == 0:
                prefix = prefix[0].lower() + prefix[1:]
        baseform = prefix + ''.join(affix[0] for affix in comp[1:-1]) + base_suffix

        # check if this baseform with the MSD tag occurs in stats_lexicon
        if baseform not in baseform_list:
            if stats_lexicon.lookup_word_tag_freq(baseform, msd_tag) > 0 or altlexicon.lookup(baseform.lower()) != []:
                baseform_list.append(baseform)

    # update dictionary
    OUT_baseform[tokid] = affix + delimiter.join(baseform_list) \
        + affix if (compounds and baseform_list) else affix


def read_xml(xml='saldom.xml', tagset="SUC"):
    """Read the XML version of SALDO's morphological lexicon (saldom.xml).
    """
    import xml.etree.cElementTree as cet
    tagmap = getattr(util.tagsets, "saldo_to_" + tagset.lower())
    util.log.info("Reading XML lexicon")
    lexicon = {}

    context = cet.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = context.next()

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':

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

                    if not param[-1].isdigit() and not param == "frag": #and (param in ("c", "ci") or (pos in ("nn", "vb", "av", "ab") or pos[-1] == "h")):

                        saldotag = " ".join([pos] + inhs + [param])
                        tags = tagmap.get(saldotag)

                        lexicon.setdefault(word, {}).setdefault(lem, {"msd": set()})["msd"].add(param)
                        lexicon[word][lem]["pos"] = pos
                        if tags:
                            lexicon[word][lem].setdefault("tags", set()).update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ['LexicalEntry', 'frame', 'resFrame']:
                root.clear()

    util.log.info("OK, read")
    return lexicon


PART_DELIM1 = "^1"
PART_DELIM2 = "^2"
PART_DELIM3 = "^3"


def save_to_picklefile(saldofile, lexicon, protocol=1, verbose=True):
    """Save a Saldo lexicon to a Pickled file.
    The input lexicon should be a dict:
      - lexicon = {wordform: {lemgram: {"msd": set(), "pos": str}}}
    """
    if verbose:
        util.log.info("Saving Saldo lexicon in Pickle format")

    picklex = {}
    for word in lexicon:
        lemgrams = []

        for lemgram, annotation in lexicon[word].items():
            msds = PART_DELIM2.join(annotation["msd"])
            tags = PART_DELIM2.join(annotation.get("tags", []))
            lemgrams.append(PART_DELIM1.join([lemgram, msds, annotation["pos"], tags]))

        picklex[word] = sorted(lemgrams)

    with open(saldofile, "wb") as F:
        pickle.dump(picklex, F, protocol=protocol)
    if verbose:
        util.log.info("OK, saved")


def _split_triple(annotation_tag_words):
    lemgram, msds, pos, tags = annotation_tag_words.split(PART_DELIM1)
    msds = msds.split(PART_DELIM2)
    tags = tags.split(PART_DELIM2)
    tags = list(set([t[:t.find(".")] if t.find(".") != -1 else t for t in tags]))
    return lemgram, msds, pos, tags


def xml_to_pickle(xml, filename):
    """Read an XML dictionary and save as a pickle file."""
    xml_lexicon = read_xml(xml)
    save_to_picklefile(filename, xml_lexicon)

######################################################################

if __name__ == '__main__':
    util.run.main(annotate, xml_to_pickle=xml_to_pickle)
