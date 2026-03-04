"""Pandoc filter for fixing issues in the documentation.

This filter will:
- remove links that won't work in PDF
- remove images
- fix linebreaks
- wrap inline code in an inlinecode{} command (used for highlighting in PDF)
- reformat admonitions

https://pandoc.org/filters.html


Note: When debugging, print to stderr (e.g. print(value, file=sys.stderr)) as printing to stdout will break
pandocfilters.
"""

from __future__ import annotations

from typing import Any

from pandocfilters import BlockQuote, Para, RawInline, Str, Strong, toJSONFilter


class AdmonitionTracker:
    """Class to track the state of the previous admonition."""

    def __init__(self) -> None:
        """Initialize the tracker with no previous admonition."""
        self.previous_admonition = None


tracker = AdmonitionTracker()


def fix_document(key: str, value: str | list | dict | None, _format: str, _meta: dict) -> Any | None:
    """Remove links that won't work in PDF and reformat block quotes."""  # noqa: DOC201
    # Remove internal links, just keep the text
    if key == "Link":
        url = value[2][0]
        if url.startswith(("user-manual", "developers-guide")) or ".md" in url:
            return value[1]

    elif key == "Image":
        # Remove images containing the "intro-logo" class and the watch release screenshot
        if ["intro-logo"] in value[0] or "../site/images/watch-releases.png" in value[2]:
            return []

    # Convert <br /> tags to LaTeX line breaks
    elif key == "RawInline":
        fmt, txt = value
        if fmt == "html" and txt.lower().strip() in {"<br>", "<br/>", "<br />"}:
            # Use either '\\newline{}' or '\\\\'
            return RawInline("latex", "\\newline{}")

    elif key == "Code":
        _attr, text = value
        text = text.replace("\\", "\\textbackslash{}")  # Escape backslashes
        text = text.replace("_", "\\_")  # Escape underscores
        return RawInline("latex", "\\inlinecode{" + text + "}")

    # Reformat the text inside block quotes (standard admonitions)
    elif key == "BlockQuote":
        try:
            first_string = value[0]["c"][0]["c"]
            if first_string.startswith("[!"):
                # Remove "[!]" and capitalize the first letter
                first_string = first_string[2:-1].capitalize()
                value[0]["c"][0] = Strong([Str(first_string + ":")])
                return BlockQuote(value)
        except Exception:
            return None

    # Check for Para starting with "!!!" (mkdocs-style admonitions)
    elif key == "Para":
        if len(value) > 1 and value[0]["t"] == "Str" and value[0]["c"] == "!!!":
            # Remove the "!!!" and format the first element (capitalize and make it bold)
            value = value[2:]
            admonition_title = Str(value[0]["c"].capitalize() + ": ")
            value[0] = Strong([admonition_title])
            # Add a linebreak after the title
            value.insert(1, RawInline("latex", "\\newline{}"))

            # Admonition with title: search for (Quoted), remove quotes and make it bold
            for item in value:
                if isinstance(item, dict) and item.get("t") == "Quoted":
                    tracker.previous_admonition = Strong([admonition_title, *item["c"][1]])
                    return []  # Return an empty list to remove the element

            # Admonition without title, convert to BlockQuote
            return BlockQuote([Para(value)])

    # Check if the current element is a CodeBlock and the previous element was an admonition
    elif key == "CodeBlock" and tracker.previous_admonition is not None:
        admonition = BlockQuote([Para([tracker.previous_admonition]), Para([Str(value[1])])])
        tracker.previous_admonition = None
        return admonition

    return None


if __name__ == "__main__":
    toJSONFilter(fix_document)
