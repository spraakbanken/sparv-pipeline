"""Import module for plain text source files."""

import unicodedata
from pathlib import Path

from sparv import importer, util
from sparv.util.classes import Config, Document, Output, Source, SourceStructure, Text


@importer("TXT import", file_extension="txt", outputs=["text"], document_annotation="text", config=[
    Config("text_import.prefix", "", description="Optional prefix to add to annotation names."),
    Config("text_import.encoding", util.UTF8, description="Encoding of source document. Defaults to UTF-8."),
    Config("text_import.keep_control_chars", False, description="Set to True if control characters should not be "
                                                                "removed from the text."),
    Config("text_import.normalize", "NFC", description="Normalize input using any of the following forms: "
                                                       "'NFC', 'NFKC', 'NFD', and 'NFKD'.")
], )
def parse(doc: Document = Document(),
          source_dir: Source = Source(),
          prefix: str = Config("text_import.prefix"),
          encoding: str = Config("text_import.encoding"),
          keep_control_chars: bool = Config("text_import.keep_control_chars"),
          normalize: str = Config("text_import.normalize"),) -> None:
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

    if not keep_control_chars:
        text = util.remove_control_characters(text)

    if normalize:
        text = unicodedata.normalize("NFC", text)

    Text(doc).write(text)

    # Make up a text annotation surrounding the whole file
    text_annotation = "{}.text".format(prefix) if prefix else "text"
    Output(text_annotation, doc=doc).write([(0, len(text))])
    SourceStructure(doc).write([text_annotation])
