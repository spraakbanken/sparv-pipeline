"""Classes used as default input for annotator functions."""

# ruff: noqa: FURB189
from __future__ import annotations

import gzip
import os
import pickle
import time
import zipfile
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from types import UnionType
from typing import Any, Self

import requests

import sparv.core
from sparv.core import io
from sparv.core.misc import get_logger, parse_annotation_list
from sparv.core.paths import paths

logger = get_logger(__name__)


class Base(ABC):
    """Base class for most Sparv classes."""

    @abstractmethod
    def __init__(self, name: str = "") -> None:
        """Initialize class.

        Args:
            name: Name of the annotation/model/etc.
        """
        assert isinstance(name, str), "'name' must be a string"
        self.name = name
        self.original_name = name
        self.root = Path.cwd()  # Save current working dir as root

    def expand_variables(self, rule_name: str = "") -> list[str]:
        """Update name by replacing <class> references with annotation names and [config] references with config values.

        Args:
            rule_name: The name of the rule using the string, for logging config usage.

        Returns:
            A list of any unresolved config references.
        """
        new_value, rest = sparv.core.registry.expand_variables(self.name, rule_name)
        self.name = new_value
        return rest

    def __contains__(self, string: str) -> bool:
        """Check if a string is contained in the name.

        Args:
            string: The string to check for.

        Returns:
            True if the string is contained in the name.
        """
        return string in self.name

    def __str__(self) -> str:
        """Return string representation of the class."""
        return self.__repr__()

    def __repr__(self) -> str:
        """Return string representation of the class."""
        return f"<{self.__class__.__name__} {self.name!r}>"

    def __format__(self, format_spec: str) -> str:
        """Return formatted string representation of the class."""
        return self.name.__format__(format_spec)

    def __lt__(self, other: Base) -> bool:
        """Compare two Base instances by name.

        Args:
            other: Another Base instance to compare with.

        Returns:
            True if self is less than other.
        """
        return self.name < other.name

    def __len__(self) -> int:
        """Return length of name."""
        return len(self.name)

    def __bool__(self) -> bool:
        """Return True if name is not empty."""
        return bool(self.name)


