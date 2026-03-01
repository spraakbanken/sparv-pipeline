"""Miscellaneous classes and methods."""

from __future__ import annotations

import logging
import re
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from typing import cast

from sparv.core.logger import SparvLogger, ensure_logger_class


class SparvErrorMessage(Exception):  # noqa: N818
    """Exception used to notify users of errors in a friendly way without displaying a traceback."""

    start_marker = "<<<START>>>"
    end_marker = "<<<END>>>"

    def __init__(self, message: str, module: str = "", function: str = "") -> None:
        """Raise an error and notify the user of the problem in a friendly way.

        This exception is handled by Sparv, automatically halting the pipeline and displaying the error message to the
        user in a user-friendly way, without displaying a traceback.

        Args:
            message: User-friendly error message to display.
            module: The name of the module where the error occurred (optional, not used in Sparv modules).
            function: The name of the function where the error occurred (optional, not used in Sparv modules).
        """
        self.message = message
        # Alter message before calling base class
        super().__init__(
            f"{SparvErrorMessage.start_marker}{module}\n{function}\n{message}{SparvErrorMessage.end_marker}"
        )


def get_logger(name: str) -> SparvLogger:
    """Get a logger that is a child of 'sparv.modules'.

    Logging in Sparv modules should always be done using the logger returned by this function.

    Args:
        name: The name of the current module (usually `__name__`).

    Returns:
        Logger object.
    """
    ensure_logger_class()
    if not name.startswith("sparv.modules"):
        name = f"sparv.modules.{name}"
    return cast(SparvLogger, logging.getLogger(name))


def parse_annotation_list(
    annotation_names: Iterable[str] | None,
    all_annotations: Iterable[str] | None = None,
    add_plain_annotations: bool = True,
) -> list[tuple[str, str | None]]:
    """Take a list of annotation names and possible export names, and return a list of tuples.

    Each item in the list is split into a tuple by the string ' as '. Each tuple will contain two elements. If ' as ' is
    not present in the string, the second element will be `None`.

    If the list of annotation names includes the element '...', all annotations from `all_annotations` will be included
    in the result, except those explicitly excluded in the list of annotations by being prefixed with 'not '.

    If an annotation occurs more than once in the list, only the last occurrence will be kept. Similarly, if an
    annotation is first included and then excluded (using 'not'), it will be excluded from the result.

    If a plain annotation (without attributes) is excluded, all its attributes will be excluded as well.

    Plain annotations (without attributes) will be added if needed, unless add_plain_annotations is set to False.
    Make sure to disable add_plain_annotations if the annotation names may include classes or config variables.

    Args:
        annotation_names: A list of annotation names.
        all_annotations: A list of all possible annotations.
        add_plain_annotations: If `True`, plain annotations (without attributes) will be added if needed. Set to `False`
            if annotation names may include classes or config variables.

    Returns:
        A list of tuples with annotation names and export names.
    """
    from sparv.api import Annotation  # noqa: PLC0415 - Avoid circular import

    if all_annotations is None:
        all_annotations = []
    if not annotation_names:
        return [(a, None) for a in all_annotations]

    plain_annotations = set()
    possible_plain_annotations = set()
    omit_annotations = set()
    include_rest = False
    plain_to_atts = defaultdict(set)

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
            result.pop(name, None)  # Remove any previous occurrence first, to keep the order
            result[name] = export_name or None
            if attr:
                possible_plain_annotations.add(plain_name)
                plain_to_atts[plain_name].add(name)
            else:
                plain_annotations.add(name)

    # If only exclusions have been listed, include the rest of the annotations
    if omit_annotations and not result:
        include_rest = True

    # Add all_annotations to result if required
    if include_rest and all_annotations:
        for a in all_annotations:
            if a not in result and a not in omit_annotations:
                result[a] = None
                plain_name, attr = Annotation(a).split()
                if attr:
                    plain_to_atts[plain_name].add(a)
                plain_annotations.add(plain_name)

    # Add annotation names without attributes to result if required
    if add_plain_annotations:
        new_plain_annotations = possible_plain_annotations.difference(plain_annotations)
        if omit_annotations:
            # Don't add new plain annotation if all connected attributes have been omitted
            for annotation in omit_annotations:
                plain_name, _ = Annotation(annotation).split()
                plain_to_atts[plain_name].discard(annotation)

        for a in sorted(new_plain_annotations):
            if a not in result and plain_to_atts[a]:
                result[a] = None

    # Remove any exclusions from the final list
    if omit_annotations:
        for annotation in omit_annotations:
            result.pop(annotation, None)
            # If we're excluding a plain annotation, also remove all attributes connected to it
            for a in plain_to_atts[annotation]:
                result.pop(a, None)

    return list(result.items())
