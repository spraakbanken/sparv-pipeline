"""`sparv.api.util.misc` provides miscellaneous util functions."""

from __future__ import annotations

import pathlib
import pickle
import unicodedata
from collections.abc import Generator, Iterable
from typing import Any

import yaml

from sparv.api import get_logger
from sparv.api.classes import Model
from sparv.core.misc import parse_annotation_list  # noqa: F401 - Imported to make available through the API

logger = get_logger(__name__)


def dump_yaml(data: dict, resolve_alias: bool = False, sort_keys: bool = False, indent: int = 2) -> str:
    """Convert a dictionary to a YAML formatted string.

    Args:
        data: The dictionary to be converted.
        resolve_alias: Whether to replace aliases with their anchor's content.
        sort_keys: Whether to sort the keys alphabetically.
        indent: The number of spaces to use for indentation.

    Returns:
        The YAML document as a string.
    """

    class IndentDumper(yaml.SafeDumper):
        """Customized YAML dumper that indents lists."""

        def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:  # noqa: ARG002
            """Force indentation."""
            return super().increase_indent(flow)

    def str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
        """Custom string representer for prettier multiline strings."""  # noqa: DOC201
        if "\n" in data:  # Check for multiline string
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    def obj_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
        """Custom representer to cast subclasses of str to strings."""  # noqa: DOC201
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))

    yaml.representer.SafeRepresenter.add_representer(str, str_representer)
    yaml.representer.SafeRepresenter.add_multi_representer(str, obj_representer)

    if resolve_alias:
        # Resolve aliases and replace them with their anchors' contents
        yaml.SafeDumper.ignore_aliases = lambda *_args: True

    return yaml.dump(
        data, sort_keys=sort_keys, allow_unicode=True, Dumper=IndentDumper, indent=indent, default_flow_style=False
    )


# TODO: Split into two functions: one for Sparv-internal lists of values, and one used by the CWB module to create the
# CWB-specific set format.
def cwbset(
    values: Iterable[str],
    delimiter: str = "|",
    affix: str = "|",
    sort: bool = False,
    maxlength: int = 4095,
    encoding: str = "UTF-8",
) -> str:
    """Take an iterable with strings and return a set in the format used by Corpus Workbench.

    Args:
        values: An iterable containing string values.
        delimiter: The delimiter to be used between the values.
        affix: The affix enclosing the resulting string.
        sort: Whether to sort the values before joining them.
        maxlength: Maximum length of the resulting string.
        encoding: Encoding to use when calculating the length of the string.

    Returns:
        The joined string.
    """
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


def set_to_list(setstring: str, delimiter: str = "|", affix: str = "|") -> list[str]:
    """Convert a set-formatted string into a list.

    Args:
        setstring: The string to convert into a list. The string should be enclosed with `affix` characters and have
            elements separated by `delimiter`.
        delimiter: The character used to separate elements in `setstring`.
        affix: The character that encloses `setstring`.

    Returns:
        A list of strings.
    """
    if setstring == affix:
        return []
    setstring = setstring.strip(affix)
    return setstring.split(delimiter)


def remove_control_characters(text: str, keep: Iterable[str] = ("\n", "\t", "\r")) -> str:
    """Remove control characters from the given text, except for those specified in `keep`.

    The characters removed are those with the Unicode category "Cc" (control characters).
    https://www.unicode.org/reports/tr44/#GC_Values_Table

    Args:
        text: The string from which to remove control characters.
        keep: An iterable of characters to keep. Default is newline, tab, and carriage return.

    Returns:
        The text with control characters removed.
    """
    return "".join(c for c in text if c in keep or unicodedata.category(c) != "Cc")


def remove_formatting_characters(text: str, keep: Iterable[str] = ()) -> str:
    """Remove formatting characters from the given text, except for those specified in 'keep'.

    The characters removed are those with the Unicode category "Cf" (formatting characters).
    https://www.unicode.org/reports/tr44/#GC_Values_Table

    Args:
        text: The text from which to remove formatting characters.
        keep: An iterable of characters to keep.

    Returns:
        The text with formatting characters removed.
    """
    if keep is None:
        keep = []
    return "".join(c for c in text if c in keep or unicodedata.category(c) != "Cf")


