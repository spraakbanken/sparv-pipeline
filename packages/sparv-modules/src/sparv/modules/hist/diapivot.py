"""Create diapivot annotation."""

import pickle
import xml.etree.ElementTree as etree  # noqa: N813
from pathlib import Path

from sparv.api import Annotation, Model, ModelOutput, Output, annotator, get_logger, modelbuilder, util

logger = get_logger(__name__)

PART_DELIM1 = "^1"


@annotator("Diapivot annotation", language=["swe-1800", "swe-fsv"])
def diapivot_annotate(
    out: Output = Output(
        "<token>:hist.diapivot", cls="token:lemgram", description="SALDO lemgrams inferred from the diapivot model"
    ),
    lemgram: Annotation = Annotation("<token>:hist.lemgram"),
    model: Model = Model("hist/diapivot.pickle"),
) -> None:
    """Annotate each lemgram with its corresponding saldo_id according to model.

    Args:
        out: Resulting annotation file.
        lemgram: Existing lemgram annotation.
        model: Crosslink model.
    """
    lexicon = PivotLexicon(model.path)
    lemgram_annotation = list(lemgram.read())

    out_annotation = []

    for lemgrams in lemgram_annotation:
        saldo_ids = []
        for lg in lemgrams.split(util.constants.DELIM):
            s_i = lexicon.get_exact_match(lg)
            if s_i:
                saldo_ids += [s_i]

        out_annotation.append(util.misc.cwbset(set(saldo_ids), sort=True))

    out.write(out_annotation)


@annotator("Combine lemgrams from SALDO, Dalin, Swedberg and the diapivot", language=["swe-1800", "swe-fsv"])
def combine_lemgrams(
    out: Output = Output(
        "<token>:hist.combined_lemgrams",
        cls="token:lemgram",
        description="SALDO lemgrams combined from SALDO, Dalin, Swedberg and the diapivot",
    ),
    diapivot: Annotation = Annotation("<token>:hist.diapivot"),
    lemgram: Annotation = Annotation("<token>:hist.lemgram"),
) -> None:
    """Combine lemgrams from SALDO, Dalin, Swedberg and the diapivot into a set of annotations.

    Args:
        out: Resulting annotation file.
        diapivot: Existing lemgram annotation from the diapivot model.
        lemgram: Existing lemgram annotation.
    """
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.merge_to_set(out, left=diapivot, right=lemgram, unique=True, sort=True)


@modelbuilder("Diapivot model", language=["swe-1800", "swe-fsv"])
def build_diapivot(out: ModelOutput = ModelOutput("hist/diapivot.pickle")) -> None:
    """Download diapivot XML dictionary and save as a pickle file.

    Args:
        out: Output model file.
    """
    # Download diapivot.xml
    xml_model = Model("hist/diapivot.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/diapivot/diapivot.xml")

    # Create pickle file
    xml_lexicon = read_xml(xml_model.path)
    logger.info("Saving cross lexicon in Pickle format")
    picklex = {}
    for lem in xml_lexicon:
        lemgrams = []
        for saldo, match in xml_lexicon[lem].items():
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

    def __init__(self, crossfile: Path, verbose: bool = True) -> None:
        """Read pickled lexicon."""
        if verbose:
            logger.info("Reading cross lexicon: %s", crossfile)
        with crossfile.open("rb") as f:
            self.lexicon = pickle.load(f)
        if verbose:
            logger.info("OK, read %d words", len(self.lexicon))

    def lookup(self, lem: str) -> list[list[str]]:
        """Lookup a word in the lexicon.

        Args:
            lem: The word to look up.

        Returns:
            A list of lists containing the lemma and its corresponding tags.
        """
        if lem.lower() == lem:
            annotation_tag_pairs = self.lexicon.get(lem, [])
        else:
            annotation_tag_pairs = self.lexicon.get(lem, []) + self.lexicon.get(lem.lower(), [])
        return list(map(_split_val, annotation_tag_pairs))

    def get_exact_match(self, word: str) -> str | None:
        """Get only exact matches from lexicon.

        Args:
            word: The word to look up.

        Returns:
            The exact match if found, otherwise None.
        """
        s = self.lookup(word)
        if s and s[0] == "exactMatch":
            return s[1]
        return None


def _split_val(key_val: str) -> list[str]:
    """Split the key-value pair into a list.

    Args:
        key_val: The key-value pair to split.

    Returns:
        A list containing the key and value.
    """
    return key_val.rsplit(PART_DELIM1)[1]


def read_xml(xml: Path) -> dict[str, dict[str, str]]:
    """Read the XML version of crosslinked lexicon.

    Args:
        xml: Path to the XML file.

    Returns:
        A dictionary with lemgrams as keys and a dictionary of SALDO and match information as values.
    """
    logger.info("Reading XML lexicon")
    lexicon = {}

    context = etree.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    _event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == "LexicalEntry":
                lemma = elem.find("Lemma")
                dalin, saldo = [], ""
                for form in lemma.findall("FormRepresentation"):
                    cat = _findval(form, "category")
                    lem = _findval(form, "lemgram")
                    if cat == "modern":
                        saldo = lem
                    else:
                        match = _findval(form, "match")
                        dalin += [(lem, match)]

                [lexicon.update({d: {"saldo": saldo, "match": m}}) for (d, m) in dalin]

            # Done parsing section. Clear tree to save memory
            if elem.tag in {"LexicalEntry", "frame", "resFrame"}:
                root.clear()

    testwords = ["tigerhjerta..nn.1", "lågland..nn.1", "gud..nn.1"]
    util.misc.test_lexicon(lexicon, testwords)

    logger.info("OK, read")
    return lexicon


def _findval(elems: etree.Element, key: str) -> str:
    """Find the value of a given element in the XML.

    Args:
        elems: The XML element whose children will be searched.
        key: The key to find the value for.

    Returns:
        The value of the key if found, otherwise an empty string.
    """
    for form in elems:
        if form.get("att", "") == key:
            return form.get("val")
    return ""