class BaseAnnotation(Base):
    """An annotation or attribute used as input."""

    data = False
    all_files = False
    common = False
    is_input = True

    def __init__(self, name: str = "", source_file: str | None = None, is_input: bool | None = None) -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
            source_file: The name of the source file.
            is_input: Deprecated, use AnnotationName instead of setting this to False.
        """
        super().__init__(name)
        self.source_file = source_file
        if is_input is not None:
            self.is_input = is_input

    def expand_variables(self, rule_name: str = "") -> list[str]:
        """Update name by replacing <class> references with annotation names and [config] references with config values.

        Note:
            This should normally not be used by Sparv modules, as it is not needed.

        Args:
            rule_name: The name of the rule using the string, for logging config usage.

        Returns:
            A list of any unresolved config references.
        """
        new_value, rest = sparv.core.registry.expand_variables(self.name, rule_name, is_annotation=True)
        self.name = new_value
        return rest

    def split(self) -> tuple[str, str]:
        """Split the name into plain annotation name and attribute.

        Returns:
            A tuple with the plain annotation name and attribute name.
        """
        return io.split_annotation(self.name)

    def has_attribute(self) -> bool:
        """Return `True` if the annotation has an attribute."""
        return io.ELEM_ATTR_DELIM in self.name

    @property
    def annotation_name(self) -> str:
        """Retrieve the plain annotation name (excluding name of any attribute).

        Returns:
            The plain annotation name without any attribute.
        """
        return self.split()[0]

    @property
    def attribute_name(self) -> str | None:
        """Retrieve the attribute name (excluding name of the span annotation).

        Returns:
            The attribute name without the name of the span annotation.
        """
        return self.split()[1] or None

    def __eq__(self, other: BaseAnnotation) -> bool:
        """Check if two BaseAnnotation instances are equal.

        Args:
            other: Another BaseAnnotation instance to compare with.

        Returns:
            True if the instances are equal.
        """
        return type(self) is type(other) and self.name == other.name and self.source_file == other.source_file

    def __hash__(self) -> int:
        """Return hash of the class instance."""
        return hash(repr(self) + repr(self.source_file))


class CommonMixin(BaseAnnotation):
    """Common methods used by many classes."""

    def exists(self) -> bool:
        """Return `True` if annotation file exists."""
        return io.annotation_exists(self)

    def remove(self) -> None:
        """Remove the annotation file."""
        io.remove_annotation(self)


class CommonAllSourceFilesMixin(BaseAnnotation):
    """Common methods used by many classes."""

    def exists(self, source_file: str) -> bool:
        """Return `True` if annotation file exists."""
        return io.annotation_exists(self, source_file)

    def remove(self, source_file: str) -> None:
        """Remove the annotation file."""
        io.remove_annotation(self, source_file)


class CommonAnnotationMixin(BaseAnnotation):
    """Methods common to Annotation and AnnotationAllSourceFiles."""

    def __init__(self, name: str = "", source_file: str | None = None) -> None:
        """Initialize class.

        Args:
            name: Name of the annotation.
            source_file: Source file for the annotation.
        """
        super().__init__(name, source_file)
        self._size = {}
        self._corpus_text = {}
        self._data = None

    def _read(self, source_file: str) -> Iterator[str]:
        """Yield each line from the annotation.

        Args:
            source_file: Source file for the annotation.

        Returns:
            An iterator of lines from the annotation.
        """
        return io.read_annotation(source_file, self)

    def _read_spans(
        self, source_file: str, decimals: bool = False, with_annotation_name: bool = False
    ) -> Iterator[tuple]:
        """Yield the spans of the annotation.

        Args:
            source_file: Source file for the annotation.
            decimals: If True, return spans with decimals.
            with_annotation_name: If True, return spans with annotation name.

        Returns:
            An iterator of spans from the annotation.
        """
        return io.read_annotation_spans(source_file, self, decimals=decimals, with_annotation_name=with_annotation_name)

    def _read_text(self, source_file: str) -> Iterator[str]:
        """Get the source text of the annotation.

        Args:
            source_file: Source file for the annotation.

        Yields:
            The source text of the annotation.
        """
        if source_file not in self._corpus_text:
            self._corpus_text[source_file] = io.read_data(source_file, io.TEXT_FILE)
        for start, end in self._read_spans(source_file):
            yield self._corpus_text[source_file][start:end]

    @staticmethod
    def _read_attributes(
        source_file: str,
        annotations: list[BaseAnnotation] | tuple[BaseAnnotation, ...],
        with_annotation_name: bool = False,
    ) -> Iterator[tuple]:
        """Yield tuples of multiple attributes on the same annotation.

        Args:
            source_file: Source file for the annotation.
            annotations: List of annotations to read attributes from.
            with_annotation_name: If True, return attributes with annotation name.

        Returns:
            An iterator of tuples of attributes.
        """
        return io.read_annotation_attributes(source_file, annotations, with_annotation_name=with_annotation_name)

    def _get_size(self, source_file: str) -> int:
        """Get number of values.

        Args:
            source_file: Source file for the annotation.

        Returns:
            The number of values in the annotation.
        """
        if self._size.get(source_file) is None:
            self._size[source_file] = io.get_annotation_size(source_file, self)
        return self._size[source_file]

    def _create_empty_attribute(self, source_file: str) -> list:
        """Return a list filled with None of the same size as this annotation.

        Args:
            source_file: Source file for the annotation.

        Returns:
            A list filled with None of the same size as this annotation.
        """
        return [None] * self._get_size(source_file)

    @staticmethod
    def _read_parents_and_children(
        source_file: str, parent: BaseAnnotation, child: BaseAnnotation
    ) -> tuple[Iterator, Iterator]:
        """Read parent and child annotations.

        Args:
            source_file: Source file for the annotation.
            parent: Parent annotation.
            child: Child annotation.

        Returns:
            A tuple of iterators for parent and child annotations.
        """
        parent_spans = list(io.read_annotation_spans(source_file, parent, decimals=True))
        child_spans = list(io.read_annotation_spans(source_file, child, decimals=True))

        # Only use sub-positions if both parent and child have them
        if parent_spans and child_spans and (len(parent_spans[0][0]) == 1 or len(child_spans[0][0]) == 1):
            parent_spans = [(p[0][0], p[1][0]) for p in parent_spans]
            child_spans = [(c[0][0], c[1][0]) for c in child_spans]

        return iter(parent_spans), iter(child_spans)

    def _get_children(self, source_file: str, child: BaseAnnotation, orphan_alert: bool = False) -> tuple[list, list]:
        """Get children of this annotation.

        Args:
            source_file: Source file for the annotation.
            child: Child annotation.
            orphan_alert: If True, log a warning when a child has no parent.

        Returns:
            A tuple of two lists.
                The first one is a list with n (= total number of parents) elements where every element is a list of
                indices in the child annotation. The second one is a list of orphans, i.e. containing indices in the
                child annotation that have no parent. Both parents and children are sorted according to their position
                in the source file.
        """
        parent_spans, child_spans = self._read_parents_and_children(source_file, self, child)
        parent_children = []
        orphans = []
        previous_parent_span = None
        try:
            parent_span = next(parent_spans)
            parent_children.append([])
        except StopIteration:
            parent_span = None

        for child_i, child_span in enumerate(child_spans):
            if parent_span:
                while child_span[1] > parent_span[1]:
                    previous_parent_span = parent_span
                    try:
                        parent_span = next(parent_spans)
                        parent_children.append([])
                    except StopIteration:
                        parent_span = None
                        break
            if parent_span is None or parent_span[0] > child_span[0]:
                if orphan_alert:
                    logger.warning(
                        "Child '%s' missing parent; closest parent is %s", child_i, parent_span or previous_parent_span
                    )
                orphans.append(child_i)
            else:
                parent_children[-1].append(child_i)

        # Add rest of parents
        if parent_span is not None:
            parent_children.extend([] for _ in parent_spans)

        return parent_children, orphans

    def _get_child_values(
        self, source_file: str, child: BaseAnnotation, append_orphans: bool = False, orphan_alert: bool = False
    ) -> Iterator:
        """Get values of children of this annotation.

        Args:
            source_file: Source file for the annotation.
            child: Child annotation.
            append_orphans: If True, append orphans to the end.
            orphan_alert: If True, log a warning when a child has no parent.

        Yields:
            For each parent, an iterator of values of children of this annotation. If append_orphans is True, the last
            iterator is of orphans.
        """
        child_values = list(child._read(source_file))
        parents, orphans = self._get_children(source_file, child, orphan_alert)
        for parent in parents:
            yield (child_values[child_index] for child_index in parent)
        if append_orphans:
            yield (child_values[child_index] for child_index in orphans)

    def _get_parents(self, source_file: str, parent: BaseAnnotation, orphan_alert: bool = False) -> list:
        """Get parents of this annotation.

        Args:
            source_file: Source file for the annotation.
            parent: Parent annotation.
            orphan_alert: If True, log a warning when a child has no parent.

        Returns:
            A list with n (= total number of children) elements where every element is an index in the parent
                annotation, or None when no parent is found.
        """
        parent_spans, child_spans = self._read_parents_and_children(source_file, parent, self)
        parent_index_spans = enumerate(parent_spans)
        child_parents = []
        previous_parent_span = None
        try:
            parent_i, parent_span = next(parent_index_spans)
        except StopIteration:
            parent_i = None
            parent_span = None

        for child_span in child_spans:
            while parent_span is not None and child_span[1] > parent_span[1]:
                previous_parent_span = parent_span
                try:
                    parent_i, parent_span = next(parent_index_spans)
                except StopIteration:
                    parent_span = None
                    break
            if parent_span is None or parent_span[0] > child_span[0]:
                if orphan_alert:
                    logger.warning(
                        "Child '%s' missing parent; closest parent is %s",
                        child_span,
                        parent_span or previous_parent_span,
                    )
                child_parents.append(None)
            else:
                child_parents.append(parent_i)

        return child_parents


class Annotation(CommonAnnotationMixin, CommonMixin, BaseAnnotation):
    """Regular Annotation tied to one source file.

    This class represents a regular annotation tied to a single source file. It is used when an annotation is required
    as input for a function, for example, `Annotation("<token:word>")`.
    """

    def __iter__(self) -> Iterator[str]:
        """Get an iterator of values from the annotation.

        This is a convenience method equivalent to read().

        Returns:
            An iterator of values from the annotation.
        """
        return self._read(self.source_file)

    def read(self) -> Iterator[str]:
        """Get an iterator of values from the annotation.

        Returns:
            An iterator of values from the annotation.
        """
        return self._read(self.source_file)

    def read_spans(self, decimals: bool = False, with_annotation_name: bool = False) -> Iterator[tuple]:
        """Get an iterator of spans from the annotation.

        Args:
            decimals: If `True`, return spans with decimals.
            with_annotation_name: If `True`, return spans with annotation name.

        Returns:
            An iterator of spans from the annotation.
        """
        return self._read_spans(self.source_file, decimals=decimals, with_annotation_name=with_annotation_name)

    def read_text(self) -> Iterator[str]:
        """Get the source text of the annotation.

        Returns:
            An iterator of the source text of the annotation.
        """
        return self._read_text(self.source_file)

    def read_attributes(
        self, annotations: list[BaseAnnotation] | tuple[BaseAnnotation, ...], with_annotation_name: bool = False
    ) -> Iterator[tuple]:
        """Return an iterator of tuples of multiple attributes on the same annotation.

        Args:
            annotations: List of annotations to read attributes from.
            with_annotation_name: If `True`, return attributes with annotation name.

        Returns:
            An iterator of tuples of attributes.
        """
        return self._read_attributes(self.source_file, annotations, with_annotation_name)

    def get_children(self, child: BaseAnnotation, orphan_alert: bool = False) -> tuple[list, list]:
        """Get children of this annotation.

        Args:
            child: Child annotation.
            orphan_alert: If `True`, log a warning when a child has no parent.

        Returns:
            A tuple of two lists.
                The first one is a list with n (= total number of parents) elements where every element is a list of
                indices in the child annotation. The second one is a list of orphans, i.e. containing indices in the
                child annotation that have no parent. Both parents and children are sorted according to their position
                in the source file.
        """
        return self._get_children(self.source_file, child, orphan_alert)

    def get_child_values(
        self, child: BaseAnnotation, append_orphans: bool = False, orphan_alert: bool = False
    ) -> Iterator[Iterator]:
        """Get values of children of this annotation.

        Args:
            child: Child annotation.
            append_orphans: If `True`, append orphans to the end.
            orphan_alert: If `True`, log a warning when a child has no parent.

        Returns:
            An iterator with one element for each parent. Each element is an iterator of values in the child annotation.
                If `append_orphans` is `True`, the last element is an iterator of orphans.
        """
        return self._get_child_values(self.source_file, child, append_orphans, orphan_alert)

    def get_parents(self, parent: BaseAnnotation, orphan_alert: bool = False) -> list:
        """Get parents of this annotation.

        Args:
            parent: Parent annotation.
            orphan_alert: If `True`, log a warning when a child has no parent.

        Returns:
            A list with n (= total number of children) elements where every element is an index in the parent
                annotation, or `None` when no parent is found.
        """
        return self._get_parents(self.source_file, parent, orphan_alert)

    def read_parents_and_children(self, parent: BaseAnnotation, child: BaseAnnotation) -> tuple[Iterator, Iterator]:
        """Read parent and child annotations.

        Reorders them according to span position, but keeps original index information.

        Args:
            parent: Parent annotation.
            child: Child annotation.

        Returns:
            A tuple of iterators for parent and child annotations.
        """
        return self._read_parents_and_children(self.source_file, parent, child)

    def create_empty_attribute(self) -> list:
        """Return a list filled with `None` of the same size as this annotation."""
        return self._create_empty_attribute(self.source_file)

    def get_size(self) -> int:
        """Get number of values.

        Note:
            This method is deprecated and will be removed in future versions. Use `len()` instead.

        Returns:
            The number of values in the annotation.
        """
        return self._get_size(self.source_file)

    def __len__(self) -> int:
        """Get the number of values in the annotation.

        Returns:
            The number of values in the annotation.
        """
        return self._get_size(self.source_file)


class AnnotationName(BaseAnnotation):
    """Class representing an Annotation name.

    Use this class when only the name of an annotation is needed, not the actual data. The annotation will not be added
    as a prerequisite for the annotator, meaning that using `AnnotationName` will not automatically trigger the creation
    of the referenced annotation.
    """

    is_input = False


class AnnotationData(CommonMixin, BaseAnnotation):
    """Annotation of the data type, for one source file, not tied to spans in the corpus text.

    This class represents an annotation holding arbitrary data, i.e., data that is not tied to spans in the corpus text.
    It is used as input to an annotator.
    """

    data = True

    def __init__(self, name: str = "", source_file: str | None = None) -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
            source_file: The name of the source file.
        """
        super().__init__(name, source_file=source_file)

    def read(self) -> Any:
        """Read arbitrary data from the annotation file.

        Returns:
            The data of the annotation.
        """
        return io.read_data(self.source_file, self)

    def split(self) -> tuple[str, str]:
        """Split the name into plain annotation name and attribute.

        Returns:
            A tuple with the plain annotation name and an empty string.
        """
        return self.name, ""

    @staticmethod
    def has_attribute() -> bool:
        """Return `False` as this class does not have an attribute."""
        return False


