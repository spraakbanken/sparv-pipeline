# -*- coding: utf-8 -*-
import pickle
import sparv.util as util


def annotate(out_prefix, out_suffix, word, msd, model, delimiter="|", affix="|", lexicon=None):
    """Divides compound words into prefix and suffix.
    - out_prefix is the resulting annotation file for prefixes
    - out_suffix is the resulting annotation file for suffixes
    - word and msd are existing annotations for wordforms and MSDs
    - model is the Saldo compound model
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. this argument must be last
    """

    if not lexicon:
        lexicon = SaldoLexicon(model)

    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)

    OUT_p = {}
    OUT_s = {}

    for tokid in WORD:
        compounds = compound(lexicon, WORD[tokid], MSD[tokid])
        OUT_p[tokid] = affix + delimiter.join(set(c[0][1] for c in compounds)) + affix if compounds else affix
        OUT_s[tokid] = affix + delimiter.join(set(c[1][1] for c in compounds)) + affix if compounds else affix

    util.write_annotation(out_prefix, OUT_p)
    util.write_annotation(out_suffix, OUT_s)


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
        return list(map(_split_triple, annotation_tag_pairs))

    def get_prefixes(self, prefix):
        return [ (prefix, p[0]) for p in self.lookup(prefix) if set(p[1]).intersection(set(["c", "ci"])) ]

    def get_suffixes(self, suffix, msd=None):
        return [ (suffix, s[0]) for s in self.lookup(suffix)
                if (s[2] in ("nn", "vb", "av", "ab") or s[2][-1] == "h")
                and set(s[1]).difference(set(["c", "ci", "cm", "sms"]))
                and (msd in s[3] or not msd or [partial for partial in s[3] if partial.startswith(msd[:msd.find(".")])])
                ]


def prefixes_suffixes(w):
    """ Split a word into every possible prefix-suffix pair. """
    return [(w[:i], w[i:]) for i in range(1, len(w))]


def exception(w):
    """ Filter out unwanted suffixes. """
    return w in [
        "il", u"ör", "en", "ens", "ar", "ars",
        "or", "ors", "ur", "urs", u"lös", "tik", "bar",
        "lik", "het", "hets", "lig", "ligt", "te", "tet", "tets",
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l",
        "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x",
        "y", "z", u"ä"]


def sandhi(prefix, suffix):
    """ ("glas", "skål") --> ("glas", "skål"), ("glass", "skål") """
    if prefix[-1] == suffix[0] and prefix[-1] in "bdfgjlmnprstv":
        return [(prefix, suffix), (prefix + prefix[-1], suffix)]
    else:
        return [(prefix, suffix)]


def compound(saldo_lexicon, w, msd=None):
    compounds = []
    for (_prefix, _suffix) in prefixes_suffixes(w):
        if not(exception(_suffix)):
            for (prefix, suffix) in sandhi(_prefix, _suffix):
                anap = saldo_lexicon.get_prefixes(prefix)
                anas = saldo_lexicon.get_suffixes(suffix, msd)
                compounds.extend([(p, s) for p in anap for s in anas])
    return compounds


def read_xml(xml='saldom.xml', tagset="SUC"):
    """Read the XML version of SALDO's morphological lexicon (saldom.xml).
    """
    import xml.etree.cElementTree as cet
    tagmap = getattr(util.tagsets, "saldo_to_" + tagset.lower() + "_compound")
    util.log.info("Reading XML lexicon")
    lexicon = {}

    context = cet.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = next(context)

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

def save_to_picklefile(saldofile, lexicon, protocol=-1, verbose=True):
    """Save a Saldo lexicon to a Pickled file.
    The input lexicon should be a dict:
      - lexicon = {wordform: {lemgram: {"msd": set(), "pos": str}}}
    """
    if verbose: util.log.info("Saving Saldo lexicon in Pickle format")

    picklex = {}
    for word in lexicon:
        lemgrams = []

        for lemgram, annotation in list(lexicon[word].items()):
            msds = PART_DELIM2.join(annotation["msd"])
            tags = PART_DELIM2.join(annotation.get("tags", []))
            lemgrams.append( PART_DELIM1.join([lemgram, msds, annotation["pos"], tags] ) )

        picklex[word] = sorted(lemgrams)

    with open(saldofile, "wb") as F:
        pickle.dump(picklex, F, protocol=protocol)
    if verbose: util.log.info("OK, saved")


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
