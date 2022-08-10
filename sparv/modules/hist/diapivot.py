"""Create diapivot annotation."""

import pickle
import xml.etree.ElementTree as etree

from sparv.api import Annotation, Model, ModelOutput, Output, annotator, get_logger, modelbuilder, util

logger = get_logger(__name__)

PART_DELIM1 = "^1"


@annotator("Diapivot annotation", language=["swe-1800", "swe-fsv"])
def diapivot_annotate(out: Output = Output("<token>:hist.diapivot", cls="token:lemgram",
                                           description="SALDO lemgrams inferred from the diapivot model"),
                      lemgram: Annotation = Annotation("<token>:hist.lemgram"),
                      model: Model = Model("hist/diapivot.pickle")):
    """Annotate each lemgram with its corresponding saldo_id according to model.

    Args:
        out (str, optional): Resulting annotation file.
            Defaults to Output("<token>:hist.diapivot", description="SALDO IDs corresponding to lemgrams").
        lemgram (str, optional): Existing lemgram annotation. Defaults to Annotation("<token>:saldo.lemgram").
        model (str, optional): Crosslink model. Defaults to Model("hist/diapivot.pickle").
    """
    lexicon = PivotLexicon(model.path)
    lemgram_annotation = list(lemgram.read())

    out_annotation = []

    for lemgrams in lemgram_annotation:
        saldo_ids = []
        for lemgram in lemgrams.split(util.constants.DELIM):
            s_i = lexicon.get_exactMatch(lemgram)
            if s_i:
                saldo_ids += [s_i]

        out_annotation.append(util.misc.cwbset(set(saldo_ids), sort=True))

    out.write(out_annotation)


@annotator("Combine lemgrams from SALDO, Dalin, Swedberg and the diapivot", language=["swe-1800", "swe-fsv"])
def combine_lemgrams(out: Output = Output("<token>:hist.combined_lemgrams", cls="token:lemgram",
                                   description="SALDO lemgrams combined from SALDO, Dalin, Swedberg and the diapivot"),
                     diapivot: Annotation = Annotation("<token>:hist.diapivot"),
                     lemgram: Annotation = Annotation("<token>:hist.lemgram")):
    """Combine lemgrams from SALDO, Dalin, Swedberg and the diapivot into a set of annotations."""
    from sparv.modules.misc import misc
    misc.merge_to_set(out, left=diapivot, right=lemgram, unique=True, sort=True)


@modelbuilder("Diapivot model", language=["swe-1800", "swe-fsv"])
def build_diapivot(out: ModelOutput = ModelOutput("hist/diapivot.pickle")):
    """Download diapivot XML dictionary and save as a pickle file."""
    # Download diapivot.xml
    xml_model = Model("hist/diapivot.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/diapivot/diapivot.xml")

    # Create pickle file
    xml_lexicon = read_xml(xml_model.path)
    logger.info("Saving cross lexicon in Pickle format")
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
            logger.info("Reading cross lexicon: %s", crossfile)
        with open(crossfile, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            logger.info("OK, read %d words", len(self.lexicon))

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
    logger.info("Reading XML lexicon")
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
    util.misc.test_lexicon(lexicon, testwords)

    logger.info("OK, read")
    return lexicon


def _findval(elems, key):
    for form in elems:
        att = form.get("att", "")
        if att == key:
            return form.get("val")
    return ""
