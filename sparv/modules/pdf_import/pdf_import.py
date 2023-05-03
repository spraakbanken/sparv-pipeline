"""Import module for pdf source files."""

import re
import unicodedata
from typing import Optional

import pdfplumber

from sparv.api import Config, Output, Source, SourceFilename, SourceStructure, Text, importer, util


@importer("pdf import", file_extension="pdf", outputs=["text", "page:number"], text_annotation="text", config=[
    Config("pdf_import.prefix", description="Optional prefix to add to annotation names."),
    Config("pdf_import.keep_control_chars", False, description="Set to True if control characters should not be "
                                                                "removed from the text."),
    Config("pdf_import.normalize", "NFC", description="Normalize input using any of the following forms: "
                                                       "'NFC', 'NFKC', 'NFD', and 'NFKD'.")
])
def parse(source_file: SourceFilename = SourceFilename(),
          source_dir: Source = Source(),
          prefix: Optional[str] = Config("pdf_import.prefix"),
          keep_control_chars: bool = Config("pdf_import.keep_control_chars"),
          normalize: str = Config("pdf_import.normalize")) -> None:
    """Parse pdf file as input to the Sparv Pipeline and keep page information.

    Args:
        source_file: The source filename.
        source_dir: The source directory.
        prefix: Optional prefix for output annotation.
        keep_control_chars: Set to True to keep control characters in the text.
        normalize: Normalize input text using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            'NFC' is used by default.
    """
    source_file_path = source_dir.get_path(source_file, ".pdf")

    # Extract text from PDF pages
    texts = []
    pages = []
    start_position = 0
    with pdfplumber.open(source_file_path) as pdf:
        for n, p in enumerate(pdf.pages):
            pagetext = p.extract_text(layout=True, y_density=12)
            # Keep track of the page indentation
            min_indent = min(map(len, re.findall(r"^ +", pagetext, flags=re.MULTILINE)))
            if not keep_control_chars:
                pagetext = util.misc.remove_control_characters(pagetext)
            if normalize:
                pagetext = unicodedata.normalize(normalize, pagetext)
            # Remove indentation and trailing whitespaces from every line
            pagetext = "\n".join(line[min_indent:].strip() for line in pagetext.split("\n"))
            texts.append(pagetext)

            # Create page span
            if n + 1 == len(pdf.pages):
                end_position = start_position + len(pagetext)
            else:
                end_position = start_position + len(pagetext) + 1
            pages.append((start_position, end_position))
            start_position = end_position

    # Write page spans
    Output("{}.page".format(prefix) if prefix else "page", source_file=source_file).write(pages)
    Output("{}.page:number".format(prefix) if prefix else "page:number", source_file=source_file).write(list(str(i) for i in range(1, len(pages) + 1)))

    text = "\n".join(texts)
    Text(source_file).write(text)

    # Make up a text annotation surrounding the whole file
    text_annotation = "{}.text".format(prefix) if prefix else "text"
    Output(text_annotation, source_file=source_file).write([(0, len(text))])
    SourceStructure(source_file).write([text_annotation, "page", "page:number"])
