from typing import Optional, List

from sparv.core import config as _config


class Annotation(str):
    """An annotation or attribute."""
    def __new__(_cls, name: str, *args, **kwargs):
        return super().__new__(_cls, name)

    def __init__(self, name: str, data: bool = False):
        self.source = name
        self.data = data


class Output(Annotation):
    """An annotation or attribute used as output."""
    def __init__(self, name: str, cls: Optional[str] = None, data: bool = False, description: Optional[str] = None):
        self.source = name
        self.cls = cls
        self.data = data
        self.description = description


class Document(str):
    """A source document."""
    pass


class Corpus(str):
    """Name of the corpus."""
    pass


class AllDocuments(List[str]):
    """All source documents."""
    pass


class Config(str):
    """Class holding configuration key names."""

    def __new__(cls, name: str, *args, **kwargs):
        return super().__new__(cls, name)

    def __init__(self, name: str, default: str = None):
        self.default = default
        _config.get(name, default)  # Add to config if not already there


class Model(str):
    """Path to model file."""
    pass


class Binary(str):
    """Path to binary executable."""
    pass


class Source(str):
    """Source path of XML files."""
    pass


class Export(str):
    """Export path."""
    pass


class ExportAnnotations(List[Annotation]):
    """List of annotations to include in export."""
    pass