class AnnotationAllSourceFiles(CommonAnnotationMixin, CommonAllSourceFilesMixin, BaseAnnotation):
    """Regular annotation but source file must be specified for all actions.

    Like [`Annotation`][sparv.api.classes.Annotation], this class represents a regular annotation, but is used as input
    to an annotator to require the specified annotation for *every source file* in the corpus. By calling an instance of
    this class with a source file name as an argument, you can get an instance of `Annotation` for that source file.

    Note:
        All methods of this class are deprecated and will be removed in a future version of Sparv. Instead, create an
        instance of `Annotation` by passing a source file name as an argument, and use the methods of the `Annotation`
        class.
    """

    all_files = True

    def __init__(self, name: str = "") -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
        """
        super().__init__(name)
        self._size = {}

    def __call__(self, source_file: str) -> Annotation:
        """Get an Annotation instance for the specified source file.

        Args:
            source_file: Source file for the annotation.

        Returns:
            An Annotation instance for the specified source file.
        """
        return Annotation(self.name, source_file)

    def read(self, source_file: str) -> Iterator[str]:
        """Get an iterator of values from the annotation.

        Args:
            source_file: Source file for the annotation.

        Returns:
            An iterator of values from the annotation.
        """
        return self._read(source_file)

    def read_spans(self, source_file: str, decimals: bool = False, with_annotation_name: bool = False) -> Iterator:
        """Get an iterator of spans from the annotation.

        Args:
            source_file: Source file for the annotation.
            decimals: If True, return spans with decimals.
            with_annotation_name: If True, return spans with annotation name.

        Returns:
            An iterator of spans from the annotation.
        """
        return self._read_spans(source_file, decimals=decimals, with_annotation_name=with_annotation_name)

    def read_text(self, source_file: str) -> Iterator[str]:
        """Get the source text of the annotation.

        Args:
            source_file: Source file for the annotation.

        Returns:
            An iterator of the source text of the annotation.
        """
        return self._read_text(source_file)

    def read_attributes(
        self,
        source_file: str,
        annotations: list[BaseAnnotation] | tuple[BaseAnnotation, ...],
        with_annotation_name: bool = False,
    ) -> Iterator:
        """Return an iterator of tuples of multiple attributes on the same annotation.

        Args:
            source_file: Source file for the annotation.
            annotations: List of annotations to read attributes from.
            with_annotation_name: If True, return attributes with annotation name.

        Returns:
            An iterator of tuples of attributes.
        """
        return self._read_attributes(source_file, annotations, with_annotation_name=with_annotation_name)

    def get_children(self, source_file: str, child: BaseAnnotation, orphan_alert: bool = False) -> tuple[list, list]:
        """Get children of this annotation.

        Args:
            source_file: Source file for the annotation.
            child: Child annotation.
            orphan_alert: If True, log a warning when a child has no parent.

        Returns:
            A tuple of two lists.
                The first one is a list with n (= total number of parents) elements where every element is a list of
                indices in the child annotation. The second one is a list of orphans, i.e. containing indices in the
                child annotation that have no parent. Both parents and children are sorted according to their position
                in the source file.
        """
        return self._get_children(source_file, child, orphan_alert)

    def get_child_values(
        self, source_file: str, child: BaseAnnotation, append_orphans: bool = False, orphan_alert: bool = False
    ) -> Iterator[Iterator]:
        """Get values of children of this annotation.

        Args:
            source_file: Source file for the annotation.
            child: Child annotation.
            append_orphans: If True, append orphans to the end.
            orphan_alert: If True, log a warning when a child has no parent.

        Returns:
            An iterator with one element for each parent. Each element is an iterator of values in the child annotation.
                If append_orphans is True, the last element is an iterator of orphans.
        """
        return self._get_child_values(source_file, child, append_orphans, orphan_alert)

    def get_parents(self, source_file: str, parent: BaseAnnotation, orphan_alert: bool = False) -> list:
        """Get parents of this annotation.

        Args:
            source_file: Source file for the annotation.
            parent: Parent annotation.
            orphan_alert: If True, log a warning when a child has no parent.

        Returns:
            A list with n (= total number of children) elements where every element is an index in the parent
                annotation, or None when no parent is found.
        """
        return self._get_parents(source_file, parent, orphan_alert)

    def create_empty_attribute(self, source_file: str) -> list:
        """Return a list filled with None of the same size as this annotation.

        Args:
            source_file: Source file for the annotation.
        """
        return self._create_empty_attribute(source_file)

    def get_size(self, source_file: str) -> int:
        """Get number of values.

        Args:
            source_file: Source file for the annotation.

        Returns:
            The number of values in the annotation.
        """
        return self._get_size(source_file)


class AnnotationDataAllSourceFiles(CommonAllSourceFilesMixin, BaseAnnotation):
    """Data annotation but source file must be specified for all actions.

    Similar to [`AnnotationData`][sparv.api.classes.AnnotationData], this class is used for annotations holding
    arbitrary data, but it is used as input to an annotator to require the specified annotation for *every source file*
    in the corpus. By calling an instance of this class with a source file name as an argument, you can get an instance
    of `AnnotationData` for that source file.

    Note:
        All methods of this class are deprecated and will be removed in a future version of Sparv. Instead, create an
        instance of [`AnnotationData`][sparv.api.classes.AnnotationData] by passing a source file name as an argument,
        and use the methods of the `AnnotationData` class.
    """

    all_files = True
    data = True

    def __init__(self, name: str = "") -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
        """
        super().__init__(name)

    def __call__(self, source_file: str) -> AnnotationData:
        """Get an AnnotationData instance for the specified source file.

        Args:
            source_file: Source file for the annotation.

        Returns:
            An AnnotationData instance for the specified source file.
        """
        return AnnotationData(self.name, source_file)

    def read(self, source_file: str) -> Any:
        """Read arbitrary data from annotation file.

        Args:
            source_file: Source file for the annotation.

        Returns:
            The data of the annotation.
        """
        return io.read_data(source_file, self)

    def split(self) -> tuple[str, str]:
        """Split the name into plain annotation name and attribute.

        Returns:
            A tuple with the plain annotation name and an empty string.
        """
        return self.name, ""

    @staticmethod
    def has_attribute() -> bool:
        """Return `False` as this class does not have an attribute."""
        return False


