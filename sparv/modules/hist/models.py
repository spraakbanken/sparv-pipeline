"""Model builders for older Swedish lexicons."""

import re
import xml.etree.ElementTree as etree

from sparv.api import Model, ModelOutput, get_logger, modelbuilder, util
from sparv.api.util.tagsets import tagmappings
from sparv.modules.saldo.saldo_model import HashableDict, SaldoLexicon

logger = get_logger(__name__)


@modelbuilder("Dalin morphology model", language=["swe-1800"])
def build_dalin(out: ModelOutput = ModelOutput("hist/dalin.pickle")):
    """Download Dalin morphology XML and save as a pickle file."""
    # Download dalinm.xml
    xml_model = Model("hist/dalinm.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm/dalinm.xml")

    # Create pickle file
    lmf_to_pickle(xml_model.path, out.path)

    # Clean up
    xml_model.remove()


@modelbuilder("Swedberg morphology model", language=["swe-1800"])
def build_swedberg(out: ModelOutput = ModelOutput("hist/swedberg.pickle")):
    """Download Swedberg morphology XML and save as a pickle file."""
    # Download swedbergm.xml
    xml_model = Model("hist/swedbergm.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swedbergm/swedbergm.xml")

    # Create pickle file
    lmf_to_pickle(xml_model.path, out.path)

    # Clean up
    xml_model.remove()


@modelbuilder("Morphology model for Old Swedish", language=["swe-fsv"])
def build_fsvm(out: ModelOutput = ModelOutput("hist/fsvm.pickle")):
    """Download pickled model for fornsvenska."""
    xml_model = Model("hist/fsvm.xml")
    xml_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/fsvm/fsvm.xml")

    # Create pickle file
    lmf_to_pickle(xml_model.path, out.path, use_fallback=True)

    # Clean up
    xml_model.remove()


@modelbuilder("Spelling variants list for Old Swedish", language=["swe-fsv"])
def build_fsv_spelling(out: ModelOutput = ModelOutput("hist/fsv-spelling-variants.txt")):
    """Download spelling variants list for fornsvenska."""
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/hist/fsv-spelling-variants.txt")


################################################################################
# LMF CONVERSION
################################################################################


def lmf_to_pickle(xml, filename, annotation_elements=("writtenForm", "lemgram"), skip_multiword=False,
                  translate_tags=True, use_fallback=False):
    """Read an XML dictionary and save as a pickle file."""
    xml_lexicon = read_lmf(xml, annotation_elements=annotation_elements, skip_multiword=skip_multiword,
                           translate_tags=translate_tags, use_fallback=use_fallback)
    SaldoLexicon.save_to_picklefile(filename, xml_lexicon)


def read_lmf(xml, annotation_elements=("writtenForm", "lemgram"), verbose=True, skip_multiword=False,
             translate_tags=True, use_fallback=False):
    """Parse a historical morphological LMF lexicon into the standard SALDO format.

    Does not handle msd-information well.
    Does not mark particles.
    Does handle multiwords expressions with gaps.

    Args:
        xml (str): Path to the input XML file.
        annotation_elements (tuple, optional): XML element(s) for the annotation value, "writtenForm" for baseform,
            "lemgram" for lemgram. "writtenForm" is translated to "gf" and "lemgram" to "lem"
            (for compatability with Saldo). Defaults to ("writtenForm", "lemgram").
        verbose (bool, optional): Whether to turn on verbose mode. Defaults to True.
        skip_multiword (bool, optional): Whether to make special entries for multiword expressions.
            Set this to False only if the tool used for text annotation cannot handle this at all. Defaults to False.
        translate_tags (bool, optional): [description]. Defaults to True.
        use_fallback (bool, optional): [description]. Defaults to False.

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
                    annotations[key] = tuple([_findval(lem, a)])

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

                            # Is it the last word in the multi word expression?
                            if i == len(wordparts) - 1:
                                lexicon.setdefault(multiwords[0], {}).setdefault(annotations, (set(), set(), mwe_gap, particle))[1].add(tuple(multiwords[1:]))
                                multiwords = []
                        else:
                            # Single word expressions
                            if translate_tags:
                                tags = _convert_default(pos, inhs, param)
                                if not tags and use_fallback:
                                    tags = _pos_from_lemgram(lemgram)
                                if tags:
                                    lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), False, False))[0].update(tags)
                            else:
                                saldotag = " ".join([pos, param])  # this tag is rather useless, but at least gives some information
                                tags = tuple([saldotag])
                                lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), False, False))[0].update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ["LexicalEntry", "frame", "resFrame"]:
                root.clear()
    if verbose:
        testwords = ["äplebuske",
                     "stöpljus",
                     "katt",
                     "doktor"]
        util.misc.test_lexicon(lexicon, testwords)
        logger.info(f"OK, read {len(lexicon)} entries")
    return lexicon


################################################################################
# Auxiliaries
################################################################################

def _findval(elems, key):
    """Help function for looking up values in the lmf."""
    def iterfindval():
        for form in elems:
            att = form.get("att", "")
            if att == key:
                yield form.get("val")
        yield ""

    return next(iterfindval())


def _convert_default(pos, inhs, param):
    """Try to convert SALDO tags into SUC tags."""
    tagmap = tagmappings.mappings["saldo_to_suc"]
    saldotag = " ".join(([pos] + inhs + [param]))
    tags = tagmap.get(saldotag)
    if tags:
        return tags
    tags = _try_translate(saldotag)
    if tags:
        tagmap[saldotag] = tags
        return tags
    tags = tagmap.get(pos)
    if tags:
        return tags
    tags = []
    for t in list(tagmap.keys()):
        if t.split()[0] == pos:
            tags.extend(tagmap.get(t))
    return tags


def _try_translate(params):
    """Do some basic translations."""
    params_list = [params]
    if " m " in params:
        # Masculine is translated into utrum
        params_list.append(re.sub(" m ", " u ", params))
    if " f " in params:
        # Feminine is translated into utrum
        params_list.append(re.sub(" f ", " u ", params))
    for params in params_list:
        params = params.split()
        # Copied from tagmappings._make_saldo_to_suc(), try to convert the tag
        # but allow m (the match) to be None if the tag still can't be translated
        paramstr = " ".join(tagmappings.mappings["saldo_params_to_suc"].get(prm, prm.upper()) for prm in params)
        for (pre, post) in tagmappings._suc_tag_replacements:
            m = re.match(pre, paramstr)
            if m:
                break
        if m is not None:
            sucfilter = m.expand(post).replace(" ", r"\.").replace("+", r"\+")
            return set(suctag for suctag in tagmappings.tags["suc_tags"] if re.match(sucfilter, suctag))
    return []


def _pos_from_lemgram(lemgram):
    """Get SUC POS tag from POS in lemgram."""
    pos = lemgram.split(".")[2]
    tagmap = tagmappings.mappings["saldo_pos_to_suc"]
    return tagmap.get(pos, [])
