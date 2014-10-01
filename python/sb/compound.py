# -*- coding: utf-8 -*-

import cPickle as pickle
import util
import itertools


def annotate(out_complemgram, out_compwf, word, msd, model, delimiter="|", compdelim="+", affix="|", lexicon=None):
    """Divides compound words into prefix(es) and suffix.
    - out_complemgram is the resulting annotation file for compound lemgrams
    - out_compwf is the resulting annotation file for compound wordforms
    - word and msd are existing annotations for wordforms and MSDs
    - model is the Saldo compound model
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. this argument must be last
    """

    if not lexicon:
        saldo_lexicon = SaldoLexicon(model)

    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)

    # create alternative lexicon (for words within the file)
    altlexicon = InFileLexicon(WORD, MSD)

    OUT_complem = {}
    OUT_compwf = {}

    for tokid in WORD:
        compounds = compound(saldo_lexicon, altlexicon, WORD[tokid], MSD[tokid])
        # compounds = list of saldo compound lists which contain compound tuples; e.g. glasskål:
        # [[(('glas', 'glas..nn.1'), ('skål', 'skål..nn.1')), (('glas', 'glasa..vb.1'), ('skål', 'skål..nn.1'))], ...]
        complem_list = []
        compwf_list = []
        for comp_list in compounds:
            complems = True
            for comp in comp_list:
                for a in comp:
                    if a[1] == 0:
                        complems = False
                        break
                if complems:
                    complem_list.append(compdelim.join(affix[1] for affix in comp))

            compwf_list.append(compdelim.join(affix[0] for affix in comp_list[0]))

        OUT_complem[tokid] = affix + delimiter.join(complem_list) + affix if compounds and complem_list else affix
        OUT_compwf[tokid] = affix + delimiter.join(compwf_list) + affix if compounds else affix

    util.write_annotation(out_complemgram, OUT_complem)
    util.write_annotation(out_compwf, OUT_compwf)


class InFileLexicon(object):
    """A dictionary of all words occuring in the input file.
    keys = words, values =  MSD tags
    """
    def __init__(self, word, msd):
        lex = {}
        for tokid in word:
            w = word[tokid].lower()
            # skip words consisting of a single letter (saldo takes care of these)
            if len(w) > 1:
                lex[w] = lex.get(w, set())
                lex[w].add((w, msd[tokid]))
        self.lexicon = lex

    def lookup(self, word):
        """Lookup a word in the lexicon."""
        return list(self.lexicon.get(word, []))

    def get_prefixes(self, prefix):
        return [(prefix, 0) for s in self.lookup(prefix.lower())]

    def get_suffixes(self, suffix, msd=None):
        return [(suffix, 0) for s in self.lookup(suffix.lower())
                if (s[1][0:2] in ("NN", "VB", "AV", "AB"))
                and (not msd or msd in s[1] or s[1].startswith(msd[:msd.find(".")]))
                ]


class SaldoLexicon(object):
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
        return [(prefix, p[0]) for p in self.lookup(prefix) if set(p[1]).intersection(set(["c", "ci"]))]

    def get_suffixes(self, suffix, msd=None):
        return [(suffix, s[0]) for s in self.lookup(suffix)
                if (s[2] in ("nn", "vb", "av", "ab") or s[2][-1] == "h")
                and set(s[1]).difference(set(["c", "ci", "cm", "sms"]))
                and (msd in s[3] or not msd or [partial for partial in s[3] if partial.startswith(msd[:msd.find(".")])])
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

            comp = [w[i:j] for i, j in spans]

            # Have we analyzed this suffix yet?
            if not spans[-1] in valid_spans:
                if not has_suffix_analysis(saldo_lexicon, altlexicon, comp[-1]):
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


def has_suffix_analysis(saldo_lexicon, altlexicon, suffix):
    """Check if suffix has a valid analysis in saldo."""
    # check if suffix is not an exeption
    return not exception(suffix) and (saldo_lexicon.get_suffixes(suffix) or altlexicon.get_suffixes(suffix))


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
    for index in range(len(compound)-1):
        current_prefix = compound[index]
        current_suffix = compound[index+1]
        # last prefix letter == first suffix letter; and prefix ends in one of "bdfgjlmnprstv"
        if current_prefix[-1] == current_suffix[0] and current_prefix[-1] in "bdfgjlmnprstv":
            combinations.append((current_prefix, current_prefix + current_prefix[-1]))
        else:
            combinations.append((current_prefix, current_prefix))
    suffix = compound[len(compound)-1]
    combinations.append((suffix, suffix))
    # return a list of all possible affix combinations
    return list(set(itertools.product(*combinations)))


def compound(saldo_lexicon, altlexicon, w, msd=None):
    """Create a list of compound analyses for word w."""
    in_compounds = [i for i in split_word(saldo_lexicon, altlexicon, w)]
    out_compounds = []
    for _comp in in_compounds:
        # expand prefixes if possible
        for comp in three_consonant_rule(_comp):
            current_combinations = []
            # get prefix analysis for every affix
            for affix in comp[:len(comp)-1]:
                anap = saldo_lexicon.get_prefixes(affix) + altlexicon.get_prefixes(affix)
                if len(anap) == 0:
                    break
                current_combinations.append(anap)
            # get suffix analysis for suffix
            anas = saldo_lexicon.get_suffixes(comp[len(comp)-1], msd)
            # check if every affix in comp has an analysis
            if len(current_combinations) < len(comp)-1 or len(anas) == 0:
                break
            current_combinations.append(anas)
            out_compounds.append(list(itertools.product(*current_combinations)))
    return out_compounds


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

                    if not param[-1].isdigit() and not param == "frag" and (param in ("c", "ci") or (pos in ("nn", "vb", "av", "ab") or pos[-1] == "h")):

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
    return lemgram, msds, pos, tags


def xml_to_pickle(xml, filename):
    """Read an XML dictionary and save as a pickle file."""

    xml_lexicon = read_xml(xml)
    save_to_picklefile(filename, xml_lexicon)

######################################################################

if __name__ == '__main__':
    util.run.main(annotate, xml_to_pickle=xml_to_pickle)
