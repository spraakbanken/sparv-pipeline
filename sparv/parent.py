"""
Add annotations for parent links and/or children links.
"""
from collections import defaultdict
import sparv.util as util


def annotate_parents(doc, parent, child, orphan_alert=False):
    """Create parent links; parent, child are existing annotations."""
    orphan_alert = util.strtobool(orphan_alert)
    parent_spans, child_spans = read_parents_and_children(doc, parent, child)
    child_parents = []
    previous_parent_i = None
    try:
        parent_i, parent_span = next(parent_spans)
    except StopIteration:
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
                util.log.warning("Child '%s' missing parent; closest parent is %s",
                                 child_i, parent_i or previous_parent_i)
            child_parents.append((child_i, None))
        else:
            child_parents.append((child_i, parent_i))

    # Restore child order
    child_parents = [p for _, p in sorted(child_parents)]

    return child_parents


def annotate_children(doc, parent, child, orphan_alert=False):
    """Create links to children; parent, child are existing annotations."""
    orphan_alert = util.strtobool(orphan_alert)
    parent_spans, child_spans = read_parents_and_children(doc, parent, child)
    parent_children = []
    orphans = []
    previous_parent_i = None
    try:
        parent_i, parent_span = next(parent_spans)
        parent_children.append((parent_i, []))
    except StopIteration:
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
                util.log.warning("Child '%s' missing parent; closest parent is %s",
                                 child_i, parent_i or previous_parent_i)
            orphans.append(child_i)
        else:
            parent_children[-1][1].append(child_i)

    # Restore parent order
    parent_children = [p for _, p in sorted(parent_children)]

    return parent_children, orphans


def read_parents_and_children(doc, parent, child):
    """Read parent and child annotations. Reorder them according to span position, but keep original index
    information."""
    if isinstance(parent, str):
        parent = iter(sorted(enumerate(util.read_annotation_spans(doc, parent, decimals=True)), key=lambda x: x[1]))
    if isinstance(child, str):
        child = iter(sorted(enumerate(util.read_annotation_spans(doc, child, decimals=True)), key=lambda x: x[1]))

    return parent, child


if __name__ == "__main__":
    util.run.main(parents=annotate_parents,
                  children=annotate_children)
