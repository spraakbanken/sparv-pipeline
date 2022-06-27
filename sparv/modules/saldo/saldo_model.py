"""SALDO Model builders."""

import pathlib
import pickle
import re
import xml.etree.ElementTree as etree

from sparv.api import Model, ModelOutput, get_logger, modelbuilder, util
from sparv.api.util.tagsets import tagmappings

logger = get_logger(__name__)


# SALDO: Delimiters that hopefully are never found in an annotation or in a POS tag:
PART_DELIM = "^"
PART_DELIM1 = "^1"
PART_DELIM2 = "^2"
PART_DELIM3 = "^3"


@modelbuilder("SALDO morphology XML", language=["swe"])
def download_saldo(out: ModelOutput = ModelOutput("saldo/saldom.xml")):
    """Download SALDO morphology XML."""
    out.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml")


@modelbuilder("SALDO morphology model", language=["swe"])
def build_saldo(out: ModelOutput = ModelOutput("saldo/saldo.pickle"),
                saldom: Model = Model("saldo/saldom.xml")):
    """Save SALDO morphology as a pickle file."""
    tagmap = tagmappings.mappings["saldo_to_suc"]
    lmf_to_pickle(saldom.path, out.path, tagmap)


class SaldoLexicon:
    """A lexicon for Saldo lookups.

    It is initialized from a Pickled file, or a space-separated text file.
    """

    def __init__(self, saldofile: pathlib.Path, verbose=True):
        """Read lexicon."""
        if verbose:
            logger.info("Reading Saldo lexicon: %s", saldofile)
        if saldofile.suffix == ".pickle":
            with open(saldofile, "rb") as F:
                self.lexicon = pickle.load(F)
        else:
            lexicon = self.lexicon = {}
            with open(saldofile, "rb") as F:
                for line in F:
                    row = line.decode(util.constants.UTF8).split()
                    word = row.pop(0)
                    lexicon[word] = row
        if verbose:
            logger.info("OK, read %d words", len(self.lexicon))

    def lookup(self, word):
        """Lookup a word in the lexicon.

        Returns a list of (annotation-dictionary, list-of-pos-tags, list-of-lists-with-words).
        """
        if word.lower() == word:
            annotation_tag_pairs = self.lexicon.get(word, [])
        else:
            annotation_tag_pairs = self.lexicon.get(word, []) + self.lexicon.get(word.lower(), [])
        return list(map(split_triple, annotation_tag_pairs))

    @staticmethod
    def save_to_picklefile(saldofile, lexicon, protocol=-1, verbose=True):
        """Save a Saldo lexicon to a Pickled file.

        The input lexicon should be a dict:
          - lexicon = {wordform: {{annotation-type: annotation}: (set(possible tags), set(tuples with following words), gap-allowed-boolean, is-particle-verb-boolean)}}
        """
        if verbose:
            logger.info("Saving LMF lexicon in Pickle format")

        picklex = {}
        for word in lexicon:
            annotations = []
            for annotation, extra in list(lexicon[word].items()):
                # annotationlist = PART_DELIM3.join(annotation)
                annotationlist = PART_DELIM2.join(k + PART_DELIM3 + PART_DELIM3.join(annotation[k]) for k in annotation)
                taglist = PART_DELIM3.join(sorted(extra[0]))
                wordlist = PART_DELIM2.join([PART_DELIM3.join(x) for x in sorted(extra[1])])
                gap_allowed = "1" if extra[2] else "0"
                particle = "1" if extra[3] else "0"
                annotations.append(PART_DELIM1.join([annotationlist, taglist, wordlist, gap_allowed, particle]))

            picklex[word] = sorted(annotations)

        with open(saldofile, "wb") as F:
            pickle.dump(picklex, F, protocol=protocol)
        if verbose:
            logger.info("OK, saved")

    @staticmethod
    def save_to_textfile(saldofile, lexicon, verbose=True):
        """Save a Saldo lexicon to a space-separated text file.

        The input lexicon should be a dict:
          - lexicon = {wordform: {annotation: set(possible tags)}}
        NOT UP TO DATE
        """
        if verbose:
            logger.info("Saving LMF lexicon in text format")
        with open(saldofile, "w") as F:
            for word in sorted(lexicon):
                annotations = [PART_DELIM.join([annotation] + sorted(postags))
                               for annotation, postags in list(lexicon[word].items())]
                print(" ".join([word] + annotations).encode(util.constants.UTF8), file=F)
        if verbose:
            logger.info("OK, saved")


