"""Provide a Console instance for pretty-printing."""

from rich.console import Console
from rich.theme import Theme

# Remove some automatic highlighting from the default theme to improve our log output
_theme = Theme(
    {
        "repr.ipv6": "none",
        "repr.eui48": "none",
        "repr.eui64": "none",
        "repr.number": "none",
    }
)

# Initialize rich console for pretty-printing
console = Console(theme=_theme)
