"""Korp-related annotators, exporters and installers."""

from sparv.api import Config

from . import config, lemgram_index, timespan, wordpicture

__config__ = [
    Config("korp.remote_host", description="Remote host to install to. Leave blank to install locally.", datatype=str),
    Config("korp.mysql_dbname", description="Name of database where Korp data will be stored", datatype=str),
    Config(
        "korp.modes",
        default=[{"name": "default"}],
        description="The Korp modes in which the corpus will be published",
        datatype=list[dict],
    ),
    Config(
        "korp.protected",
        default=False,
        description="Whether this corpus should have limited access or not",
        datatype=bool,
    ),
    Config(
        "korp.config_dir",
        description="Path on remote host where Korp corpus configuration files are stored",
        datatype=str,
    ),
    Config(
        "korp.wordpicture_table",
        default="relations",
        description="Prefix used for Word Picture database table names",
        datatype=str,
    ),
    Config(
        "korp.wordpicture_pos",
        default="<token:pos>",
        description="POS annotation used for Word Picture. Should be a token-level annotation with POS tags "
        "compatible with the relation patterns.",
        datatype=str,
    ),
    Config(
        "korp.wordpicture_baseform",
        default="<token:lemgram>",
        description="Baseform-like annotation for Word Picture. For Swedish, lemgrams are used.",
        datatype=str,
    ),
    Config(
        "korp.wordpicture_display_form",
        default="<token:baseform>",
        description="Display form annotation for Word Picture. Used for labeling intermediate tokens in complex "
        "relations. Usually this should be a baseform annotation, without any additional suffixes (e.g. for Swedish, "
        "this should be the actual baseform, not the lemgram).",
        datatype=str,
    ),
    Config(
        "korp.wordpicture_rel_patterns",
        default=wordpicture.DEFAULT_REL_PATTERNS,
        description=("""Relation patterns for Word Picture.

A simple pattern has three keys: 'head' (head POS), 'rel' (dependency relation), and 'dep' (dependent POS). Values can
be literal strings or regex patterns.

A complex pattern adds a 'secondary' dict describing a chained relation. The secondary's 'shared' key (default: "dep")
specifies which primary token the secondary relation chains from: "dep" (primary dependent is secondary head) or "head"
(primary head is also secondary head). The secondary must have 'rel' and 'dep' keys. 'output_head' and 'output_dep'
(default: "head" and "dep") control which tokens appear in the output triple. Valid values are "head", "dep", or
"secondary_dep". An optional 'extra' format string (e.g. "{dep}", "{secondary_dep}") references display forms of tokens,
and will be prepended to the dependent when displayed in Korp (e.g. to include prepositions)."""
        ),
        datatype=list[dict],
    ),
    Config(
        "korp.wordpicture_null_rels",
        default=wordpicture.DEFAULT_NULL_RELS,
        description="POS tags mapped to lists of dependency relations that should be missing (e.g. to collect verbs "
        "without objects).",
        datatype=dict[str, list],
    ),
    Config(
        "korp.wordpicture_rel_grouping",
        default=wordpicture.DEFAULT_REL_GROUPING,
        description="Mapping of raw dependency relation names to grouped relation names used in the database.",
        datatype=dict[str, str],
    ),
    Config(
        "korp.wordpicture_rel_names",
        default=wordpicture.DEFAULT_REL_NAMES,
        description="All possible relation names (after grouping) allowed in the database.",
        datatype=list[str],
    ),
    Config(
        "korp.wordpicture_multiword_pattern",
        default=wordpicture.DEFAULT_MULTIWORD_PATTERN,
        description="Regex pattern to identify multi-word expressions in baseform values. Used to remove duplicate "
        "multi-word entries appearing in both head and dep. Set to empty string to disable.",
        datatype=str,
    ),
]
