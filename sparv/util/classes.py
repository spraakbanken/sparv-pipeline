"""Classes used as default input for annotator functions."""
from typing import Any, List, Optional


class Annotation(str):
    """An annotation or attribute used as input."""

    def __new__(_cls, name: str, *args, **kwargs):
        return super().__new__(_cls, name)

    def __init__(self, name: str, data: bool = False, all_docs: bool = False, common: bool = False):
        assert not (all_docs and common), "'all_docs' and 'common' are mutually exclusive"
        assert not (common and not data), "'common' requires 'data'"
        self.data = data
        self.all_docs = all_docs
        self.common = common


class Output(Annotation):
    """An annotation or attribute used as output."""

    def __init__(self, name: str, cls: Optional[str] = None, data: bool = False, all_docs: bool = False,
                 common: bool = False, description: Optional[str] = None):
        super().__init__(name, data, all_docs, common)
        self.cls = cls
        self.description = description


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

    def __init__(self, name: str, default: Any = None):
        self.name = name
        self.default = default


class Model(str):
    """Path to model file."""

    pass


class Binary(str):
    """Path to binary executable."""

    pass


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
