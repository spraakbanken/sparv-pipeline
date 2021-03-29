"""
Pandoc filter for removing links that won't work in PDF and reformatting docsify block quotes.

https://pandoc.org/filters.html
"""

from pandocfilters import Str, Strong, toJSONFilter, BlockQuote


def fix_document(key, value, _format, _meta):
    """Remove links that won't work in PDF and reformat docsify block quotes."""
    if key == "Link":
        url = value[2][0]
        if url.startswith("user-manual") or url.startswith("developers-guide"):
            # Return the link text
            return value[1]
    # Reformat the text inside block quotes
    elif key == "BlockQuote":
        try:
            first_string = value[0]["c"][0]["c"]
            if first_string == "[!NOTE]":
                value[0]["c"][0] = Strong([Str("Note:")])
                return BlockQuote(value)
            elif first_string == "[!TIP]":
                value[0]["c"][0] = Strong([Str("Tip:")])
                return BlockQuote(value)
            elif first_string == "[!WARNING]":
                value[0]["c"][0] = Strong([Str("Warning:")])
                return BlockQuote(value)
            elif first_string == "[!ATTENTION]":
                value[0]["c"][0] = Strong([Str("Attention:")])
                return BlockQuote(value)
        except Exception:
            return
        return


if __name__ == "__main__":
    toJSONFilter(fix_document)
