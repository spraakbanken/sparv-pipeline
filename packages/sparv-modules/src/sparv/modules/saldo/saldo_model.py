"""SALDO Model builders."""

import pathlib
import pickle
import re
import xml.etree.ElementTree as etree  # noqa: N813
from pathlib import Path

from sparv.api import Model, ModelOutput, get_logger, modelbuilder, util
from sparv.api.util.tagsets import tagmappings

logger = get_logger(__name__)


# SALDO: Delimiters that hopefully are never found in an annotation or in a POS tag:
PART_DELIM = "^"
PART_DELIM1 = "^1"
PART_DELIM2 = "^2"
PART_DELIM3 = "^3"


@modelbuilder("SALDO morphology XML")
def download_saldo_xml(out: ModelOutput = ModelOutput("saldo/saldom.xml")) -> None:
    """Download SALDO morphology XML.

    Args:
        out: The output file path.
    """
    out.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml")


@modelbuilder("SALDO morphology model", order=1)
def download_saldo_pickle(out: ModelOutput = ModelOutput("saldo/saldo.pickle")) -> None:
    """Download prebuilt SALDO morphology model from sparv-models repo.

    Args:
        out: The output file path.
    """
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/saldo/saldo.pickle")


@modelbuilder("SALDO morphology model", order=2)
def build_saldo_pickle(
    out: ModelOutput = ModelOutput("saldo/saldo.pickle"), saldom: Model = Model("saldo/saldom.xml")
) -> None:
    """Save SALDO morphology as a pickle file.

    Args:
        out: The output file path.
        saldom: The input XML file path.
    """
    tagmap = tagmappings.mappings.saldo_to_suc
    lmf_to_pickle(saldom.path, out.path, tagmap)


class SaldoLexicon:
    """A lexicon for Saldo lookups.

    It is initialized from a Pickled file, or a space-separated text file.
    """

    def __init__(self, saldofile: pathlib.Path, verbose: bool = True) -> None:
        """Read lexicon."""
        if verbose:
            logger.info("Reading Saldo lexicon: %s", saldofile)
        if saldofile.suffix == ".pickle":
            with saldofile.open("rb") as f:
                self.lexicon = pickle.load(f)
        else:
            lexicon = self.lexicon = {}
            with saldofile.open("rb") as f:
                for line in f:
                    row = line.decode(util.constants.UTF8).split()
                    word = row.pop(0)
                    lexicon[word] = row
        if verbose:
            logger.info("OK, read %d words", len(self.lexicon))

    def lookup(self, word: str) -> list:
        """Lookup a word in the lexicon.

        Args:
            word: The word to look up.

        Returns:
            list: A list of tuples containing the annotation dictionary, list of POS tags, and list of lists with words.
        """
        if word.lower() == word:
            annotation_tag_pairs = self.lexicon.get(word, [])
        else:
            annotation_tag_pairs = self.lexicon.get(word, []) + self.lexicon.get(word.lower(), [])
        return list(map(split_triple, annotation_tag_pairs))

    @staticmethod
    def save_to_picklefile(saldofile: Path, lexicon: dict, protocol: int = -1, verbose: bool = True) -> None:
        """Save a Saldo lexicon to a Pickled file.

        Args:
            saldofile: The output file path.
            lexicon: The input lexicon, in the format produced by read_lmf().
            protocol: The Pickle protocol version to use.
            verbose: Whether to log progress.
        """
        if verbose:
            logger.info("Saving LMF lexicon in Pickle format")

        picklex = {}
        for word in lexicon:  # noqa: PLC0206
            annotations = []
            for annotation, extra in lexicon[word].items():
                # annotationlist = PART_DELIM3.join(annotation)
                annotationlist = PART_DELIM2.join(k + PART_DELIM3 + PART_DELIM3.join(annotation[k]) for k in annotation)
                taglist = PART_DELIM3.join(sorted(extra[0]))
                wordlist = PART_DELIM2.join([PART_DELIM3.join(x) for x in sorted(extra[1])])
                gap_allowed = "1" if extra[2] else "0"
                particle = "1" if extra[3] else "0"
                annotations.append(PART_DELIM1.join([annotationlist, taglist, wordlist, gap_allowed, particle]))

            picklex[word] = sorted(annotations)

        with saldofile.open("wb") as f:
            pickle.dump(picklex, f, protocol=protocol)
        if verbose:
            logger.info("OK, saved")

    @staticmethod
    def save_to_textfile(saldofile: Path, lexicon: dict, verbose: bool = True) -> None:
        """Save a Saldo lexicon to a space-separated text file.

        Args:
            saldofile: The output file path.
            lexicon: The input lexicon.
            verbose: Whether to log progress.

        Note:
            Not updated to the new format.
        """
        if verbose:
            logger.info("Saving LMF lexicon in text format")
        with saldofile.open("w", encoding="UTF-8") as f:
            for word in sorted(lexicon):
                annotations = [
                    PART_DELIM.join([annotation, *sorted(postags)]) for annotation, postags in lexicon[word].items()
                ]
                print(" ".join([word, *annotations]).encode(util.constants.UTF8), file=f)
        if verbose:
            logger.info("OK, saved")


