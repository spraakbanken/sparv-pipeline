# -*- coding: utf-8 -*-
import sparv.util as util
import pickle


def annotate(out, lemgram, model, affix="|", delimiter="|"):
    """ Annotates each lemgram with its corresponding saldo_id,
        according to model (crosslink.pickle)
      - out is the resulting annotation file
      - lemgram is the existing annotations for lemgrams
      - model is the crosslink model
    """
    lexicon = PivotLexicon(model)
    WORD = util.read_annotation(lemgram)

    OUT = {}

    for tokid in WORD:
        saldo_ids = []
        for lemgram in WORD[tokid].split(delimiter):
            s_i = lexicon.get_exactMatch(lemgram)
            if s_i:
                saldo_ids += [s_i]
        OUT[tokid] = affix + delimiter.join(set(saldo_ids)) + affix if saldo_ids else affix

    util.write_annotation(out, OUT)


class PivotLexicon(object):
    """A lexicon for oldswedish-Saldo  lookups.
    It is initialized from a Pickled file.
    """
    def __init__(self, crossfile, verbose=True):
        if verbose:
            util.log.info("Reading cross lexicon: %s", crossfile)
        with open(crossfile, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            util.log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, lem):
        """Lookup a word in the lexicon."""
        if lem.lower() == lem:
            annotation_tag_pairs = self.lexicon.get(lem, [])
        else:
            annotation_tag_pairs = self.lexicon.get(lem, []) + self.lexicon.get(lem.lower(), [])
        return list(map(_split_val, annotation_tag_pairs))

    def get_exactMatch(self, word):
        s = self.lookup(word)
        if s and s[0] == "exactMatch":
            return s[1]


def _split_val(key_val):
    return key_val.rsplit(PART_DELIM1)[1]


def read_xml(xml='diapivot.xml'):
    """Read the XML version of crosslinked lexicon (crosslink.xml)."""

    import xml.etree.cElementTree as cet
    util.log.info("Reading XML lexicon")
    lexicon = {}

    context = cet.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':

                lemma = elem.find("Lemma")
                dalin, saldo = [], ''
                for form in lemma.findall("FormRepresentation"):
                    cat = findval(form, "category")
                    lem = findval(form, "lemgram")
                    if cat == "modern":
                        saldo = lem
                    else:
                        match = findval(form, "match")
                        dalin += [(lem, match)]

                [lexicon.update({d: {'saldo': saldo, 'match': m}}) for (d, m) in dalin]

            # Done parsing section. Clear tree to save memory
            if elem.tag in ['LexicalEntry', 'frame', 'resFrame']:
                root.clear()

    test_annotations(lexicon)
    util.log.info("OK, read")
    return lexicon


def findval(elems, key):
    for form in elems:
        param, word = "", ""
        att = form.get("att", "")
        if att == key:
            return form.get("val")
    return ""


def test_annotations(lexicon):
    for key in testwords:
        util.log.output("%s = %s", key, lexicon.get(key))

testwords = [u"tigerhjerta..nn.1",
             u"lågland..nn.1",
             u"gud..nn.1"
             ]

PART_DELIM1 = "^1"


def save_to_picklefile(saldofile, lexicon, protocol=-1, verbose=True):
    """Save a cross lexicon to a Pickled file.
    The input lexicon should be a dict:
      - lexicon = {lemgram: {saldo: str, match : str}}
    """
    if verbose:
        util.log.info("Saving cross lexicon in Pickle format")

    picklex = {}
    for lem in lexicon:
        lemgrams = []

        for saldo, match in list(lexicon[lem].items()):
            lemgrams.append(PART_DELIM1.join([saldo, match]))

        picklex[lem] = sorted(lemgrams)

    with open(saldofile, "wb") as F:
        pickle.dump(picklex, F, protocol=protocol)
    if verbose:
        util.log.info("OK, saved")


def xml_to_pickle(xml, filename):
    """Read an XML dictionary and save as a pickle file."""

    xml_lexicon = read_xml(xml)
    save_to_picklefile(filename, xml_lexicon)


if __name__ == '__main__':
    util.run.main(annotate, xml_to_pickle=xml_to_pickle)