class AnnotationCommonData(CommonMixin, BaseAnnotation):
    """Data annotation for the whole corpus.

    Like [`AnnotationData`][sparv.api.classes.AnnotationData], this class represents an annotation with arbitrary data
    when used as input to an annotator. However, `AnnotationCommonData` is used for data that applies to the entire
    corpus, not tied to a specific source file.
    """

    common = True
    data = True

    def __init__(self, name: str = "") -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
        """
        super().__init__(name)

    def read(self) -> Any:
        """Read arbitrary corpus-level data from the annotation file.

        Returns:
            The data of the annotation.
        """
        return io.read_data(None, self)

    def split(self) -> tuple[str, str]:
        """Split the name into plain annotation name and attribute.

        Returns:
            A tuple with the plain annotation name and an empty string.
        """
        return self.name, ""

    @staticmethod
    def has_attribute() -> bool:
        """Return `False` as this class does not have an attribute."""
        return False


class Marker(AnnotationCommonData):
    """A marker indicating that something has run.

    Similar to [`AnnotationCommonData`][sparv.api.classes.AnnotationCommonData], but typically without any actual data.
    Used as input. Markers are used to make sure that something has been executed. Created using
    [`OutputMarker`][sparv.api.classes.OutputMarker].
    """

    def __init__(self, name: str = "") -> None:
        """Initialize class.

        Args:
            name: The name of the marker.
        """
        super().__init__(name)

    def read(self) -> Iterator[str]:
        """Read arbitrary corpus-level string data from the marker file.

        Returns:
            An iterator with the data of the marker.
        """
        return super().read()

    def exists(self) -> bool:
        """Return `True` if marker file exists."""
        return super().exists()

    def remove(self) -> None:
        """Remove the marker file."""
        return super().remove()


class MarkerOptional(Marker):
    """Same as [`Marker`][sparv.api.classes.Marker], but if the marker file doesn't exist, it won't be created.

    This is mainly used to get a reference to a marker that may or may not exist, to be able to remove markers from
    connected (un)installers without triggering the connected (un)installation. Otherwise, running an uninstaller
    without first having run the installer would needlessly trigger the installation first.
    """

    is_input = False


class BaseOutput(BaseAnnotation):
    """Base class for all Output classes."""

    data = False
    all_files = False
    common = False

    def __init__(
        self, name: str = "", cls: str | None = None, description: str | None = None, source_file: str | None = None
    ) -> None:
        """Initialize class.

        Args:
            name: Name of the annotation.
            cls: Class of the annotation.
            description: Description of the annotation.
            source_file: Source file for the annotation.
        """
        super().__init__(name, source_file)
        self.cls = cls
        self.description = description


class Output(CommonMixin, BaseOutput):
    """Regular annotation or attribute used as output from an annotator function."""

    def __init__(
        self, name: str = "", cls: str | None = None, description: str | None = None, source_file: str | None = None
    ) -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
            cls: Optional annotation class of the output.
            description: Description of the annotation.
            source_file: The name of the source file.
        """
        super().__init__(name, cls, description=description, source_file=source_file)

    def write(self, values: list) -> None:
        """Write the annotation to a file, overwriting any existing annotation.

        All values will be converted to strings.

        Args:
            values: A list of values.
        """
        io.write_annotation(self.source_file, self, values)


