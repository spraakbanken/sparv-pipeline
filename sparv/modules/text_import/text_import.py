"""Import module for plain text source files."""

import unicodedata
from pathlib import Path

from sparv import importer, util
from sparv.util.classes import Document, Source, Text


@importer("TXT import", source_type="txt", outputs=["text"])
def parse(doc: Document = Document(),
          source_dir: Source = Source(),
          prefix: str = "",
          encoding: str = util.UTF8,
          normalize: str = "NFC") -> None:
    """Parse plain text file as input to the Sparv pipeline.

    Args:
        doc: The document name.
        source_dir: The source directory.
        prefix: Optional prefix for output annotation.
        encoding: Encoding of source file. Default is UTF-8.
        normalize: Normalize input text using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            'NFC' is used by default.
    """
    # Source path
    if ":" in doc:
        doc, _, doc_chunk = doc.partition(":")
        source_file = Path(source_dir, doc, doc_chunk + ".txt")
    else:
        source_file = Path(source_dir, doc + ".txt")

    text = source_file.read_text(encoding=encoding)

    if normalize:
        text = unicodedata.normalize("NFC", text)

    Text(doc).write(text)

    # Make up a text annotation surrounding the whole file
    text_annotation = "{}.text".format(prefix) if prefix else "text"
    util.write_annotation(doc, text_annotation, [(0, len(text))])
    util.write_structure(doc, [])
