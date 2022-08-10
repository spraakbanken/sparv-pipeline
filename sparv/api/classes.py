"""Classes used as default input for annotator functions."""

import gzip
import os
import pathlib
import pickle
import urllib.request
import zipfile
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

import sparv.core
from sparv.core import io
from sparv.core.misc import get_logger
from sparv.core.paths import models_dir

logger = get_logger(__name__)


class Base(ABC):
    """Base class for most Sparv classes."""

    @abstractmethod
    def __init__(self, name: str = ""):
        assert isinstance(name, str)
        self.name = name
        self.original_name = name
        self.root = pathlib.Path.cwd()  # Save current working dir as root

    def expand_variables(self, rule_name: str = "") -> List[str]:
        """Update name by replacing <class> references with annotation names, and [config] references with config values.

        Return a list of any unresolved config references.
        """
        new_value, rest = sparv.core.registry.expand_variables(self.name, rule_name)
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
    all_files = False
    common = False
    is_input = True

    def __init__(self, name: str = "", source_file: Optional[str] = None, is_input: bool = True):
        super().__init__(name)
        self.source_file = source_file
        self.is_input = is_input

    def expand_variables(self, rule_name: str = "") -> List[str]:
        """Update name by replacing <class> references with annotation names, and [config] references with config values.

        Return a list of any unresolved config references.
        """
        new_value, rest = sparv.core.registry.expand_variables(self.name, rule_name, is_annotation=True)
        self.name = new_value
        return rest

    def split(self) -> Tuple[str, str]:
        """Split name into annotation name and attribute."""
        return io.split_annotation(self.name)

    def has_attribute(self) -> bool:
        """Return True if the annotation has an attribute."""
        return io.ELEM_ATTR_DELIM in self.name

    @property
    def annotation_name(self) -> str:
        """Get annotation name (excluding name of any attribute)."""
        return self.split()[0]

    @property
    def attribute_name(self) -> Optional[str]:
        """Get attribute name (excluding name of annotation)."""
        return self.split()[1] or None

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name and self.source_file == other.source_file

    def __hash__(self):
        return hash(repr(self) + repr(self.source_file))


