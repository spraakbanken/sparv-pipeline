"""Model builders for older Swedish lexicons."""

import re
import xml.etree.ElementTree as etree  # noqa: N813
from collections.abc import Iterable
from pathlib import Path

from sparv.api import Model, ModelOutput, get_logger, modelbuilder, util
from sparv.api.util.tagsets import tagmappings
from sparv.modules.saldo.saldo_model import HashableDict, SaldoLexicon

from .diapivot import _findval

logger = get_logger(__name__)


@modelbuilder("Dalin morphology model", language=["swe-1800"])
def build_dalin(out: ModelOutput = ModelOutput("hist/dalin.pickle")) -> None:
    """Download Dalin morphology XML and save as a pickle file.

    Args:
        out: Output model file.
    """
    # Download dalinm.xml
    xml_model = Model("hist/dalinm.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm/dalinm.xml")

    # Create pickle file
    lmf_to_pickle(xml_model.path, out.path)

    # Clean up
    xml_model.remove()


@modelbuilder("Swedberg morphology model", language=["swe-1800"])
def build_swedberg(out: ModelOutput = ModelOutput("hist/swedberg.pickle")) -> None:
    """Download Swedberg morphology XML and save as a pickle file.

    Args:
        out: Output model file.
    """
    # Download swedbergm.xml
    xml_model = Model("hist/swedbergm.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swedbergm/swedbergm.xml")

    # Create pickle file
    lmf_to_pickle(xml_model.path, out.path)

    # Clean up
    xml_model.remove()


@modelbuilder("Morphology model for Old Swedish", language=["swe-fsv"])
def build_fsvm(out: ModelOutput = ModelOutput("hist/fsvm.pickle")) -> None:
    """Download pickled model for fornsvenska.

    Args:
        out: Output model file.
    """
    xml_model = Model("hist/fsvm.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/fsvm/fsvm.xml")

    # Create pickle file
    lmf_to_pickle(xml_model.path, out.path, use_fallback=True)

    # Clean up
    xml_model.remove()


@modelbuilder("Spelling variants list for Old Swedish", language=["swe-fsv"])
def build_fsv_spelling(out: ModelOutput = ModelOutput("hist/fsv-spelling-variants.txt")) -> None:
    """Download spelling variants list for fornsvenska.

    Args:
        out: Output model file.
    """
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/hist/fsv-spelling-variants.txt")


################################################################################
# LMF CONVERSION
################################################################################


def lmf_to_pickle(
    xml: Path,
    filename: Path,
    annotation_elements: Iterable[str] = ("writtenForm", "lemgram"),
    skip_multiword: bool = False,
    translate_tags: bool = True,
    use_fallback: bool = False,
) -> None:
    """Read an XML dictionary and save as a pickle file."""
    xml_lexicon = read_lmf(
        xml,
        annotation_elements=annotation_elements,
        skip_multiword=skip_multiword,
        translate_tags=translate_tags,
        use_fallback=use_fallback,
    )
    SaldoLexicon.save_to_picklefile(filename, xml_lexicon)


