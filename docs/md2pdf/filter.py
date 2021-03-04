"""
Pandoc filter for removing links that won't work in PDF.

https://pandoc.org/filters.html
"""

from pandocfilters import toJSONFilter


def remove_links(key, value, _format, _meta):
    """Remove links that won't work in PDF."""
    if key == "Link":
        url = value[2][0]
        if url.startswith("user-manual") or url.startswith("developers-guide"):
            # Return the link text
            return value[1]


if __name__ == "__main__":
    toJSONFilter(remove_links)