class Annotation(BaseAnnotation):
    """Regular Annotation tied to one source file."""

    def __init__(self, name: str = "", source_file: Optional[str] = None, is_input: bool = True):
        super().__init__(name, source_file=source_file)
        self._size = None
        self.is_input = is_input

    def exists(self) -> bool:
        """Return True if annotation file exists."""
        return io.annotation_exists(self.source_file, self)

    def get_size(self):
        """Get number of values."""
        if self._size is None:
            self._size = io.get_annotation_size(self.source_file, self)
        return self._size

    def read(self, allow_newlines: bool = False):
        """Yield each line from the annotation."""
        return io.read_annotation(self.source_file, self, allow_newlines=allow_newlines)

    def get_children(self, child: BaseAnnotation, orphan_alert=False, preserve_parent_annotation_order=False):
        """Return two lists.

        The first one is a list with n (= total number of parents) elements where every element is a list
        of indices in the child annotation.
        The second one is a list of orphans, i.e. containing indices in the child annotation that have no parent.
        Both parents and children are sorted according to their position in the source file, unless
        preserve_parent_annotation_order is set to True, in which case the parents keep the order from the parent
        annotation.
        """
        parent_spans, child_spans = self.read_parents_and_children(self, child)
        parent_children = []
        orphans = []
        previous_parent_i = None
        try:
            parent_i, parent_span = next(parent_spans)
            parent_children.append((parent_i, []))
        except StopIteration:
            parent_i = None
            parent_span = None

        for child_i, child_span in child_spans:
            if parent_span:
                while child_span[1] > parent_span[1]:
                    previous_parent_i = parent_i
                    try:
                        parent_i, parent_span = next(parent_spans)
                        parent_children.append((parent_i, []))
                    except StopIteration:
                        parent_span = None
                        break
            if parent_span is None or parent_span[0] > child_span[0]:
                if orphan_alert:
                    logger.warning("Child '%s' missing parent; closest parent is %s",
                                   child_i, parent_i or previous_parent_i)
                orphans.append(child_i)
            else:
                parent_children[-1][1].append(child_i)

        # Add rest of parents
        if parent_span is not None:
            for parent_i, parent_span in parent_spans:
                parent_children.append((parent_i, []))

        if preserve_parent_annotation_order:
            # Restore parent order
            parent_children = [p for _, p in sorted(parent_children)]
        else:
            parent_children = [p for _, p in parent_children]

        return parent_children, orphans

    def get_parents(self, parent: BaseAnnotation, orphan_alert: bool = False):
        """Return a list with n (= total number of children) elements where every element is an index in the parent annotation.

        Return None when no parent is found.
        """
        parent_spans, child_spans = self.read_parents_and_children(parent, self)
        child_parents = []
        previous_parent_i = None
        try:
            parent_i, parent_span = next(parent_spans)
        except StopIteration:
            parent_i = None
            parent_span = None

        for child_i, child_span in child_spans:
            while parent_span is not None and child_span[1] > parent_span[1]:
                previous_parent_i = parent_i
                try:
                    parent_i, parent_span = next(parent_spans)
                except StopIteration:
                    parent_span = None
                    break
            if parent_span is None or parent_span[0] > child_span[0]:
                if orphan_alert:
                    logger.warning("Child '%s' missing parent; closest parent is %s",
                                   child_i, parent_i or previous_parent_i)
                child_parents.append((child_i, None))
            else:
                child_parents.append((child_i, parent_i))

        # Restore child order
        child_parents = [p for _, p in sorted(child_parents)]

        return child_parents

    def read_parents_and_children(self, parent: BaseAnnotation, child: BaseAnnotation):
        """Read parent and child annotations.

        Reorder them according to span position, but keep original index information.
        """
        parent_spans = sorted(enumerate(io.read_annotation_spans(self.source_file, parent, decimals=True)), key=lambda x: x[1])
        child_spans = sorted(enumerate(io.read_annotation_spans(self.source_file, child, decimals=True)), key=lambda x: x[1])

        # Only use sub-positions if both parent and child have them
        if parent_spans and child_spans:
            if len(parent_spans[0][1][0]) == 1 or len(child_spans[0][1][0]) == 1:
                parent_spans = [(p[0], (p[1][0][0], p[1][1][0])) for p in parent_spans]
                child_spans = [(c[0], (c[1][0][0], c[1][1][0])) for c in child_spans]

        return iter(parent_spans), iter(child_spans)

    def read_attributes(self, annotations: Union[List[BaseAnnotation], Tuple[BaseAnnotation, ...]],
                        with_annotation_name: bool = False, allow_newlines: bool = False):
        """Yield tuples of multiple attributes on the same annotation."""
        return io.read_annotation_attributes(self.source_file, annotations, with_annotation_name=with_annotation_name,
                                             allow_newlines=allow_newlines)

    def read_spans(self, decimals=False, with_annotation_name=False):
        """Yield the spans of the annotation."""
        return io.read_annotation_spans(self.source_file, self, decimals=decimals,
                                        with_annotation_name=with_annotation_name)

    def create_empty_attribute(self):
        """Return a list filled with None of the same size as this annotation."""
        return [None] * self.get_size()


class AnnotationData(BaseAnnotation):
    """Annotation of the data type, not tied to spans in the corpus text."""

    data = True

    def __init__(self, name: str = "", source_file: Optional[str] = None):
        super().__init__(name, source_file=source_file)

    def read(self, source_file: Optional[str] = None):
        """Read arbitrary string data from annotation file."""
        return io.read_data(self.source_file or source_file, self)

    def exists(self):
        """Return True if annotation file exists."""
        return io.data_exists(self.source_file, self)


class AnnotationAllSourceFiles(BaseAnnotation):
    """Regular annotation but source file must be specified for all actions.

    Use as input to an annotator to require the specificed annotation for every source file in the corpus.
    """

    all_files = True

    def __init__(self, name: str = ""):
        super().__init__(name)
        self._size = {}

    def read(self, source_file: str):
        """Yield each line from the annotation."""
        return io.read_annotation(source_file, self)

    def read_spans(self, source_file: str, decimals=False, with_annotation_name=False):
        """Yield the spans of the annotation."""
        return io.read_annotation_spans(source_file, self, decimals=decimals, with_annotation_name=with_annotation_name)

    @staticmethod
    def read_attributes(source_file: str, annotations: Union[List[BaseAnnotation], Tuple[BaseAnnotation, ...]],
                        with_annotation_name: bool = False, allow_newlines: bool = False):
        """Yield tuples of multiple attributes on the same annotation."""
        return io.read_annotation_attributes(source_file, annotations, with_annotation_name=with_annotation_name,
                                             allow_newlines=allow_newlines)

    def get_size(self, source_file: str):
        """Get number of values."""
        if self._size.get(source_file) is None:
            self._size[source_file] = io.get_annotation_size(source_file, self)
        return self._size[source_file]

    def create_empty_attribute(self, source_file: str):
        """Return a list filled with None of the same size as this annotation."""
        return [None] * self.get_size(source_file)

    def exists(self, source_file: str):
        """Return True if annotation file exists."""
        return io.annotation_exists(source_file, self)


