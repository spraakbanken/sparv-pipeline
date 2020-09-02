"""Create diapivot annotation."""

import logging
import pickle
import xml.etree.ElementTree as etree

import sparv.util as util
from sparv import Annotation, Model, ModelOutput, Output, annotator, modelbuilder

log = logging.getLogger(__name__)

PART_DELIM1 = "^1"


@annotator("Diapivot annotation", language=["swe-1800"])
def diapivot_annotate(out: Output = Output("<token>:hist.diapivot", description="SALDO IDs corresponding to lemgrams"),
                      lemgram: Annotation = Annotation("<token>:saldo.lemgram"),
                      model: Model = Model("hist/diapivot.pickle")):
    """Annotate each lemgram with its corresponding saldo_id according to model.

    Args:
        out (str, optional): Resulting annotation file.
            Defaults to Output("<token>:hist.diapivot", description="SALDO IDs corresponding to lemgrams").
        lemgram (str, optional): Existing lemgram annotation. Defaults to Annotation("<token>:saldo.lemgram").
        model (str, optional): Crosslink model. Defaults to Model("hist/diapivot.pickle").
    """
    lexicon = PivotLexicon(model)
    lemgram_annotation = list(lemgram.read())

    out_annotation = []

    for lemgrams in lemgram_annotation:
        saldo_ids = []
        for lemgram in lemgrams.split(util.DELIM):
            s_i = lexicon.get_exactMatch(lemgram)
            if s_i:
                saldo_ids += [s_i]
        out_annotation.append(util.AFFIX + util.DELIM.join(set(saldo_ids)) + util.AFFIX if saldo_ids else util.AFFIX)

    out.write(out_annotation)


@modelbuilder("Diapivot model", language=["swe"])
def build_diapivot(out: ModelOutput = ModelOutput("hist/diapivot.pickle")):
    """Download diapivot XML dictionary and save as a pickle file."""
    # Download diapivot.xml
    xml_model = Model("hist/diapivot.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/diapivot/diapivot.xml")

    # Create pickle file
    xml_lexicon = read_xml(xml_model.path)
    log.info("Saving cross lexicon in Pickle format")
    picklex = {}
    for lem in xml_lexicon:
        lemgrams = []
        for saldo, match in list(xml_lexicon[lem].items()):
            lemgrams.append(PART_DELIM1.join([saldo, match]))
        picklex[lem] = sorted(lemgrams)

    out.write_pickle(picklex)

    # Clean up
    xml_model.remove()


################################################################################
# Auxiliaries
################################################################################


class PivotLexicon:
    """A lexicon for old swedish SALDO lookups.

    It is initialized from a pickled file.
    """

    def __init__(self, crossfile, verbose=True):
        """Read pickled lexicon."""
        if verbose:
            log.info("Reading cross lexicon: %s", crossfile)
        with open(crossfile, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, lem):
        """Lookup a word in the lexicon."""
        if lem.lower() == lem:
            annotation_tag_pairs = self.lexicon.get(lem, [])
        else:
            annotation_tag_pairs = self.lexicon.get(lem, []) + self.lexicon.get(lem.lower(), [])
        return list(map(_split_val, annotation_tag_pairs))

    def get_exactMatch(self, word):
        """Get only exact matches from lexicon."""
        s = self.lookup(word)
        if s and s[0] == "exactMatch":
            return s[1]


def _split_val(key_val):
    return key_val.rsplit(PART_DELIM1)[1]


def read_xml(xml):
    """Read the XML version of crosslinked lexicon."""
    log.info("Reading XML lexicon")
    lexicon = {}

    context = etree.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    _event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':

                lemma = elem.find("Lemma")
                dalin, saldo = [], ''
                for form in lemma.findall("FormRepresentation"):
                    cat = _findval(form, "category")
                    lem = _findval(form, "lemgram")
                    if cat == "modern":
                        saldo = lem
                    else:
                        match = _findval(form, "match")
                        dalin += [(lem, match)]

                [lexicon.update({d: {'saldo': saldo, 'match': m}}) for (d, m) in dalin]

            # Done parsing section. Clear tree to save memory
            if elem.tag in ['LexicalEntry', 'frame', 'resFrame']:
                root.clear()

    testwords = ["tigerhjerta..nn.1",
                 "lågland..nn.1",
                 "gud..nn.1"]
    util.test_lexicon(lexicon, testwords)

    log.info("OK, read")
    return lexicon


def _findval(elems, key):
    for form in elems:
        att = form.get("att", "")
        if att == key:
            return form.get("val")
    return ""
