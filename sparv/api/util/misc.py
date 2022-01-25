"""Misc util functions."""

import pathlib
import re
import unicodedata
from collections import OrderedDict, defaultdict
from typing import List, Optional, Tuple, Union

from sparv.api import get_logger
from sparv.api.classes import Annotation, Model

logger = get_logger(__name__)


def parse_annotation_list(annotation_names: Optional[List[str]], all_annotations: Optional[List[str]] = None,
                          add_plain_annotations: bool = True) -> List[Tuple[str, Optional[str]]]:
    """Take a list of annotation names and possible export names, and return a list of tuples.

    Each list item will be split into a tuple by the string ' as '.
    Each tuple will contain 2 elements. If there is no ' as ' in the string, the second element will be None.

    If there is an element called '...' everything from all_annotations will be included in the result, except for
    the elements that are prefixed with 'not '.

    If an annotation occurs more than once in the list, only the last occurrence will be kept. Similarly, if an
    annotation is first included and then excluded (using 'not') it will be excluded from the result.

    If a plain annotation (without attributes) is excluded, all its attributes will be excluded as well.

    Plain annotations (without attributes) will be added if needed, unless add_plain_annotations is set to False.
    Make sure to disable add_plain_annotations if the annotation names may include classes or config variables.
    """
    if all_annotations is None:
        all_annotations = []
    if not annotation_names:
        return [(a, None) for a in all_annotations]

    plain_annotations = set()
    possible_plain_annotations = set()
    omit_annotations = set()
    include_rest = False
    plain_to_atts = defaultdict(list)

    result: OrderedDict = OrderedDict()
    for a in annotation_names:
        # Check if this annotation should be omitted
        if a.startswith("not ") and " as " not in a:
            omit_annotations.add(a[4:])
        elif a == "...":
            include_rest = True
        else:
            name, _, export_name = a.partition(" as ")
            if not re.match(r"^<[^>]+>$", name):  # Prevent splitting class names
                plain_name, attr = Annotation(name).split()
            else:
                plain_name, attr = None, None
            result.pop(name, None)
            result[name] = export_name or None
            if attr:
                possible_plain_annotations.add(plain_name)
                plain_to_atts[plain_name].append(name)
            else:
                plain_annotations.add(name)

    # If only exclusions have been listed, include rest of annotations
    if omit_annotations and not result:
        include_rest = True

    # Add all_annotations to result if required
    if include_rest and all_annotations:
        for a in [a for a in all_annotations if not a in omit_annotations]:
            if a not in result:
                result[a] = None
                plain_name, _ = Annotation(a).split()
                plain_to_atts[plain_name].append(a)
                plain_annotations.add(plain_name)

    # Add annotations names without attributes to result if required
    if add_plain_annotations:
        for a in sorted(possible_plain_annotations.difference(plain_annotations)):
            if a not in result:
                result[a] = None

    # Remove any exclusions from final list
    if omit_annotations:
        for annotation in omit_annotations:
            result.pop(annotation, None)
            # If we're excluding a plain annotation, also remove all attributes connected to it
            for a in plain_to_atts[annotation]:
                result.pop(a, None)

    return list(result.items())


# TODO: Split into two functions: one for Sparv-internal lists of values, and one used by the CWB module to create the
# CWB-specific set format.
def cwbset(values, delimiter="|", affix="|", sort=False, maxlength=4095, encoding="UTF-8"):
    """Take an iterable object and return a set in the format used by Corpus Workbench."""
    values = list(values)
    if sort:
        values.sort()
    if maxlength:
        length = 1  # Including the last affix
        for i, value in enumerate(values):
            length += len(value.encode(encoding)) + 1
            if length > maxlength:
                values = values[:i]
                break
    return affix if not values else affix + delimiter.join(values) + affix


def set_to_list(setstring, delimiter="|", affix="|"):
    """Turn a set string into a list."""
    if setstring == affix:
        return []
    setstring = setstring.strip(affix)
    return setstring.split(delimiter)


def remove_control_characters(text, keep: Optional[str] = None):
    """Remove control characters from text, except for those in 'keep'."""
    if keep is None:
        keep = ["\n", "\t", "\r"]
    return "".join(c for c in text if c in keep or unicodedata.category(c)[0:2] != "Cc")


def remove_formatting_characters(text, keep: Optional[str] = None):
    """Remove formatting characters from text, except for those in 'keep'."""
    if keep is None:
        keep = []
    return "".join(c for c in text if c in keep or unicodedata.category(c)[0:2] != "Cf")


def chain(annotations, default=None):
    """Create a functional composition of a list of annotations.

    E.g., token.sentence + sentence.id -> token.sentence-id

    >>> from pprint import pprint
    >>> pprint(dict(
    ...   chain([{"w:1": "s:A",
    ...           "w:2": "s:A",
    ...           "w:3": "s:B",
    ...           "w:4": "s:C",
    ...           "w:5": "s:missing"},
    ...          {"s:A": "text:I",
    ...           "s:B": "text:II",
    ...           "s:C": "text:mystery"},
    ...          {"text:I": "The Bible",
    ...           "text:II": "The Samannaphala Sutta"}],
    ...         default="The Principia Discordia")))
    {'w:1': 'The Bible',
     'w:2': 'The Bible',
     'w:3': 'The Samannaphala Sutta',
     'w:4': 'The Principia Discordia',
     'w:5': 'The Principia Discordia'}
    """
    def follow(key):
        for annot in annotations:
            try:
                key = annot[key]
            except KeyError:
                return default
        return key
    return ((key, follow(key)) for key in annotations[0])


def test_lexicon(lexicon: dict, testwords):
    """Test the validity of a lexicon.

    Takes a dictionary ('lexicon') and a list of test words that are expected to occur as keys in 'lexicon'.
    Prints the value for each test word.
    """
    logger.info("Testing annotations...")
    for key in testwords:
        logger.info("  %s = %s", key, lexicon.get(key))


class PickledLexicon:
    """Read basic pickled lexicon and look up keys."""

    def __init__(self, picklefile: Union[pathlib.Path, Model], verbose=True):
        """Read lexicon from picklefile."""
        import pickle
        picklefile_path: pathlib.Path = picklefile.path if isinstance(picklefile, Model) else picklefile
        if verbose:
            logger.info("Reading lexicon: %s", picklefile)
        with open(picklefile_path, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            logger.info("OK, read %d words", len(self.lexicon))

    def lookup(self, key, default=set()):
        """Lookup a key in the lexicon."""
        return self.lexicon.get(key, default)


def indent_xml(elem, level=0, indentation="  ") -> None:
    """Add pretty-print indentation to XML tree.

    From http://effbot.org/zone/element-lib.htm#prettyprint
    """
    i = "\n" + level * indentation
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indentation
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent_xml(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