class AnnotationDataAllSourceFiles(BaseAnnotation):
    """Data annotation but source file must be specified for all actions."""

    all_files = True
    data = True

    def __init__(self, name: str = ""):
        super().__init__(name)

    def read(self, source_file: str):
        """Read arbitrary string data from annotation file."""
        return io.read_data(source_file, self)

    def exists(self, source_file: str):
        """Return True if annotation file exists."""
        return io.data_exists(source_file, self)


class AnnotationCommonData(BaseAnnotation):
    """Data annotation for the whole corpus."""

    common = True
    data = True

    def __init__(self, name: str = ""):
        super().__init__(name)

    def read(self):
        """Read arbitrary corpus level string data from annotation file."""
        return io.read_data(None, self)


class BaseOutput(BaseAnnotation):
    """Base class for all Output classes."""

    data = False
    all_files = False
    common = False

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None,
                 source_file: Optional[str] = None):
        super().__init__(name, source_file)
        self.cls = cls
        self.description = description


class Output(BaseOutput):
    """Regular annotation or attribute used as output."""

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None,
                 source_file: Optional[str] = None):
        super().__init__(name, cls, description=description, source_file=source_file)

    def write(self, values, append: bool = False, allow_newlines: bool = False, source_file: Optional[str] = None):
        """Write an annotation to file. Existing annotation will be overwritten.

        'values' should be a list of values.
        """
        io.write_annotation(self.source_file or source_file, self, values, append, allow_newlines)

    def exists(self):
        """Return True if annotation file exists."""
        return io.annotation_exists(self.source_file, self)


class OutputAllSourceFiles(BaseOutput):
    """Regular annotation or attribute used as output, but source file must be specified for all actions."""

    all_files = True

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None):
        super().__init__(name, cls, description=description)

    def write(self, values, source_file: str, append: bool = False, allow_newlines: bool = False):
        """Write an annotation to file. Existing annotation will be overwritten.

        'values' should be a list of values.
        """
        io.write_annotation(source_file, self, values, append, allow_newlines)

    def exists(self, source_file: str):
        """Return True if annotation file exists."""
        return io.annotation_exists(source_file, self)


class OutputData(BaseOutput):
    """Data annotation used as output."""

    data = True

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None,
                 source_file: Optional[str] = None):
        super().__init__(name, cls, description=description, source_file=source_file)

    def write(self, value, append: bool = False):
        """Write arbitrary string data to annotation file."""
        io.write_data(self.source_file, self, value, append)

    def exists(self):
        """Return True if annotation file exists."""
        return io.data_exists(self.source_file, self)


class OutputDataAllSourceFiles(BaseOutput):
    """Data annotation used as output, but source file must be specified for all actions."""

    all_files = True
    data = True

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None):
        super().__init__(name, cls, description=description)

    def read(self, source_file: str):
        """Read arbitrary string data from annotation file."""
        return io.read_data(source_file, self)

    def write(self, value, source_file: str, append: bool = False):
        """Write arbitrary string data to annotation file."""
        io.write_data(source_file, self, value, append)

    def exists(self, source_file: str):
        """Return True if annotation file exists."""
        return io.data_exists(source_file, self)


class OutputCommonData(BaseOutput):
    """Data annotation for the whole corpus."""

    common = True
    data = True

    def __init__(self, name: str = "", cls: Optional[str] = None, description: Optional[str] = None):
        super().__init__(name, cls, description=description)

    def write(self, value, append: bool = False):
        """Write arbitrary corpus level string data to annotation file."""
        io.write_data(None, self, value, append)


