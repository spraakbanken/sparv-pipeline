"""Import module for docx source files."""

import unicodedata

from docx2python import docx2python
from docx2python.iterators import iter_at_depth

from sparv.api import Config, Output, Source, SourceFilename, SourceStructure, SparvErrorMessage, Text, importer, util


@importer(
    "docx import",
    file_extension="docx",
    outputs=["text"],
    text_annotation="text",
    config=[
        Config("docx_import.prefix", description="Optional prefix to add to annotation names.", datatype=str),
        Config(
            "docx_import.keep_control_chars",
            default=False,
            description="Set to True if control characters should not be removed from the text.",
            datatype=bool,
        ),
        Config(
            "docx_import.normalize",
            default="NFC",
            description="Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.",
            datatype=str,
            choices=("NFC", "NFKC", "NFD", "NFKD"),
        ),
    ],
)
def parse(
    source_file: SourceFilename = SourceFilename(),
    source_dir: Source = Source(),
    prefix: str | None = Config("docx_import.prefix"),
    keep_control_chars: bool = Config("docx_import.keep_control_chars"),
    normalize: str = Config("docx_import.normalize"),
) -> None:
    """Parse docx file as input to Sparv.

    Args:
        source_file: The source filename.
        source_dir: The source directory.
        prefix: Optional prefix for output annotation.
        keep_control_chars: Set to True to keep control characters in the text.
        normalize: Normalize input text using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            'NFC' is used by default.

    Raises:
        SparvErrorMessage: If the docx file cannot be parsed.
    """
    source_file_path = source_dir.get_path(source_file, ".docx")
    try:
        d = docx2python(source_file_path)
    except Exception as e:
        raise SparvErrorMessage(f"Failed to parse docx file '{source_file}'. {type(e).__name__}: {e}") from None

    # Extract all text from the body, ignoring headers and footers
    text = "\n\n".join(iter_at_depth(d.body, 4))

    if not keep_control_chars:
        text = util.misc.remove_control_characters(text)

    if normalize:
        text = unicodedata.normalize(normalize, text)

    Text(source_file).write(text)

    # Make up a text annotation surrounding the whole file
    text_annotation = f"{prefix}.text" if prefix else "text"
    Output(text_annotation, source_file=source_file).write([(0, len(text))])
    SourceStructure(source_file).write([text_annotation])
