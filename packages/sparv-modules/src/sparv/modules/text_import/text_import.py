"""Import module for plain text source files."""

import unicodedata

from sparv.api import Config, Output, Source, SourceFilename, SourceStructure, Text, importer, util


@importer(
    "TXT import",
    file_extension="txt",
    outputs=["text"],
    text_annotation="text",
    config=[
        Config("text_import.prefix", description="Optional prefix to add to annotation names.", datatype=str),
        Config(
            "text_import.encoding",
            util.constants.UTF8,
            description="Encoding of source file. Defaults to UTF-8.",
            datatype=str,
        ),
        Config(
            "text_import.keep_control_chars",
            False,
            description="Set to True if control characters should not be removed from the text.",
            datatype=bool,
        ),
        Config(
            "text_import.keep_unassigned_chars",
            False,
            description="Set to True if unassigned characters should not be removed from the text.",
            datatype=bool,
        ),
        Config(
            "text_import.normalize",
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
    prefix: str | None = Config("text_import.prefix"),
    encoding: str = Config("text_import.encoding"),
    keep_control_chars: bool = Config("text_import.keep_control_chars"),
    normalize: str = Config("text_import.normalize"),
) -> None:
    """Parse plain text file as input to Sparv.

    Args:
        source_file: The name of the source file.
        source_dir: The source directory.
        prefix: Optional prefix for output annotation.
        encoding: Encoding of source file. Default is UTF-8.
        keep_control_chars: Set to True to keep control characters in the text.
        normalize: Normalize input text using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            'NFC' is used by default.
    """
    text = source_dir.get_path(source_file, ".txt").read_text(encoding=encoding)

    if not keep_control_chars:
        text = util.misc.remove_control_characters(text)

    if normalize:
        text = unicodedata.normalize(normalize, text)

    Text(source_file).write(text)

    # Make up a text annotation surrounding the whole file
    text_annotation = f"{prefix}.text" if prefix else "text"
    Output(text_annotation, source_file=source_file).write([(0, len(text))])
    SourceStructure(source_file).write([text_annotation])