class OutputAllSourceFiles(CommonAllSourceFilesMixin, BaseOutput):
    """Regular annotation or attribute used as output, but not tied to a specific source file.

    Similar to [`Output`][sparv.api.classes.Output], this class represents a regular annotation or attribute used as
    output, but it is used when output should be produced for *every source file* in the corpus. By calling an instance
    of this class with a source file name as an argument, you can get an instance of `Output` for that source file.

    Note:
        All methods of this class are deprecated and will be removed in a future version of Sparv. Instead, create an
        instance of `Output` by passing a source file name as an argument, and use the methods of the `Output` class.
    """

    all_files = True

    def __init__(self, name: str = "", cls: str | None = None, description: str | None = None) -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
            cls: Optional annotation class of the output.
            description: Description of the annotation.
        """
        super().__init__(name, cls, description=description)

    def __call__(self, source_file: str) -> Output:
        """Get an AnnotationData instance for the specified source file.

        Args:
            source_file: Source file for the annotation.

        Returns:
            An Output instance for the specified source file.
        """
        return Output(self.name, source_file=source_file)

    def write(self, values: list, source_file: str) -> None:
        """Write an annotation to file. Existing annotation will be overwritten.

        Args:
            values: A list of values.
            source_file: Source file for the annotation.
        """
        io.write_annotation(source_file, self, values)


class OutputData(CommonMixin, BaseOutput):
    """An annotation holding arbitrary data that is used as output.

    This data is not tied to spans in the corpus text.
    """

    data = True

    def __init__(
        self, name: str = "", cls: str | None = None, description: str | None = None, source_file: str | None = None
    ) -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
            cls: Optional annotation class of the output.
            description: Description of the annotation.
            source_file: The name of the source file.
        """
        super().__init__(name, cls, description=description, source_file=source_file)

    def write(self, value: Any) -> None:
        """Write arbitrary corpus-level string data to the annotation file.

        Args:
            value: The data to write.
        """
        io.write_data(self.source_file, self, value)

    def split(self) -> tuple[str, str]:
        """Split the name into plain annotation name and attribute.

        Returns:
            A tuple with the plain annotation name and an empty string.
        """
        return self.name, ""

    @staticmethod
    def has_attribute() -> bool:
        """Return `False` as this class does not have an attribute."""
        return False


