"""Import module for odt source files."""

import unicodedata
import xml.etree.ElementTree as etree  # noqa: N813
import zipfile
from pathlib import Path

from sparv.api import (
    Config,
    Output,
    Source,
    SourceFilename,
    SourceStructure,
    SparvErrorMessage,
    Text,
    get_logger,
    importer,
    util,
)

logger = get_logger(__name__)


@importer(
    "odt import",
    file_extension="odt",
    outputs=["text"],
    text_annotation="text",
    config=[
        Config("odt_import.prefix", description="Optional prefix to add to annotation names.", datatype=str),
        Config(
            "odt_import.keep_control_chars",
            default=False,
            description="Set to True if control characters should not be removed from the text.",
            datatype=bool,
        ),
        Config(
            "odt_import.normalize",
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
    prefix: str | None = Config("odt_import.prefix"),
    keep_control_chars: bool = Config("odt_import.keep_control_chars"),
    normalize: str = Config("odt_import.normalize"),
) -> None:
    """Parse odt file as input to Sparv.

    Args:
        source_file: The source filename.
        source_dir: The source directory.
        prefix: Optional prefix for output annotation.
        keep_control_chars: Set to True to keep control characters in the text.
        normalize: Normalize input text using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            'NFC' is used by default.

    Raises:
        SparvErrorMessage: If the file cannot be parsed or if the file is not an odt file.
    """
    source_file_path = source_dir.get_path(source_file, ".odt")

    # Parse odt and extract all text content
    try:
        text = OdtParser(source_file_path).text
    except Exception as e:
        raise SparvErrorMessage(f"Failed to parse odt file '{source_file}'. {type(e).__name__}: {e}") from None

    if not keep_control_chars:
        text = util.misc.remove_control_characters(text)

    if normalize:
        text = unicodedata.normalize(normalize, text)

    Text(source_file).write(text)

    # Make up a text annotation surrounding the whole file
    text_annotation = f"{prefix}.text" if prefix else "text"
    Output(text_annotation, source_file=source_file).write([(0, len(text))])
    SourceStructure(source_file).write([text_annotation])


class OdtParser:
    """Parse an odt file and extract its text content.

    Inspired by https://github.com/deanmalmgren/textract
    """

    def __init__(self, filename: Path) -> None:
        """Initialize OdtParser."""
        self.filename = filename
        self.extract()

    def extract(self) -> None:
        """Extract text content from odt file."""
        # Get content XML file from ODT zip archive
        with self.filename.open("rb") as stream:
            zip_stream = zipfile.ZipFile(stream)
            content = etree.fromstring(zip_stream.read("content.xml"))
        # Iterate the XML and extract all strings
        self.text = ""
        for child in content.iter():
            if child.tag in {self.ns("text:p"), self.ns("text:h")}:
                self.text += self.get_text(child) + "\n\n"
        # Remove the final two linebreaks
        if self.text:
            self.text = self.text[:-2]

    def get_text(self, element: etree.Element) -> str:
        """Recursively extract all text from element.

        Args:
            element: XML element to extract text from.

        Returns:
            Extracted text.
        """
        buffer = ""
        if element.text is not None:
            buffer += element.text
        for child in element:
            if child.tag == self.ns("text:tab"):
                buffer += "\t"
                if child.tail is not None:
                    buffer += child.tail
            elif child.tag == self.ns("text:s"):
                buffer += " "
                if child.get(self.ns("text:c")) is not None:
                    buffer += " " * (int(child.get(self.ns("text:c"))) - 1)
                if child.tail is not None:
                    buffer += child.tail
            # Add placeholders for images
            elif child.tag == self.ns("drawing:image"):
                image = child.get(self.ns("xmlns:href"))
                if image:
                    buffer += f"----{image}----"
            else:
                buffer += self.get_text(child)
        if element.tail is not None:
            buffer += element.tail
        return buffer

    @staticmethod
    def ns(tag: str) -> str:
        """Get the name for 'tag' including its namespace.

        Args:
            tag: The tag to get the namespace for.

        Returns:
            The tag with its namespace.
        """
        nsmap = {
            "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
            "drawing": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
            "xmlns": "http://www.w3.org/1999/xlink",
        }
        domain, tagname = tag.split(":")
        return f"{{{nsmap[domain]}}}{tagname}"
