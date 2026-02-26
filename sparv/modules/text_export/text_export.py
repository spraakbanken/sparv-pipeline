"""Plain text export."""

from pathlib import Path

from sparv.api import Export, Text, exporter, get_logger

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
