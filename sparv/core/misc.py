"""Miscellaneous classes and methods."""

import logging
import re
from collections import OrderedDict, defaultdict
from typing import Iterable, List, Optional, Tuple


class SparvErrorMessage(Exception):
    """Exception used to notify users of errors in a friendly way without displaying traceback."""

    start_marker = "<<<START>>>"
    end_marker = "<<<END>>>"

    def __init__(self, message, module="", function=""):
        """Raise an error and notify user of the problem in a friendly way.

        Args:
            message: Error message.
            module: Name of module where error occurred (optional, not used in Sparv modules)
            function: Name of function where error occurred (optional, not used in Sparv modules)
        """
        self.message = message
        # Alter message before calling base class
        super().__init__("{}{}\n{}\n{}{}".format(SparvErrorMessage.start_marker, module, function, message,
                                                 SparvErrorMessage.end_marker))


def get_logger(name):
    """Get a logger that is a child of 'sparv.modules'."""
    if not name.startswith("sparv.modules"):
        name = "sparv.modules." + name
    return logging.getLogger(name)


def parse_annotation_list(annotation_names: Optional[Iterable[str]], all_annotations: Optional[Iterable[str]] = None,
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
    from sparv.api import Annotation

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
