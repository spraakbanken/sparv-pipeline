"""Example for a custom annotator."""

from typing import Optional

from sparv import Annotation, Document, Output, custom_annotator, util


@custom_annotator("Convert every word to uppercase.")
def uppercase(doc: str = Document,
              word: str = Annotation("<token:word>"),
              out: str = Output("<token>:custom.convert.upper")):
    """Add prefix and/or suffix to annotation."""
    util.write_annotation(doc, out, [val.upper() for val in util.read_annotation(doc, word)])
