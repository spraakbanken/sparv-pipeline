"""Common constants."""

DELIM = "|"  # Delimiter char to put between ambiguous results
AFFIX = "|"  # Char to put before and after results to mark a set
SCORESEP = ":"  # Char that separates an annotation from a score
COMPSEP = "+"  # Char to separate compound parts

UNDEF = "__UNDEF__"  # Value for undefined annotations

OVERLAP_ATTR = "overlap"  # Name for automatically created overlap attributes

# Namespace to be used in case annotation names collide and sparv_namespace is not set in config
SPARV_DEFAULT_NAMESPACE = "sparv"
# Char used in annotations to separate a prefix from its tag name in XML namespaces
XML_NAMESPACE_SEP = "+"

# Encodings:
UTF8 = "UTF-8"
LATIN1 = "ISO-8859-1"

HEADER_CONTENTS = "contents"  # Name of annotation containing header contents
