"""Plain text export."""

from pathlib import Path

from sparv.api import Annotation, Config, Export, Text, exporter, get_logger

logger = get_logger(__name__)


@exporter("Plain text export")
def plain_text(text: Text = Text(), out: Export = Export("text_export/[text_export.filename]")) -> None:
    """Export the corpus text to plain text format."""
    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Read corpus text
    corpus_text = text.read()

    # Write corpus text to file
    out_path.write_text(corpus_text, encoding="utf-8")
    logger.info("Exported: %s", out)


@exporter(
    "Scrambled plain text export",
    config=[Config("text_export.scramble_on", description="Annotation to use for scrambling.", datatype=str)],
)
def scrambled(
    out: Export = Export("text_export.scrambled/[text_export.filename]"),
    chunk: Annotation = Annotation("[text_export.scramble_on]"),
    chunk_order: Annotation = Annotation("[text_export.scramble_on]:misc.number_random"),
) -> None:
    """Export the corpus text to scrambled plain text format.

    Args:
        out: The output file path and pattern.
        chunk: The annotation to use for scrambling the text.
        chunk_order: The annotation to use for determining the order of the chunks.
    """
    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunk_annotation = list(chunk.read())

    # Construct scrambled corpus text based on the chunk order
    corpus_text = []
    for i in list(chunk_order.read()):
        chunk_pos = int(i) - 1
        chunk_text = chunk_annotation[chunk_pos]
        corpus_text.append(chunk_text)

    # Write scrmbled corpus text to file
    out_path.write_text("\n".join(corpus_text), encoding="utf-8")
    logger.info("Exported: %s", out)