def split_triple(annotation_tag_words):
    """Split annotation_tag_words."""
    annotation, tags, words, gap_allowed, particle = annotation_tag_words.split(PART_DELIM1)
    # annotationlist = [x for x in annotation.split(PART_DELIM3) if x]
    annotationdict = {}
    for a in annotation.split(PART_DELIM2):
        key, values = a.split(PART_DELIM3, 1)
        annotationdict[key] = values.split(PART_DELIM3)

    taglist = [x for x in tags.split(PART_DELIM3) if x]
    wordlist = [x.split(PART_DELIM3) for x in words.split(PART_DELIM2) if x]

    return annotationdict, taglist, wordlist, gap_allowed == "1", particle == "1"


################################################################################
# Auxiliaries
################################################################################


def lmf_to_pickle(xml, filename, tagmap, annotation_elements=("gf", "lem", "saldo")):
    """Read an XML dictionary and save as a pickle file."""
    xml_lexicon = read_lmf(xml, tagmap, annotation_elements)
    SaldoLexicon.save_to_picklefile(filename, xml_lexicon)


def read_lmf(xml, tagmap, annotation_elements=("gf", "lem", "saldo"), verbose=True):
    """Read the XML version of SALDO's morphological lexicon (saldom.xml).

    Return a lexicon dictionary, {wordform: {{annotation-type: annotation}: ( set(possible tags), set(tuples with following words) )}}
     - annotation_element is the XML element for the annotation value (currently: 'gf' for baseform, 'lem' for lemgram or 'saldo' for SALDO id)
     - tagset is the tagset for the possible tags (currently: 'SUC', 'Parole', 'Saldo')
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

                for a in annotation_elements:
                    annotations[a] = tuple(x.text for x in elem.findall(a))

                pos = elem.findtext("pos")
                inhs = elem.findtext("inhs")
                if inhs == "-":
                    inhs = ""
                inhs = inhs.split()

                # Check the paradigm for an "x", meaning a multi-word expression with a required gap
                p = elem.findtext("p")
                x_find = re.search(r"_x(\d*)_", p)
                x_insert = x_find.groups()[0] if x_find else None
                if x_insert == "":
                    x_insert = "1"

                # Only vbm and certain paradigms allow gaps
                gap_allowed = (pos == "vbm" or p in (u"abm_x1_var_än", u"knm_x_ju_ju", u"pnm_x1_inte_ett_dugg", u"pnm_x1_vad_än", u"ppm_x1_för_skull"))

                table = elem.find("table")
                multiwords = []

                for form in list(table):
                    word = form.findtext("wf")
                    param = form.findtext("param")

                    if param in ("frag", "c", "ci", "cm"):
                        # We don't use these wordforms, so skip
                        continue
                    elif param[-1].isdigit() and param[-2:] != "-1":
                        # Handle multi-word expressions
                        multiwords.append(word)
                        multipart, multitotal = param.split(":")[-1].split("-")
                        particle = bool(re.search(r"vbm_.+?p.*?\d+_", p))  # Multi-word with particle

                        # Add a "*" where the gap should be
                        if x_insert and multipart == x_insert:
                            multiwords.append("*")

                        if multipart == multitotal:
                            lexicon.setdefault(multiwords[0], {}).setdefault(annotations, (set(), set(), gap_allowed, particle))[1].add(tuple(multiwords[1:]))
                            multiwords = []
                    else:
                        # Single word expressions
                        if param[-2:] == "-1":
                            param = param.rsplit(" ", 1)[0]
                            if pos == "vbm":
                                pos = "vb"
                        saldotag = " ".join([pos] + inhs + [param])
                        tags = tagmap.get(saldotag)
                        if tags:
                            lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), False, False))[0].update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ["LexicalEntry", "frame", "resFrame"]:
                root.clear()

    testwords = ["äggtoddyarna",
                 "Linköpingsbors",
                 "katabatiska",
                 "väg-",
                 "formar",
                 "in",
                 "datorrelaterade"]
    util.misc.test_lexicon(lexicon, testwords)

    if verbose:
        logger.info("OK, read")
    return lexicon


class HashableDict(dict):
    """A dict that's hashable."""

    def __key(self):
        return tuple((k, self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()


################################################################################
# Additional utilities
################################################################################


def extract_tags(lexicon):
    """Extract the set of all tags that are used in a lexicon.

    The input lexicon should be a dict:
      - lexicon = {wordform: {annotation: set(possible tags)}}
    """
    tags = set()
    for annotations in list(lexicon.values()):
        tags.update(*list(annotations.values()))
    return tags
