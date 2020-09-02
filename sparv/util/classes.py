"""Classes used as default input for annotator functions."""

import gzip
import logging
import os
import pathlib
import pickle
import urllib.request
import zipfile
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Union

import sparv.core
from sparv.core.paths import models_dir
from sparv.util import corpus
from sparv.util import parent as parents

log = logging.getLogger(__name__)


class Base(ABC):
    """Base class for most Sparv classes."""

    @abstractmethod
    def __init__(self, name: str = ""):
        assert isinstance(name, str)
        self.name = name
        self.original_name = name

    def expand_variables(self, module_name: str = "") -> List[str]:
        """Update annotation name by replacing <class> references with real annotations, and [config] references with config values.

        Return a list of any unresolved config references.
        """
        new_value, rest = sparv.core.registry.expand_variables(self.name, module_name)
        self.name = new_value
        return rest

    def __contains__(self, string):
        return string in self.name

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __format__(self, format_spec):
        return self.name.__format__(format_spec)

    def __lt__(self, other):
        return self.name < other.name

    def __len__(self):
        return len(self.name)


class BaseAnnotation(Base):
    """An annotation or attribute used as input."""

    data = False
    all_docs = False
    common = False

    def __init__(self, name: str = "", doc: Optional[str] = None):
        super().__init__(name)
        self.doc = doc

    def split(self) -> Tuple[str, str]:
        """Split name into annotation name and attribute."""
        return corpus.split_annotation(self.name)

    def has_attribute(self) -> bool:
        """Return True if the annotation has an attribute."""
        return corpus.has_attribute(self.name)

    def annotation_name(self) -> str:
        """Get annotation name (excluding name of any attribute)."""
        return self.split()[0]

    def attribute_name(self) -> Optional[str]:
        """Get attribute name (excluding name of annotation)."""
        return self.split()[1] or None

    def __eq__(self, other):
        return (type(self) == type(other) and self.name == other.name and self.doc == other.doc
                and self.data == other.data and self.all_docs == other.all_docs and self.common == other.common)


class Annotation(BaseAnnotation):
    """Regular Annotation tied to one document."""

    def __init__(self, name: str = "", doc: Optional[str] = None):
        super().__init__(name, doc=doc)

    def exists(self) -> bool:
        """Return True if annotation file exists."""
        return corpus.annotation_exists(self.doc, self.name)

    def read(self):
        """Yield each line from the annotation."""
        return corpus.read_annotation(self.doc, self.name)

    def get_children(self, child: BaseAnnotation, orphan_alert=False, preserve_parent_annotation_order=False):
        """Return two lists.

        The first one is a list with n (= total number of parents) elements where every element is a list
        of indices in the child annotation.
        The second one is a list of orphans, i.e. containing indices in the child annotation that have no parent.
        Both parents and children are sorted according to their position in the source document, unless
        preserve_parent_annotation_order is set to True, in which case the parents keep the order from the parent
        annotation.
        """
        return parents.get_children(self.doc, self.name, child.name, orphan_alert=orphan_alert,
                                    preserve_parent_annotation_order=preserve_parent_annotation_order)

    def get_parents(self, parent: BaseAnnotation, orphan_alert: bool = False):
        """Return a list with n (= total number of children) elements where every element is an index in the parent annotation.

        Return None when no parent is found.
        """
        return parents.get_parents(self.doc, parent.name, self.name, orphan_alert=orphan_alert)

    def read_attributes(self, annotations: Union[List[BaseAnnotation], Tuple[BaseAnnotation, ...]],
                        with_annotation_name: bool = False, allow_newlines: bool = False):
        """Yield tuples of multiple attributes on the same annotation."""
        annotation_names = [a.name for a in annotations]
        return corpus.read_annotation_attributes(self.doc, annotation_names, with_annotation_name=with_annotation_name,
                                                 allow_newlines=allow_newlines)

    def read_spans(self, decimals=False, with_annotation_name=False):
        """Yield the spans of the annotation."""
        return corpus.read_annotation_spans(self.doc, self.name, decimals=decimals,
                                            with_annotation_name=with_annotation_name)

    def create_empty_attribute(self):
        """Return a list filled with None of the same size as this annotation."""
        return corpus.create_empty_attribute(self)


