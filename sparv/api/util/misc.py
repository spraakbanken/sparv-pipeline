"""Misc util functions."""

import pathlib
import unicodedata
from typing import Optional, Union

import pycountry
import yaml

from sparv.api import get_logger
from sparv.api.classes import Model
from sparv.core.misc import parse_annotation_list  # noqa

logger = get_logger(__name__)


def dump_yaml(data: dict, resolve_alias: bool = False, sort_keys: bool = False, indent: int = 2) -> str:
    """Convert a dict to a YAML document string.

    Args:
        data: The data to be dumped.
        resolve_alias: Will replace aliases with their anchor's content if set to True.
        sort_keys: Whether to sort the keys alphabetically.
        indent: Number of spaces used for indentation.
    """

    class IndentDumper(yaml.SafeDumper):
        """Customized YAML dumper that indents lists."""

        def increase_indent(self, flow=False, indentless=False):
            """Force indentation."""
            return super(IndentDumper, self).increase_indent(flow)

    def str_representer(dumper, data):
        """Custom string representer for prettier multiline strings."""
        if "\n" in data:  # Check for multiline string
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    def obj_representer(dumper, data):
        """Custom representer to cast subclasses of str to strings."""
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))

    yaml.representer.SafeRepresenter.add_representer(str, str_representer)
    yaml.representer.SafeRepresenter.add_multi_representer(str, obj_representer)

    if resolve_alias:
        # Resolve aliases and replace them with their anchors' contents
        yaml.SafeDumper.ignore_aliases = lambda *args: True

    return yaml.dump(
        data, sort_keys=sort_keys, allow_unicode=True, Dumper=IndentDumper, indent=indent, default_flow_style=False
    )


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


def get_language_name_by_part3(part3: str) -> Optional[str]:
    """Return language name in English given an ISO 639-3 code."""
    lang = pycountry.languages.get(alpha_3=part3)
    return lang.name if lang else None


def get_language_part1_by_part3(part3: str) -> Optional[str]:
    """Return ISO 639-1 code given an ISO 639-3 code."""
    lang = pycountry.languages.get(alpha_3=part3)
    return lang.alpha_2 if lang else None