def normalize_space_separators(text: str, keep: Iterable[str] = ()) -> str:
    """Replace any space separators with regular spaces.

    The characters replaced are those with the Unicode category "Zs" (space separators), except for regular spaces and
    those specified in 'keep'.
    https://www.unicode.org/reports/tr44/#GC_Values_Table

    Args:
        text: The text to normalize.
        keep: An iterable of characters to keep.

    Returns:
        The text with space separators replaced with regular spaces.
    """
    if keep is None:
        keep = []
    return "".join(c if c in keep or unicodedata.category(c) != "Zs" else " " for c in text)


def remove_unassigned_characters(text: str, keep: Iterable[str] = ()) -> str:
    """Remove unassigned characters from the given text, except for those specified in 'keep'.

    The characters removed are those with the Unicode category "Cn" (unassigned characters).
    https://www.unicode.org/reports/tr44/#GC_Values_Table

    Args:
        text: The text from which to remove unassigned characters.
        keep: An iterable of characters to keep.

    Returns:
        The text with unassigned characters removed.
    """
    if keep is None:
        keep = []
    return "".join(c for c in text if c in keep or unicodedata.category(c) != "Cn")


def chain(annotations: Iterable[dict], default: Any = None) -> Generator[tuple]:
    """Create a functional composition of a list of annotations.

    Args:
        annotations: A list of dictionaries where each dictionary maps keys to values. The values are keys in the next
            dictionary, except for the last dictionary where the values are the final values.
        default: The default value to return if a key is not found.

    Returns:
        A generator that yields tuples with the original key and the final value.

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

    def follow(key: Any) -> Any:
        for annot in annotations:
            try:
                key = annot[key]
            except KeyError:
                return default
        return key

    return ((key, follow(key)) for key in annotations[0])


def test_lexicon(lexicon: dict, testwords: Iterable[str]) -> None:
    """Test the validity of a lexicon by checking if specific test words are present as keys.

    This function takes a dictionary (lexicon) and a list of test words, printing the value associated with each test
    word.

    Args:
        lexicon: A dictionary representing the lexicon.
        testwords: An iterable of strings, each expected to be a key in the lexicon.
    """
    logger.info("Testing annotations...")
    for key in testwords:
        logger.info("  %s = %s", key, lexicon.get(key))


class PickledLexicon:
    """A class for reading a basic pickled lexicon and looking up keys."""

    def __init__(self, picklefile: pathlib.Path | Model, verbose: bool = True) -> None:
        """Read lexicon from a pickled file.

        Args:
            picklefile: A `pathlib.Path` or `Model` object pointing to the pickled lexicon.
            verbose: Whether to log status updates while reading the lexicon.
        """
        picklefile_path: pathlib.Path = picklefile.path if isinstance(picklefile, Model) else picklefile
        if verbose:
            logger.info("Reading lexicon: %s", picklefile)
        with picklefile_path.open("rb") as f:
            self.lexicon = pickle.load(f)
        if verbose:
            logger.info("OK, read %d words", len(self.lexicon))

    def lookup(self, key: Any, default: Any = None) -> Any:
        """Lookup a key in the lexicon.

        Args:
            key: The key to look up.
            default: The default value to return if the key is not found.

        Returns:
            The value for the key, or the default value if the key is not found.
        """
        return self.lexicon.get(key, default)


def get_language_name_by_part3(part3: str) -> str | None:
    """Return language name in English given an ISO 639-3 code.

    Args:
        part3: ISO 639-3 code.

    Returns:
        Language name in English.
    """
    import pycountry  # noqa: PLC0415

    lang = pycountry.languages.get(alpha_3=part3)
    return lang.name if lang else None


def get_language_part1_by_part3(part3: str) -> str | None:
    """Return ISO 639-1 code given an ISO 639-3 code.

    Args:
        part3: ISO 639-3 code.

    Returns:
        ISO 639-1 code.
    """
    import pycountry  # noqa: PLC0415

    lang = pycountry.languages.get(alpha_3=part3)
    return lang.alpha_2 if lang else None