class AnnotationData(BaseAnnotation):
    """Annotation of the data type, not tied to spans in the corpus text."""

    data = True

    def __init__(self, name: str = "", doc: Optional[str] = None):
        super().__init__(name, doc=doc)

    def read(self, doc: Optional[str] = None):
        """Read arbitrary string data from annotation file."""
        return corpus.read_data(self.doc or doc, self.name)

    def exists(self):
        """Return True if annotation file exists."""
        return corpus.data_exists(self.doc, self.name)


class AnnotationAllDocs(BaseAnnotation):
    """Regular annotation but document must be specified for all actions.

    Use as input to an annotator to require the specificed annotation for every document in the corpus.
    """

    all_docs = True

    def __init__(self, name: str = ""):
        super().__init__(name)

    def read(self, doc: str):
        """Yield each line from the annotation."""
        return corpus.read_annotation(doc, self.name)

    def read_spans(self, doc: str, decimals=False, with_annotation_name=False):
        """Yield the spans of the annotation."""
        return corpus.read_annotation_spans(doc, self.name, decimals=decimals,
                                            with_annotation_name=with_annotation_name)

    def create_empty_attribute(self, doc: str):
        """Return a list filled with None of the same size as this annotation."""
        return corpus.create_empty_attribute(self.read_spans(doc))

    def exists(self, doc: str):
        """Return True if annotation file exists."""
        return corpus.annotation_exists(doc, self.name)


class AnnotationDataAllDocs(BaseAnnotation):
    """Data annotation but document must be specified for all actions."""

    all_docs = True
    data = True

    def __init__(self, name: str = ""):
        super().__init__(name)

    def read(self, doc: str):
        """Read arbitrary string data from annotation file."""
        return corpus.read_data(doc, self.name)

    def exists(self, doc: str):
        """Return True if annotation file exists."""
        return corpus.data_exists(doc, self.name)


class AnnotationCommonData(BaseAnnotation):
    """Data annotation for the whole corpus."""

    common = True
    data = True

    def __init__(self, name: str = ""):
        super().__init__(name)

    def read(self):
        """Read arbitrary corpus level string data from annotation file."""
        return corpus.read_common_data(self.name)


class BaseOutput(BaseAnnotation):
    """Base class for all Output classes."""

    data = False
    all_docs = False
    common = False

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None,
                 doc: Optional[str] = None):
        super().__init__(name, doc)
        self.cls = cls
        self.description = description


class Output(BaseOutput):
    """Regular annotation or attribute used as output."""

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None,
                 doc: Optional[str] = None):
        super().__init__(name, cls, description=description, doc=doc)

    def write(self, values, append: bool = False, allow_newlines: bool = False, doc: Optional[str] = None):
        """Write an annotation to file. Existing annotation will be overwritten.

        'values' should be a list of values.
        """
        corpus.write_annotation(self.doc or doc, self.name, values, append, allow_newlines)

    def exists(self):
        """Return True if annotation file exists."""
        return corpus.annotation_exists(self.doc, self.name)


class OutputAllDocs(BaseOutput):
    """Regular annotation or attribute used as output, but document must be specified for all actions."""

    all_docs = True

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None):
        super().__init__(name, cls, description=description)

    def write(self, values, doc: str, append: bool = False, allow_newlines: bool = False):
        """Write an annotation to file. Existing annotation will be overwritten.

        'values' should be a list of values.
        """
        corpus.write_annotation(doc, self.name, values, append, allow_newlines)

    def exists(self, doc: str):
        """Return True if annotation file exists."""
        return corpus.annotation_exists(doc, self.name)


class OutputData(BaseOutput):
    """Data annotation used as output."""

    data = True

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None,
                 doc: Optional[str] = None):
        super().__init__(name, cls, description=description, doc=doc)

    def write(self, value, append: bool = False):
        """Write arbitrary string data to annotation file."""
        corpus.write_data(self.doc, self.name, value, append)

    def exists(self):
        """Return True if annotation file exists."""
        return corpus.data_exists(self.doc, self.name)


class OutputDataAllDocs(BaseOutput):
    """Data annotation used as output, but document must be specified for all actions."""

    all_docs = True
    data = True

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None):
        super().__init__(name, cls, description=description)

    def write(self, value, doc: str, append: bool = False):
        """Write arbitrary string data to annotation file."""
        corpus.write_data(doc, self, value, append)

    def exists(self, doc: str):
        """Return True if annotation file exists."""
        return corpus.data_exists(doc, self.name)