def read_lmf(
    xml: Path,
    annotation_elements: Iterable[str] = ("writtenForm", "lemgram"),
    verbose: bool = True,
    skip_multiword: bool = False,
    translate_tags: bool = True,
    use_fallback: bool = False,
) -> dict:
    """Parse a historical morphological LMF lexicon into the standard SALDO format.

    Does not handle msd-information well.
    Does not mark particles.
    Does handle multiwords expressions with gaps.

    Args:
        xml: Path to the input XML file.
        annotation_elements: XML element(s) for the annotation value, "writtenForm" for baseform,
            "lemgram" for lemgram. "writtenForm" is translated to "gf" and "lemgram" to "lem"
            (for compatability with Saldo). Defaults to ("writtenForm", "lemgram").
        verbose: Whether to turn on verbose mode. Defaults to True.
        skip_multiword: Whether to make special entries for multiword expressions.
            Set this to False only if the tool used for text annotation cannot handle this at all. Defaults to False.
        translate_tags: Whether to translate SALDO tags into SUC tags. Defaults to True.
        use_fallback: Whether to get SUC POS tag from POS in lemgram as a fallback. Defaults to False.

    Returns:
        A lexicon dict:
            {wordform: {{annotation-type: annotation}: (set(possible tags), set(tuples with following words) )}}
    """
    if verbose:
        logger.info("Reading XML lexicon")
    lexicon = {}

    context = etree.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == "LexicalEntry":
                annotations = HashableDict()

                lem = elem.find("Lemma").find("FormRepresentation")
                for a in annotation_elements:
                    if a == "writtenForm":
                        key = "gf"
                    elif a == "lemgram":
                        key = "lem"
                    annotations[key] = (_findval(lem, a),)

                pos = _findval(lem, "partOfSpeech")
                inhs = _findval(lem, "inherent")
                lemgram = _findval(lem, "lemgram")
                if inhs == "-":
                    inhs = ""
                inhs = inhs.split()

                # there may be several WordForms
                for forms in elem.findall("WordForm"):
                    word = _findval(forms, "writtenForm")
                    param = _findval(forms, "msd")

                    multiwords = []
                    wordparts = word.split()
                    for i, word in enumerate(wordparts):
                        if (not skip_multiword) and len(wordparts) > 1:
                            # Handle multi-word expressions
                            multiwords.append(word)

                            # We don't use any particles or mwe:s with gaps since that information is not formally
                            # expressed in the historical lexicons. But keep the fields so that the file format matches
                            # the saldo-pickle format.
                            particle = False
                            mwe_gap = False

                            # Is it the last word in the multi-word expression?
                            if i == len(wordparts) - 1:
                                lexicon.setdefault(multiwords[0], {}).setdefault(
                                    annotations, (set(), set(), mwe_gap, particle)
                                )[1].add(tuple(multiwords[1:]))
                                multiwords = []
                        else:  # noqa: PLR5501
                            # Single word expressions
                            if translate_tags:
                                tags = _convert_default(pos, inhs, param)
                                if not tags and use_fallback:
                                    tags = _pos_from_lemgram(lemgram)
                                if tags:
                                    lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), False, False))[
                                        0
                                    ].update(tags)
                            else:
                                saldotag = f"{pos} {param}"  # this tag is rather useless, but at least gives some info
                                tags = (saldotag,)
                                lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), False, False))[
                                    0
                                ].update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in {"LexicalEntry", "frame", "resFrame"}:
                root.clear()
    if verbose:
        testwords = ["äplebuske", "stöpljus", "katt", "doktor"]
        util.misc.test_lexicon(lexicon, testwords)
        logger.info("OK, read %d entries", len(lexicon))
    return lexicon


################################################################################
# Auxiliaries
################################################################################


def _convert_default(pos: str, inhs: list[str], param: str) -> set[str]:
    """Try to convert SALDO tags into SUC tags.

    Args:
        pos: The part of speech.
        inhs: The inherent features.
        param: The MSD.

    Returns:
        A set of SUC tags.
    """
    tagmap = tagmappings.mappings["saldo_to_suc"]
    saldotag = " ".join([pos, *inhs, param])
    if tags := tagmap.get(saldotag):
        return tags
    if tags := _try_translate(saldotag):
        tagmap[saldotag] = tags
        return tags
    if tags := tagmap.get(pos):
        return tags
    tags = []
    for t in tagmap:
        if t.split()[0] == pos:
            tags.extend(tagmap.get(t))
    return tags


def _try_translate(params: str) -> set[str]:
    """Do some basic translations.

    Args:
        params: The parameters to translate.

    Returns:
        A set of SUC tags.
    """
    params_list = [params]
    if " m " in params:
        # Masculine is translated into utrum
        params_list.append(params.replace(" m ", " u "))
    if " f " in params:
        # Feminine is translated into utrum
        params_list.append(params.replace(" f ", " u "))
    for p in params_list:
        params = p.split()
        # Copied from tagmappings._make_saldo_to_suc(), try to convert the tag
        # but allow m (the match) to be None if the tag still can't be translated
        paramstr = " ".join(tagmappings.mappings["saldo_params_to_suc"].get(param, param.upper()) for param in params)
        for pre, post in tagmappings._suc_tag_replacements:  # noqa: B007
            m = re.match(pre, paramstr)
            if m:
                break
        if m is not None:
            sucfilter = m.expand(post).replace(" ", r"\.").replace("+", r"\+")
            return {suctag for suctag in tagmappings.tags["suc_tags"] if re.match(sucfilter, suctag)}
    return []


def _pos_from_lemgram(lemgram: str) -> list[str]:
    """Get SUC POS tag from POS in lemgram.

    Args:
        lemgram: The lemgram to extract the POS from.

    Returns:
        A list of SUC POS tags.
    """
    pos = lemgram.split(".")[2]
    tagmap = tagmappings.mappings["saldo_pos_to_suc"]
    return tagmap.get(pos, [])