class Text:
    """Corpus text."""

    def __init__(self, source_file: Optional[str] = None):
        self.source_file = source_file

    def read(self) -> str:
        """Get corpus text."""
        return io.read_data(self.source_file, io.TEXT_FILE)

    def write(self, text):
        """Write text to the designated file of a corpus.

        text is a unicode string.
        """
        io.write_data(self.source_file, io.TEXT_FILE, text)

    def __repr__(self):
        return "<Text>"


class SourceStructure(BaseAnnotation):
    """Every annotation available in a source file."""

    data = True

    def __init__(self, source_file):
        super().__init__(io.STRUCTURE_FILE, source_file)

    def read(self):
        """Read structure file."""
        return io.read_data(self.source_file, self)

    def write(self, structure):
        """Sort the source file's structural elements and write structure file."""
        structure.sort()
        io.write_data(self.source_file, self, "\n".join(structure))


class Headers(BaseAnnotation):
    """List of header annotation names."""

    data = True

    def __init__(self, source_file):
        super().__init__(io.HEADERS_FILE, source_file)

    def read(self) -> List[str]:
        """Read headers file."""
        return io.read_data(self.source_file, self).splitlines()

    def write(self, header_annotations: List[str]):
        """Write headers file."""
        io.write_data(self.source_file, self, "\n".join(header_annotations))

    def exists(self):
        """Return True if headers file exists."""
        return io.data_exists(self.source_file, self)


class Namespaces(BaseAnnotation):
    """Namespace mapping (URI to prefix) for a source file."""

    data = True

    def __init__(self, source_file):
        super().__init__(io.NAMESPACE_FILE, source_file)

    def read(self):
        """Read namespace file and parse it into a dict."""
        try:
            lines = io.read_data(self.source_file, self).split("\n")
            return dict(l.split(" ") for l in lines)
        except FileNotFoundError:
            return {}

    def write(self, namespaces: Dict[str, str]):
        """Write namespace file."""
        io.write_data(self.source_file, self, "\n".join([f"{k} {v}" for k, v in namespaces.items()]))


class SourceFilename(str):
    """Name of a source file."""


class Corpus(str):
    """Name of the corpus."""


class AllSourceFilenames(List[str]):
    """List with names of all source files."""


class Config(str):
    """Class holding configuration key names."""

    def __new__(cls, name: str, *args, **kwargs):
        return super().__new__(cls, name)

    def __init__(self, name: str, default: Any = None, description: Optional[str] = None):
        self.name = name
        self.default = default
        self.description = description


class Wildcard(str):
    """Class holding wildcard information."""

    ANNOTATION = 1
    ATTRIBUTE = 2
    ANNOTATION_ATTRIBUTE = 3
    OTHER = 0

    def __new__(cls, name: str, *args, **kwargs):
        return super().__new__(cls, name)

    def __init__(self, name: str, type: int = OTHER, description: Optional[str] = None):
        self.name = name
        self.type = type
        self.description = description


class Model(Base):
    """Path to model file."""

    def __init__(self, name):
        super().__init__(name)

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name and self.path == other.path

    @property
    def path(self) -> pathlib.Path:
        """Get model path."""
        return_path = pathlib.Path(self.name)
        # Return as is if path is absolute, models dir is already included, or if relative path to a file that exists
        if return_path.is_absolute() or models_dir in return_path.parents or return_path.is_file():
            return return_path
        else:
            return models_dir / return_path

    def write(self, data):
        """Write arbitrary string data to models directory."""
        file_path = self.path
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data)
        # Update file modification time even if nothing was written
        os.utime(file_path, None)
        logger.info("Wrote %d bytes: %s", len(data), self.name)

    def read(self):
        """Read arbitrary string data from file in models directory."""
        file_path = self.path
        with open(file_path, encoding="utf-8") as f:
            data = f.read()
        logger.debug("Read %d bytes: %s", len(data), self.name)
        return data

    def write_pickle(self, data, protocol=-1):
        """Dump data to pickle file in models directory."""
        file_path = self.path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            pickle.dump(data, f, protocol=protocol)
        # Update file modification time even if nothing was written
        os.utime(file_path, None)
        logger.info("Wrote %d bytes: %s", len(data), self.name)

    def read_pickle(self):
        """Read pickled data from file in models directory."""
        file_path = self.path
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        logger.debug("Read %d bytes: %s", len(data), self.name)
        return data

    def download(self, url: str):
        """Download file from url and save to modeldir."""
        os.makedirs(self.path.parent, exist_ok=True)
        logger.debug("Downloading from: %s", url)
        try:
            urllib.request.urlretrieve(url, self.path)
            logger.info("Successfully downloaded %s", self.name)
        except Exception as e:
            logger.error("Download of %s from %s failed", self.name, url)
            raise e

    def unzip(self):
        """Unzip zip file inside modeldir."""
        out_dir = self.path.parent
        with zipfile.ZipFile(self.path) as z:
            z.extractall(out_dir)
        logger.info("Successfully unzipped %s", self.name)

    def ungzip(self, out: str):
        """Unzip gzip file inside modeldir."""
        with gzip.open(self.path) as z:
            data = z.read()
            with open(out, "wb") as f:
                f.write(data)
        logger.info("Successfully unzipped %s", out)

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