def split_triple(annotation_tag_words: str) -> tuple:
    """Split annotation_tag_words.

    Args:
        annotation_tag_words: A string containing the information to be split.

    Returns:
        A tuple containing the split information.
    """
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


def lmf_to_pickle(
    xml: Path, filename: Path, tagmap: dict[str, str], annotation_elements: tuple = ("gf", "lem", "saldo")
) -> None:
    """Read an XML dictionary and save as a pickle file.

    Args:
        xml: The input XML file path.
        filename: The output pickle file path.
        tagmap: The tag mapping dictionary.
        annotation_elements: The XML elements for the annotations.
    """
    xml_lexicon = read_lmf(xml, tagmap, annotation_elements)
    SaldoLexicon.save_to_picklefile(filename, xml_lexicon)


def read_lmf(
    xml: Path, tagmap: dict[str, str], annotation_elements: tuple = ("gf", "lem", "saldo"), verbose: bool = True
) -> dict:
    """Read the XML version of SALDO's morphological lexicon (saldom.xml).

    Args:
        xml: The input XML file path.
        tagmap: The tag mapping dictionary.
        annotation_elements: The XML elements for the annotations.
        verbose: Whether to log progress.

    Returns:
        A dictionary representing the lexicon.

            The structure is as follows:
            - lexicon = {wordform: {{annotation-type: annotation}: (set(possible-tags),
              set(tuples-with-following-words), gap-allowed-boolean, is-particle-verb-boolean)}}
            - annotation-type is the type of annotation (currently: 'gf' for baseform, 'lem' for lemgram or 'saldo' for
              SALDO id)
            - annotation is the value of the annotation
            - possible-tags is a set of possible POS tags for the wordform
            - tuples-with-following-words is a set of tuples with the following words of a multi-word expression
            - gap-allowed-boolean indicates if a gap is allowed (True or False)
            - is-particle-verb-boolean indicates if the word is a particle verb (True or False)
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
                if x_insert == "":  # noqa: PLC1901
                    x_insert = "1"

                # Only vbm and certain paradigms allow gaps
                gap_allowed = pos == "vbm" or p in {
                    "abm_x1_var_än",
                    "knm_x_ju_ju",
                    "pnm_x1_inte_ett_dugg",
                    "pnm_x1_vad_än",
                    "ppm_x1_för_skull",
                }

                table = elem.find("table")
                multiwords = []

                for form in list(table):
                    word = form.findtext("wf")
                    param = form.findtext("param")

                    if param in {"frag", "c", "ci", "cm"}:
                        # We don't use these wordforms, so skip
                        continue
                    if param[-1].isdigit() and param[-2:] != "-1":
                        # Handle multi-word expressions
                        multiwords.append(word)
                        multipart, multitotal = param.split(":")[-1].split("-")
                        particle = bool(re.search(r"vbm_.+?p.*?\d+_", p))  # Multi-word with particle

                        # Add a "*" where the gap should be
                        if x_insert and multipart == x_insert:
                            multiwords.append("*")

                        if multipart == multitotal:
                            lexicon.setdefault(multiwords[0], {}).setdefault(
                                annotations, (set(), set(), gap_allowed, particle)
                            )[1].add(tuple(multiwords[1:]))
                            multiwords = []
                    else:
                        # Single word expressions
                        if param[-2:] == "-1":
                            param = param.rsplit(" ", 1)[0]
                            if pos == "vbm":
                                pos = "vb"
                        saldotag = " ".join([pos, *inhs, param])
                        tags = tagmap.get(saldotag)
                        if tags:
                            lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), False, False))[
                                0
                            ].update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in {"LexicalEntry", "frame", "resFrame"}:
                root.clear()

    testwords = ["äggtoddyarna", "Linköpingsbors", "katabatiska", "väg-", "formar", "in", "datorrelaterade"]
    util.misc.test_lexicon(lexicon, testwords)

    if verbose:
        logger.info("OK, read")
    return lexicon


class HashableDict(dict):  # noqa: FURB189
    """A dict that's hashable."""

    def __key(self) -> tuple:
        """Return a hashable representation of the dict."""
        return tuple((k, self[k]) for k in sorted(self))

    def __hash__(self) -> int:
        """Return a hash of the dict."""
        return hash(self.__key())

    def __eq__(self, other: "HashableDict") -> bool:
        """Compare two HashableDict objects.

        Args:
            other: The other HashableDict to compare with.

        Returns:
            True if the two HashableDict objects are equal, False otherwise.
        """
        return self.__key() == other.__key()


################################################################################
# Additional utilities
################################################################################


def extract_tags(lexicon: dict) -> set:
    """Extract the set of all tags that are used in a lexicon.

    This was used to create the set of tags for the SALDO model in the tagmappings module.

    Args:
        lexicon: The input lexicon, in the format {wordform: {annotation: set(possible-tags)}}

    Returns:
        A set of all tags used in the lexicon.
    """
    tags = set()
    for annotations in lexicon.values():
        tags.update(*list(annotations.values()))
    return tags