class OutputDataAllSourceFiles(CommonAllSourceFilesMixin, BaseOutput):
    """Data annotation used as output, not tied to a specific source file.

    Similar to [`OutputData`][sparv.api.classes.OutputData], this class is used for output annotations holding arbitrary
    data, but it is used when output should be produced for *every source file* in the corpus. By calling an instance of
    this class with a source file name as an argument, you can get an instance of `OutputData` for that source file.

    Note:
        All methods of this class are deprecated and will be removed in a future version of Sparv. Instead, create an
        instance of `OutputData` by passing a source file name as an argument, and use the methods of the `OutputData`
        class.
    """

    all_files = True
    data = True

    def __init__(self, name: str = "", cls: str | None = None, description: str | None = None) -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
            cls: Optional annotation class of the output.
            description: Description of the annotation.
        """
        super().__init__(name, cls, description=description)

    def __call__(self, source_file: str) -> OutputData:
        """Get an OutputData instance for the specified source file.

        Args:
            source_file: Source file for the annotation.

        Returns:
            An OutputData instance for the specified source file.
        """
        return OutputData(self.name, source_file=source_file)

    def read(self, source_file: str) -> Any:
        """Read arbitrary string data from annotation file.

        Args:
            source_file: Source file for the annotation.

        Returns:
            The data of the annotation.
        """
        return io.read_data(source_file, self)

    def write(self, value: Any, source_file: str) -> None:
        """Write arbitrary data to annotation file.

        Args:
            value: The data to write.
            source_file: Source file for the annotation.
        """
        io.write_data(source_file, self, value)

    def split(self) -> tuple[str, str]:
        """Split the name into plain annotation name and attribute.

        Returns:
            A tuple with the plain annotation name and an empty string.
        """
        return self.name, ""

    @staticmethod
    def has_attribute() -> bool:
        """Return `False` as this class does not have an attribute."""
        return False


class OutputCommonData(CommonMixin, BaseOutput):
    """Data annotation for the whole corpus.

    Similar to [`OutputData`][sparv.api.classes.OutputData], but for a data annotation that applies to the entire
    corpus.
    """

    common = True
    data = True

    def __init__(self, name: str = "", cls: str | None = None, description: str | None = None) -> None:
        """Initialize class.

        Args:
            name: The name of the annotation.
            cls: Optional annotation class of the output.
            description: Description of the annotation.
        """
        super().__init__(name, cls, description=description)

    def write(self, value: Any) -> None:
        """Write arbitrary corpus-level data to the annotation file.

        Args:
            value: The data to write.
        """
        io.write_data(None, self, value)

    def split(self) -> tuple[str, str]:
        """Split the name into plain annotation name and attribute.

        Returns:
            A tuple with the plain annotation name and an empty string.
        """
        return self.name, ""

    @staticmethod
    def has_attribute() -> bool:
        """Return `False` as this class does not have an attribute."""
        return False


class OutputMarker(OutputCommonData):
    """A class for creating a marker, indicating that something has run.

    Similar to [`OutputCommonData`][sparv.api.classes.OutputCommonData], but typically without any actual data. Markers
    are used to indicate that something has been executed, often by functions that don't produce a natural output, such
    as installers and uninstallers.
    """

    def __init__(self, name: str = "", cls: str | None = None, description: str | None = None) -> None:
        """Initialize class.

        Args:
            name: The name of the marker.
            cls: Optional annotation class of the output.
            description: Description of the annotation.
        """
        super().__init__(name, cls, description)

    def write(self, value: str = "") -> None:
        """Create a marker, indicating that something has run.

        This is used by functions that don't have any natural output, like installers and uninstallers.

        Args:
            value: The data to write. Usually this should be left out.
        """
        # Write current timestamp, as Snakemake also compares checksums for small files, not just modified time
        super().write(value or str(time.time()))


class Text:
    """Represents the text content of a source file."""

    def __init__(self, source_file: str | None = None) -> None:
        """Initialize class.

        Args:
            source_file: The name of the source file.
        """
        self.source_file = source_file

    def read(self) -> str:
        """Get the text content of the source file.

        Returns:
            The corpus text.
        """
        return io.read_data(self.source_file, io.TEXT_FILE)

    def write(self, text: str) -> None:
        """Write the provided text content to a file, overwriting any existing content.

        Args:
            text: The text to write. Should be a unicode string.
        """
        io.write_data(self.source_file, io.TEXT_FILE, text)

    def __repr__(self) -> str:
        """Return class name as string representation of the class."""
        return "<Text>"


class SourceStructure(BaseAnnotation):
    """Every annotation name available in a source file."""

    data = True

    def __init__(self, source_file: str) -> None:
        """Initialize class.

        Args:
            source_file: Name of the source file.
        """
        super().__init__(io.STRUCTURE_FILE, source_file)

    def read(self) -> list[str]:
        """Read structure file to get a list of names of annotations in the source file.

        Returns:
            A list of annotation names.
        """
        return io.read_data(self.source_file, self).split("\n")

    def write(self, structure: list[str]) -> None:
        """Sort the source file's structural elements and write structure file.

        Args:
            structure: A list of annotation names.
        """
        structure.sort()
        io.write_data(self.source_file, self, "\n".join(structure))


class Headers(CommonMixin, BaseAnnotation):
    """List of header annotation names.

    Represents a list of header annotation names for a given source file, used as output for importers.
    """

    data = True

    def __init__(self, source_file: str) -> None:
        """Initialize class.

        Args:
            source_file: The name of the source file.
        """
        super().__init__(io.HEADERS_FILE, source_file)

    def read(self) -> list[str]:
        """Read the headers file and return a list of header annotation names.

        Returns:
            A list of header annotation names.
        """
        return io.read_data(self.source_file, self).splitlines()

    def write(self, header_annotations: list[str]) -> None:
        """Write the headers file with the provided list of header annotation names.

        Args:
            header_annotations: A list of header annotation names.
        """
        io.write_data(self.source_file, self, "\n".join(header_annotations))

    def exists(self) -> bool:
        """Return `True` if the headers file exists for this source file."""
        return super().exists()

    def remove(self) -> None:
        """Remove the headers file."""
        return super().remove()

    def split(self) -> tuple[str, str]:
        """Split the name into plain annotation name and attribute.

        Returns:
            A tuple with the plain annotation name and an empty string.
        """
        return self.name, ""


class Namespaces(BaseAnnotation):
    """Namespace mapping (URI to prefix) for a source file."""

    data = True

    def __init__(self, source_file: str) -> None:
        """Initialize class.

        Args:
            source_file: Source file for the annotation.
        """
        super().__init__(io.NAMESPACE_FILE, source_file)

    def read(self) -> dict[str, str]:
        """Read namespace file and parse it into a dict.

        Returns:
            A dict with prefixes as keys and URIs as values.
        """
        try:
            lines = io.read_data(self.source_file, self).split("\n")
            return dict(l.split(" ") for l in lines)
        except FileNotFoundError:
            return {}

    def write(self, namespaces: dict[str, str]) -> None:
        """Write namespace file.

        Args:
            namespaces: A dict with prefixes as keys and URIs as values.
        """
        io.write_data(self.source_file, self, "\n".join([f"{k} {v}" for k, v in namespaces.items()]))


class SourceFilename(str):
    """A string representing the name of a source file."""


class Corpus(str):
    """A string representing the name (ID) of a corpus."""


class AllSourceFilenames(Sequence[str]):
    """List with names of all source files.

    This class provides an iterable containing the names of all source files. It is commonly used by exporter
    functions that need to combine annotations from multiple source files.
    """

    def __init__(self) -> None:
        """Initialize class."""
        self.items: Sequence[str] = []

    def __getitem__(self, index: int) -> str:
        """Return item at index."""
        return self.items[index]

    def __len__(self) -> int:
        """Return number of source files."""
        return len(self.items)


class Config(Any):
    """Class holding configuration key names.

    This class represents a configuration key and optionally its default value. You can specify the datatype and allowed
    values, which will be used for validating the config and generating the Sparv config JSON schema.

    For further information on how to use this class, see the [Config
    Parameters](writing-sparv-plugins.md#config-parameters) section.
    """

    def __init__(
        self,
        name: str,
        default: Any = None,
        description: str | None = None,
        datatype: type | UnionType | None = None,
        choices: Iterable | Callable | None = None,
        pattern: str | None = None,
        min_len: int | None = None,
        max_len: int | None = None,
        min_value: int | float | None = None,
        max_value: int | float | None = None,
        const: Any | None = None,
        conditions: list[Config] | None = None,
    ) -> None:
        """Initialize class.

        Args:
            name: The name of the configuration key.
            default: The optional default value of the configuration key.
            description: A mandatory description of the configuration key.
            datatype: A type specifying the allowed datatype(s). Supported types are `int`, `float`, `str`, `bool`,
                `None`, `type(None)`, `list`, and `dict`. For `list` and `dict`, you can specify the allowed types for
                the elements by using type arguments, like `list[str]` or `dict[str, int]`. Union types are supported,
                e.g., `int | str`. More complex types (e.g., further nesting) than these are not supported. `type(None)`
                is used to allow `None` as a value. `None` is the default value, and means that any datatype is allowed.
            choices: An iterable of valid choices, or a function that returns such an iterable.
            pattern: A regular expression matching valid values (only for the datatype `str`).
            min_len: An `int` representing the minimum length of the value.
            max_len: An `int` representing the maximum length of the value.
            min_value: An `int` or `float` representing the minimum numeric value.
            max_value: An `int` or `float` representing the maximum numeric value.
            const: Restrict the value to a constant.
            conditions: A list of `Config` objects with conditions that must also be met.
        """
        self.name = name
        self.default = default
        self.description = description
        self.datatype = datatype
        self.choices = choices
        self.pattern = pattern
        self.min_len = min_len
        self.max_len = max_len
        self.min_value = min_value
        self.max_value = max_value
        self.const = const
        self.conditions = conditions or []


class Wildcard(str):
    """Class holding wildcard information.

    Typically used in the `wildcards` list passed as an argument to the [`@annotator`
    decorator](sparv-decorators.md#annotator), e.g.:

    ```python
    @annotator("Number {annotation} by relative position within {parent}", wildcards=[
        Wildcard("annotation", Wildcard.ANNOTATION),
        Wildcard("parent", Wildcard.ANNOTATION)
    ])
    ```
    """

    ANNOTATION = 1
    ATTRIBUTE = 2
    ANNOTATION_ATTRIBUTE = 3
    OTHER = 0

    def __new__(cls, name: str, *args: Any, **kwargs: Any) -> Self:  # noqa: ARG004
        """Create a new instance of the class.

        Args:
            cls: The class to create an instance of.
            name: The name of the wildcard.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        return super().__new__(cls, name)

    def __init__(self, name: str, type: int = OTHER, description: str | None = None) -> None:  # noqa: A002
        """Initialize class.

        Args:
            name: The name of the wildcard.
            type: The type of the wildcard, by reference to the constants defined in this class
                (`Wildcard.ANNOTATION`, `Wildcard.ATTRIBUTE`, `Wildcard.ANNOTATION_ATTRIBUTE`,
                or `Wildcard.OTHER`). `Wildcard.ANNOTATION` is used for annotation names (spans), `Wildcard.ATTRIBUTE`
                is used for attribute names, and `Wildcard.ANNOTATION_ATTRIBUTE` is used for wildcards that cover both
                the annotation name and an attribute. `Wildcard.OTHER` is used for other types of wildcards, unrelated
                to annotations or attributes.
            description: The description of the wildcard.
        """
        self.name = name
        self.type = type
        self.description = description


class Model(Base):
    """Path to a model file.

    Represents a path to a model file. The path can be either an absolute path, a relative path, or a path relative to
    the Sparv model directory. Typically used as input to annotator functions.
    """

    def __init__(self, name: str) -> None:
        """Initialize class.

        Args:
            name: The path of the model file.
        """
        super().__init__(name)

    def __eq__(self, other: Model) -> bool:
        """Check if two Model instances are equal.

        Args:
            other: Another Model instance to compare with.

        Returns:
            True if the instances are equal.
        """
        return type(self) is type(other) and self.name == other.name and self.path == other.path

    def __hash__(self) -> int:
        """Return a hash of the Model instance.

        Returns:
            The hash of the Model instance.
        """
        return hash((self.name, self.path))

    @property
    def path(self) -> Path:
        """Get model path.

        Returns:
            Get the path to the model file as a `Path` object.
        """
        return_path = Path(self.name)
        # Return as is, if path is absolute, models dir is already included, or if relative path to a file that exists
        if return_path.is_absolute() or paths.models_dir in return_path.parents or return_path.is_file():
            return return_path
        else:  # noqa: RET505
            return paths.models_dir / return_path

    def write(self, data: str) -> None:
        """Write arbitrary string data to the model file.

        Args:
            data: The data to write.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(data, encoding="utf-8")

        # Update file modification time even if nothing was written
        os.utime(self.path, None)
        logger.info("Wrote %d bytes: %s", len(data), self.name)

    def read(self) -> str:
        """Read arbitrary string data from the model file.

        Returns:
            The data of the model.
        """
        data = self.path.read_text(encoding="utf-8")
        logger.debug("Read %d bytes: %s", len(data), self.name)
        return data

    def write_pickle(self, data: Any, protocol: int = -1) -> None:
        """Dump arbitrary data to the model file in pickle format.

        Args:
            data: The data to write.
            protocol: Pickle protocol to use.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("wb") as f:
            pickle.dump(data, f, protocol=protocol)
        # Update file modification time even if nothing was written
        os.utime(self.path, None)
        logger.info("Wrote %d bytes: %s", len(data), self.name)

    def read_pickle(self) -> Any:
        """Read pickled data from model file.

        Returns:
            The data of the model.
        """
        with self.path.open("rb") as f:
            data = pickle.load(f)
        logger.debug("Read %d bytes: %s", len(data), self.name)
        return data

    def download(self, url: str) -> None:
        """Download the file from the given URL and save to the model path.

        Args:
            url: URL to download from.
        """

        def log_progress(downloaded: int, total_size: int) -> None:
            if total_size > 0:
                logger.progress(progress=downloaded, total=total_size)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Downloading from: %s", url)
        try:
            with requests.get(url, timeout=30, stream=True) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                with self.path.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # Filter out keep-alive chunks
                            file.write(chunk)
                            downloaded += len(chunk)
                            log_progress(downloaded, total_size)
            logger.info("Successfully downloaded %s", self.name)
        except Exception as e:
            logger.error("Download of %s from %s failed", self.name, url)
            raise e

    def unzip(self) -> None:
        """Unzip zip file in same directory as the model file."""
        out_dir = self.path.parent
        with zipfile.ZipFile(self.path) as z:
            z.extractall(out_dir)
        logger.info("Successfully unzipped %s", self.name)

    def ungzip(self, out: str) -> None:
        """Unzip gzip file in same directory as the model file.

        Args:
            out: Path to output file.
        """
        with gzip.open(self.path) as z:
            data = z.read()
            with Path(out).open("wb") as f:
                f.write(data)
        logger.info("Successfully unzipped %s", out)

    def remove(self, raise_errors: bool = False) -> None:
        """Remove model file from disk.

        Args:
            raise_errors: If `True`, raise an error if the file cannot be removed (e.g., if it doesn't exist).
        """
        self.path.unlink(missing_ok=not raise_errors)


class ModelOutput(Model):
    """Same as [`Model`][sparv.api.classes.Model], but used as the output of a model builder."""

    def __init__(self, name: str, description: str | None = None) -> None:
        """Initialize class.

        Args:
            name: The name of the model file.
            description: Description of the model.
        """
        super().__init__(name)
        self.description = description


class Binary(str):
    """Path to binary executable.

    This class holds the path to a binary executable. The path can be either the name of a binary in the system's
    `PATH`, a full path to a binary, or a path relative to the Sparv data directory. It is often used to define a
    prerequisite for an annotator function.

    Args:
        object: Path to the binary executable.
    """


class BinaryDir(str):
    """Path to directory containing executable binaries.

    This class holds the path to a directory containing executable binaries. The path can be either an absolute path or
    a path relative to the Sparv data directory.

    Args:
        object: Path to the directory containing the executable binaries.
    """


class Source:
    """Path to the directory containing source files."""

    def __init__(self, source_dir: str = "") -> None:
        """Initialize class.

        Args:
            source_dir: Path to the directory containing source files. Should usually be left blank, for Sparv to
                automatically get the path.
        """
        self.source_dir = source_dir

    def get_path(self, source_file: SourceFilename, extension: str) -> Path:
        """Get the path of a specific source file.

        Args:
            source_file: The name of the source file.
            extension: File extension to append to the source file.

        Returns:
            The path to the source file.
        """
        if not extension.startswith("."):
            extension = "." + extension
        if ":" in source_file:
            file_name, _, file_chunk = source_file.partition(":")
            source_file = Path(self.source_dir, file_name, file_chunk + extension)
        else:
            source_file = Path(self.source_dir, source_file + extension)
        return source_file


class Export(str):
    """A string containing the path to an export directory and filename.

    Represents an export file, used to define the output of an exporter function.

    Args:
        object: The export directory and filename. The export directory must include the module name as a prefix or be
            equal to the module name. The filename may include the wildcard `{file}` which will be replaced with the
            name of the source file. For example: `"xml_export.pretty/{file}_export.xml"`.
    """


class ExportInput(str):
    """Export directory and filename pattern, used as input.

    Represents the export directory and filename pattern used as input. Use this class when you need export files as
    input for another function.
    """

    def __new__(cls, val: str, *args: Any, **kwargs: Any) -> Self:  # noqa: ARG004
        """Create a new instance of the class.

        Args:
            cls: The class to create an instance of.
            val: The export directory and filename pattern (e.g., `"xml_export.pretty/{file}_export.xml"`).
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        return super().__new__(cls, val)

    def __init__(self, val: str, all_files: bool = False) -> None:  # noqa: ARG002
        """Initialize class.

        Args:
            val: The export directory and filename pattern (e.g., `"xml_export.pretty/{file}_export.xml"`).
            all_files: Set to `True` to get the export for all source files.
        """
        self.all_files = all_files


class ExportAnnotations(Sequence[tuple[Annotation, str | None]]):
    """Iterable with annotations to include in export.

    An iterable containing annotations to be included in the export, as specified in the corpus configuration. When
    using this class, annotation files for the current source file are automatically added as dependencies.
    """

    # If is_input = False the annotations won't be added to the rule's input.
    is_input = True

    def __init__(self, config_name: str, is_input: bool | None = None) -> None:
        """Initialize class.

        Args:
            config_name: The configuration variable specifying which annotations to include.
            is_input: Deprecated, use `ExportAnnotationNames` instead of setting this to `False`.
        """
        self.config_name = config_name
        self.items = []
        if is_input is not None:
            self.is_input = is_input

    def __getitem__(self, index: int) -> tuple[Annotation, str | None]:
        """Return item at index.

        Each item is a tuple of an Annotation and an optional export name.
        """
        return self.items[index]

    def __len__(self) -> int:
        """Return number of annotations."""
        return len(self.items)


class ExportAnnotationNames(ExportAnnotations):
    """List of annotations to include in export.

    An iterable containing annotations to be included in the export, as specified in the corpus configuration. Unlike
    `ExportAnnotations`, using this class will not add the annotations as dependencies. Use this class when you only
    need the annotation names, not the actual annotation files.
    """

    is_input = False

    def __init__(self, config_name: str) -> None:
        """Initialize class.

        Args:
            config_name: The configuration variable specifying which annotations to include.
        """
        super().__init__(config_name)


class ExportAnnotationsAllSourceFiles(Sequence[tuple[AnnotationAllSourceFiles, str | None]]):
    """List of annotations to include in export.

    An iterable containing annotations to be included in the export, as specified in the corpus configuration. When
    using this class, annotation files for *all* source files will automatically be added as dependencies.
    """

    # Always true for ExportAnnotationsAllSourceFiles
    is_input = True

    def __init__(self, config_name: str) -> None:
        """Initialize class.

        Args:
            config_name: The configuration variable specifying which annotations to include.
        """
        self.config_name = config_name
        self.items: Sequence[tuple[AnnotationAllSourceFiles, str | None]] = []

    def __getitem__(self, index: int) -> tuple[AnnotationAllSourceFiles, str | None]:
        """Return item at index."""
        return self.items[index]

    def __len__(self) -> int:
        """Return number of annotations."""
        return len(self.items)


class SourceAnnotations(Sequence[tuple[Annotation, str | None]]):
    """An iterable containing source annotations to include in the export, as specified in the corpus configuration."""

    def __init__(self, config_name: str, source_file: str | None = None, _headers: bool = False) -> None:
        """Initialize class.

        Args:
            config_name: The configuration variable specifying which source annotations to include.
            source_file: The name of the source file.
            _headers: If `True`, read headers instead of source structure.
        """
        self.config_name = config_name
        self.raw_list = None
        self.annotations: Sequence[tuple[Annotation, str | None]] = []
        self.source_file = source_file
        self.initialized = False
        self.headers = _headers

    def _initialize(self) -> None:
        """Populate class with data."""
        assert self.source_file, "SourceAnnotation is missing source_file"

        # If raw_list is an empty list, don't add any source annotations automatically
        if not self.raw_list and self.raw_list is not None:
            self.initialized = True
            return

        # Parse annotation list and read available source annotations
        if self.headers:
            h = Headers(self.source_file)
            available_source_annotations = h.read() if h.exists() else []
        else:
            available_source_annotations = SourceStructure(self.source_file).read()
        parsed_items = parse_annotation_list(self.raw_list, available_source_annotations)
        # Only include annotations that are available in source
        self.annotations = [
            (Annotation(a[0], self.source_file), a[1]) for a in parsed_items if a[0] in available_source_annotations
        ]
        self.initialized = True

    def __getitem__(self, index: int) -> tuple[Annotation, str | None]:
        """Return item at index."""
        if not self.initialized:
            self._initialize()
        return self.annotations[index]

    def __len__(self) -> int:
        """Return number of annotations."""
        if not self.initialized:
            self._initialize()
        return len(self.annotations)


class HeaderAnnotations(SourceAnnotations):
    """Header annotations to include in export.

    An iterable containing header annotations from the source to be included in the export, as specified in the corpus
    configuration.
    """

    def __init__(self, config_name: str, source_file: str | None = None) -> None:
        """Initialize class.

        Args:
            config_name: The configuration variable that specifies which header annotations to include.
            source_file: Name of the source file.
        """
        super().__init__(config_name, source_file, _headers=True)


class SourceAnnotationsAllSourceFiles(Sequence[tuple[AnnotationAllSourceFiles, str | None]]):
    """Iterable with source annotations to include in export.

    An iterable containing source annotations to include in the export, as specified in the corpus configuration. Unlike
    `SourceAnnotations`, this class ensures that the source annotations structure file (created using `SourceStructure`)
    for *every* source file is added as a dependency.
    """

    def __init__(self, config_name: str, source_files: Iterable[str] = (), headers: bool = False) -> None:
        """Initialize class.

        Args:
            config_name: The configuration variable specifying which source annotations to include.
            source_files: List of source file names.
            headers: If `True`, read headers instead of source structure.
        """
        self.config_name = config_name
        self.raw_list = None
        self.annotations: Sequence[tuple[AnnotationAllSourceFiles, str | None]] = []
        self.source_files = source_files
        self.initialized = False
        self.headers = headers

    def _initialize(self) -> None:
        """Populate class with data."""
        assert self.source_files, "SourceAnnotationsAllSourceFiles is missing source_files"

        # If raw_list is an empty list, don't add any source annotations automatically
        if not self.raw_list and self.raw_list is not None:
            self.initialized = True

        # Parse annotation list and, if needed, read available source annotations
        available_source_annotations = set()
        for f in self.source_files:
            if self.headers:
                h = Headers(f)
                if h.exists():
                    available_source_annotations.update(h.read())
            else:
                available_source_annotations.update(SourceStructure(f).read())

        parsed_items = parse_annotation_list(self.raw_list, available_source_annotations)
        # Only include annotations that are available in source
        self.annotations = [
            (AnnotationAllSourceFiles(a[0]), a[1]) for a in parsed_items if a[0] in available_source_annotations
        ]
        self.initialized = True

    def __getitem__(self, index: int) -> tuple[AnnotationAllSourceFiles, str | None]:
        """Return item at index."""
        if not self.initialized:
            self._initialize()
        return self.annotations[index]

    def __len__(self) -> int:
        """Return number of annotations."""
        if not self.initialized:
            self._initialize()
        return len(self.annotations)


class HeaderAnnotationsAllSourceFiles(SourceAnnotationsAllSourceFiles):
    """Header annotations to include in export.

    An iterable containing header annotations from all source files to be included in the export, as specified in the
    corpus configuration. Unlike `HeaderAnnotations`, this class ensures that the header annotations file (created using
    `Headers`) for *every* source file is added as a dependency.
    """

    def __init__(self, config_name: str, source_files: Iterable[str] = ()) -> None:
        """Initialize class.

        Args:
            config_name: The configuration variable specifying which source annotations to include.
            source_files: List of source files (internal use only).
        """
        super().__init__(config_name, source_files, headers=True)


class Language(str):
    """The language of the corpus.

    An instance of this class contains information about the language of the corpus. This information is retrieved from
    the corpus configuration and is specified using an ISO 639-1 language code.
    """


class SourceStructureParser(ABC):
    """Abstract class that should be implemented by an importer's structure parser.

    Note:
        This class is intended to be used by the wizard. The wizard functionality is going to be deprecated in a future
        version.
    """

    def __init__(self, source_dir: Path) -> None:
        """Initialize class.

        Args:
            source_dir: Path to corpus source files.
        """
        self.answers = {}
        self.source_dir = source_dir

        # Annotations should be saved to this variable after the first scan, and read from here
        # on subsequent calls to the get_annotations() and get_plain_annotations() methods.
        self.annotations = None

    @staticmethod
    def setup() -> dict:
        """Return a list of wizard dictionaries with questions needed for setting up the class.

        Answers to the questions will automatically be saved to self.answers.
        """
        return {}

    @abstractmethod
    def get_annotations(self, corpus_config: dict) -> list[str]:
        """Return a list of annotations including attributes.

        Each value has the format 'annotation:attribute' or 'annotation'.
        Plain versions of each annotation ('annotation' without attribute) must be included as well.
        """

    def get_plain_annotations(self, corpus_config: dict) -> list[str]:
        """Return a list of plain annotations without attributes.

        Each value has the format 'annotation'.
        """
        return [e for e in self.get_annotations(corpus_config) if ":" not in e]
