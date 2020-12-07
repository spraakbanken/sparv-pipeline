"""Example for a custom annotator."""

from sparv import Annotation, Output, annotator


@annotator("Convert every word to uppercase")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:custom.convert.upper")):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
