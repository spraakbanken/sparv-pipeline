"""Common constants."""

DELIM = "|"       # Delimiter char to put between ambiguous results
AFFIX = "|"       # Char to put before and after results to mark a set
SCORESEP = ":"    # Char that separates an annotation from a score
COMPSEP = "+"     # Char to separate compound parts

UNDEF = "__UNDEF__"  # Value for undefined annotations

# Encodings:
UTF8 = "UTF-8"
LATIN1 = "ISO-8859-1"


class Color:
    """Colors and styles for printing."""

    RESET = "\033[m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    CONCEALED = "\033[8m"
    STRIKETHROUGH = "\033[9m"

    # Font colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    ON_BLACK = "\033[40m"
    ON_RED = "\033[41m"
    ON_GREEN = "\033[42m"
    ON_YELLOW = "\033[43m"
    ON_BLUE = "\033[44m"
    ON_MAGENTA = "\033[45m"
    ON_CYAN = "\033[46m"
    ON_WHITE = "\033[47m"
