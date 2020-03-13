"""Common constants."""

DELIM = "|"       # Delimiter char to put between ambiguous results
AFFIX = "|"       # Char to put before and after results to mark a set
SCORESEP = ":"    # Char that separates an annotation from a score
COMPSEP = "+"     # Char to separate compound parts

# Encodings:
UTF8 = "UTF-8"
LATIN1 = "ISO-8859-1"

# Colors for logging
COLORS = {
    "default":      "\033[m",
    # Styles
    "bold":         "\033[1m",
    "underline":    "\033[4m",
    "blink":        "\033[5m",
    "reverse":      "\033[7m",
    "concealed":    "\033[8m",
    # Font colors
    "black":        "\033[30m",
    "red":          "\033[31m",
    "green":        "\033[32m",
    "yellow":       "\033[33m",
    "blue":         "\033[34m",
    "magenta":      "\033[35m",
    "cyan":         "\033[36m",
    "white":        "\033[37m",
    # Background colors
    "on_black":     "\033[40m",
    "on_red":       "\033[41m",
    "on_green":     "\033[42m",
    "on_yellow":    "\033[43m",
    "on_blue":      "\033[44m",
    "on_magenta":   "\033[45m",
    "on_cyan":      "\033[46m",
    "on_white":     "\033[47m"
}
