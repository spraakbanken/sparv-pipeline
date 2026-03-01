"""Import module for PDF source files."""

import re
import unicodedata

import pypdfium2 as pdfium

from sparv.api import Config, Output, Source, SourceFilename, SourceStructure, SparvErrorMessage, Text, importer, util


@importer(
    "PDF Import",
    file_extension="pdf",
    outputs=["text", "page:number"],
    text_annotation="text",
    config=[
        Config("pdf_import.prefix", description="Optional prefix to add to annotation names.", datatype=str),
        Config(
            "pdf_import.keep_hyphenation",
            default=False,
            description="Set to True to retain hyphenation in the text.",
            datatype=bool,
        ),
        Config(
            "pdf_import.line_break_after_hyphenation",
            default=True,
            description="Set to True to preserve line breaks after hyphenations, or, if keep_hyphenation is False, to "
            "add line breaks after joining words.",
            datatype=bool,
        ),
        Config(
            "pdf_import.keep_control_chars",
            default=False,
            description="Set to True to retain control characters in the text.",
            datatype=bool,
        ),
        Config(
            "pdf_import.normalize",
            default="NFC",
            description="Normalize input text using one of the following forms: 'NFC', 'NFKC', 'NFD', or 'NFKD'.",
            datatype=str,
            choices=("NFC", "NFKC", "NFD", "NFKD"),
        ),
    ],
)
def parse(
    source_file: SourceFilename = SourceFilename(),
    source_dir: Source = Source(),
    prefix: str | None = Config("pdf_import.prefix"),
    keep_hyphenation: bool = Config("pdf_import.keep_hyphenation"),
    line_break_after_hyphenation: bool = Config("pdf_import.line_break_after_hyphenation"),
    keep_control_chars: bool = Config("pdf_import.keep_control_chars"),
    normalize: str = Config("pdf_import.normalize"),
) -> None:
    """Parse a PDF file as input to Sparv and retain page information.

    Args:
        source_file: The name of the source file.
        source_dir: The directory containing the source files.
        prefix: An optional prefix for output annotations.
        keep_hyphenation: Set to `True` to retain hyphenation in the text.
        line_break_after_hyphenation: Set to `True` to preserve line breaks after hyphenations, or, if
            `keep_hyphenation` is `False`, to add line breaks after joining words.
        keep_control_chars: Set to `True` to retain control characters in the text.
        normalize: Normalize input text using one of the following forms: 'NFC', 'NFKC', 'NFD', or 'NFKD'.
            Defaults to 'NFC'.

    Raises:
        SparvErrorMessage: Raised if no text is found in the PDF file.
    """
    source_file_path = source_dir.get_path(source_file, ".pdf")

    # Extract text from PDF pages
    texts = []
    pages = []
    start_position = 0
    pdf = pdfium.PdfDocument(source_file_path)
    for n, page in enumerate(pdf):
        textpage = page.get_textpage()
        pagetext = textpage.get_text_bounded().replace("\r\n", "\n")

        if keep_hyphenation and line_break_after_hyphenation:
            pagetext = pagetext.replace("\x02", "-\n")
        elif keep_hyphenation:
            pagetext = pagetext.replace("\x02", "-")
        elif not keep_hyphenation and line_break_after_hyphenation:
            pagetext = re.sub(r"(\S+)\x02(\S+)", r"\1\2\n", pagetext)
        elif not keep_hyphenation:
            pagetext = pagetext.replace("\x02", "")

        if not keep_control_chars:
            pagetext = util.misc.remove_control_characters(pagetext)
        if normalize:
            pagetext = unicodedata.normalize(normalize, pagetext)
        # Remove indentation and trailing whitespaces from each line
        min_indent = find_minimum_indentation(pagetext)
        pagetext = "\n".join(line[min_indent:].strip() for line in pagetext.split("\n"))
        texts.append(pagetext)

        # Create page span
        end_position = start_position + len(pagetext) + (1 if n + 1 < len(pdf) else 0)
        pages.append((start_position, end_position))
        start_position = end_position

    # Check if any text was found in the PDF
    if not "".join(text.strip() for text in texts):
        raise SparvErrorMessage(
            f"No text was found in the file '{source_file}.pdf'! This file cannot be processed "
            "with Sparv. Please ensure that every PDF source file contains machine-readable text."
        )

    # Write page spans
    Output(f"{prefix}.page" if prefix else "page", source_file=source_file).write(pages)
    Output(f"{prefix}.page:number" if prefix else "page:number", source_file=source_file).write(
        [str(i) for i in range(1, len(pages) + 1)]
    )

    text = "\n".join(texts)
    Text(source_file).write(text)

    # Create a text annotation covering the entire file
    text_annotation = f"{prefix}.text" if prefix else "text"
    Output(text_annotation, source_file=source_file).write([(0, len(text))])
    SourceStructure(source_file).write([text_annotation, "page", "page:number"])


def find_minimum_indentation(text: str) -> int:
    """Find the minimum indentation of a text.

    Args:
        text: The text to analyze.

    Returns:
        int: The minimum indentation of the text.
    """
    lines = [line for line in text.splitlines() if line.strip()]
    indents = [len(re.match(r"^ *", line).group(0)) for line in lines]
    return min(indents) if indents else 0