class Source:
    """Path to directory containing input files."""

    def __init__(self, source_dir: str = ""):
        self.source_dir = source_dir

    def get_path(self, source_file: SourceFilename, extension: str):
        """Get the path of a source file."""
        if not extension.startswith("."):
            extension = "." + extension
        if ":" in source_file:
            file_name, _, file_chunk = source_file.partition(":")
            source_file = pathlib.Path(self.source_dir, file_name, file_chunk + extension)
        else:
            source_file = pathlib.Path(self.source_dir, source_file + extension)
        return source_file


class Export(str):
    """Export directory and filename pattern."""


class ExportInput(str):
    """Export directory and filename pattern, used as input."""

    def __new__(_cls, val: str, *args, **kwargs):
        return super().__new__(_cls, val)

    def __init__(self, val: str, all_files: bool = False):
        self.all_files = all_files


class ExportAnnotations(List[Tuple[Annotation, Optional[str]]]):
    """List of annotations to include in export."""

    # If is_input = False the annotations won't be added to the rule's input.
    is_input = True

    def __init__(self, config_name: str, items=(), is_input: bool = True):
        list.__init__(self, items)
        self.config_name = config_name
        self.is_input = is_input


class ExportAnnotationsAllSourceFiles(List[Tuple[AnnotationAllSourceFiles, Optional[str]]]):
    """List of annotations to include in export."""

    # If is_input = False the annotations won't be added to the rule's input.
    is_input = True

    def __init__(self, config_name: str, items=(), is_input: bool = True):
        list.__init__(self, items)
        self.config_name = config_name
        self.is_input = is_input


class SourceAnnotations(List[Tuple[Annotation, Optional[str]]]):
    """List of source annotations to include in export."""

    def __init__(self, config_name: str, items=()):
        list.__init__(self, items)
        self.config_name = config_name


class SourceAnnotationsAllSourceFiles(List[Tuple[AnnotationAllSourceFiles, Optional[str]]]):
    """List of source annotations to include in export."""

    def __init__(self, config_name: str, items=()):
        list.__init__(self, items)
        self.config_name = config_name


class Language(str):
    """Language of the corpus."""


class SourceStructureParser(ABC):
    """Abstract class that should be implemented by an importer's structure parser."""

    def __init__(self, source_dir: pathlib.Path):
        """Initialize class.

        Args:
            source_dir: Path to corpus source files
        """
        self.answers = {}
        self.source_dir = source_dir

        # Annotations should be saved to this variable after the first scan, and read from here
        # on subsequent calls to the get_annotations() and get_plain_annotations() methods.
        self.annotations = None

    def setup(self):
        """Return a list of wizard dictionaries with questions needed for setting up the class.

        Answers to the questions will automatically be saved to self.answers.
        """
        return {}

    @abstractmethod
    def get_annotations(self, corpus_config: dict) -> List[str]:
        """Return a list of annotations including attributes.

        Each value has the format 'annotation:attribute' or 'annotation'.
        Plain versions of each annotation ('annotation' without attribute) must be included as well.
        """
        pass

    def get_plain_annotations(self, corpus_config: dict) -> List[str]:
        """Return a list of plain annotations without attributes.

        Each value has the format 'annotation'.
        """
        return [e for e in self.get_annotations(corpus_config) if ":" not in e]