class OutputCommonData(BaseOutput):
    """Data annotation for the whole corpus."""

    common = True
    data = True

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None):
        super().__init__(name, cls, description=description)

    def write(self, value, append: bool = False):
        """Write arbitrary corpus level string data to annotation file."""
        corpus.write_common_data(self, value, append)


class Text:
    """Corpus text."""

    def __init__(self, doc: Optional[str] = None):
        self.doc = doc

    def read(self) -> str:
        """Get corpus text."""
        return corpus.read_corpus_text(self.doc)


class Document(str):
    """Name of a source document."""


class Corpus(str):
    """Name of the corpus."""


class AllDocuments(List[str]):
    """List with names of all source documents."""


class Config(str):
    """Class holding configuration key names."""

    def __new__(cls, name: str, *args, **kwargs):
        return super().__new__(cls, name)

    def __init__(self, name: str, default: Any = None):
        self.name = name
        self.default = default


class Model(Base):
    """Path to model file."""

    def __init__(self, name):
        super().__init__(name)

    @property
    def path(self) -> pathlib.Path:
        """Get model path."""
        return_path = pathlib.Path(self.name)
        # Check if name already includes full path to models dir
        if models_dir in return_path.parents:
            return return_path
        else:
            return models_dir / return_path

    def write_data(self, data):
        """Write arbitrary string data to models directory."""
        file_path = self.path
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(data)
        # Update file modification time even if nothing was written
        os.utime(file_path, None)
        log.info("Wrote %d bytes: %s", len(data), self.name)

    def read_data(self):
        """Read arbitrary string data from file in models directory."""
        file_path = self.path
        with open(file_path) as f:
            data = f.read()
        log.info("Read %d bytes: %s", len(data), self.name)
        return data

    def write_pickle(self, data, protocol=-1):
        """Dump data to pickle file in models directory."""
        file_path = self.path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            pickle.dump(data, f, protocol=protocol)
        # Update file modification time even if nothing was written
        os.utime(file_path, None)
        log.info("Wrote %d bytes: %s", len(data), self.name)

    def read_pickle(self):
        """Read pickled data from file in models directory."""
        file_path = self.path
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        log.info("Read %d bytes: %s", len(data), self.name)
        return data

    def download(self, url: str):
        """Download file from url and save to modeldir/filename."""
        os.makedirs(self.path.parent, exist_ok=True)
        try:
            urllib.request.urlretrieve(url, self.path)
            log.info("Successfully downloaded %s", self.name)
        except Exception as e:
            log.error("Download from %s failed", url)
            raise e

    def unzip(self):
        """Unzip zip file inside modeldir."""
        out_dir = self.path.parent
        with zipfile.ZipFile(self.path) as z:
            z.extractall(out_dir)
        log.info("Successfully unzipped %s", self.name)

    def ungzip(self, out: str):
        """Unzip gzip file inside modeldir."""
        with gzip.open(self.path) as z:
            data = z.read()
            with open(out, "wb") as f:
                f.write(data)
        log.info("Successfully unzipped %s", out)

    def remove(self, raise_errors: bool = False):
        """Remove model file from disk."""
        try:
            os.remove(self.path)
        except FileNotFoundError as e:
            if raise_errors:
                raise e


class ModelOutput(Model):
    """Path to model file used as output of a modelbuilder."""

    def __init__(self, name: str, description: Optional[str] = None):
        super().__init__(name)
        self.description = description


class Binary(str):
    """Path to binary executable."""


class BinaryDir(str):
    """Path to directory containing executable binaries."""


class Source(str):
    """Path to directory containing input files."""


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


class ExportAnnotations(List[Tuple[Annotation, Optional[str]]]):
    """List of annotations to include in export."""

    is_input = True

    def __init__(self, export_type: str, items=(), is_input: bool = True):
        list.__init__(self, items)
        self.export_type = export_type
        self.is_input = is_input


class ExportAnnotationsAllDocs(List[Tuple[AnnotationAllDocs, Optional[str]]]):
    """List of annotations to include in export."""

    is_input = True

    def __init__(self, export_type: str, items=(), is_input: bool = True):
        list.__init__(self, items)
        self.export_type = export_type
        self.is_input = is_input


class Language(str):
    """Language of the corpus."""
