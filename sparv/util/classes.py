"""Classes used as default input for annotator functions."""
import re
from typing import Optional, List

from sparv.core import config as _config


class Annotation(str):
    """An annotation or attribute used as input."""

    def __new__(_cls, name: str, *args, **kwargs):
        return super().__new__(_cls, name)

    def __init__(self, name: str, data: bool = False, all_docs: bool = False):
        self.data = data
        self.all_docs = all_docs
        Config.parse_config_string(name)


class Output(Annotation):
    """An annotation or attribute used as output."""

    def __init__(self, name: str, cls: Optional[str] = None, data: bool = False, all_docs: bool = False,
                 description: Optional[str] = None):
        self.cls = cls
        self.data = data
        self.all_docs = all_docs
        self.description = description
        Config.parse_config_string(name)


class Document(str):
    """Name of a source document."""

    pass


class Corpus(str):
    """Name of the corpus."""

    pass


class AllDocuments(List[str]):
    """List with names of all source documents."""

    pass


class Config(str):
    """Class holding configuration key names."""

    def __new__(cls, name: str, *args, **kwargs):
        return super().__new__(cls, name)

    def __init__(self, name: str, default: str = None):
        self.default = default
        _config.get(name, default)  # Add to config if not already there

    @staticmethod
    def parse_config_string(string):
        """Parse a string possibly containing references to config variables and add them to the config.

        Args:
            string: The string to parse.
        """
        while True:
            cfgs = list(re.finditer(r"\[([^\]=[]+)(?:=([^\][]+))?\]", string))
            if not cfgs:
                break
            for cfg in cfgs:
                _config.get(cfg.group(1), cfg.group(2).replace("\0", "[").replace("\1", "]") if cfg.group(2) else None)
                string = string.replace(cfg.group(), "\0{}\1".format(cfg.group()[1:-1]))


class Model(str):
    """Path to model file."""

    def __init__(self, value):
        Config.parse_config_string(value)


class Binary(str):
    """Path to binary executable."""

    def __init__(self, value):
        Config.parse_config_string(value)


class Source(str):
    """Path to directory containing input files."""

    pass


class Export(str):
    """Export directory and filename pattern."""

    def __new__(cls, name: str, *args, **kwargs):
        return super().__new__(cls, name)

    def __init__(self, name: str, absolute_path: bool = False):
        self.absolute_path = absolute_path


class ExportInput(str):
    """Export directory and filename pattern, used as input."""

    def __new__(_cls, val: str, *args, **kwargs):
        return super().__new__(_cls, val)

    def __init__(self, val: str, all_docs: bool = False, absolute_path: bool = False):
        self.all_docs = all_docs
        self.absolute_path = absolute_path


class ExportAnnotations(list):
    """List of annotations to include in export."""

    is_input = True

    def __init__(self, items=(), is_input: bool = True):
        list.__init__(self, items)
        self.is_input = is_input


class Language(str):
    """Language of the corpus."""

    pass
