"""Create files needed for the word picture in Korp."""

import pickle
import re
from collections import defaultdict
from dataclasses import dataclass

from sparv.api import (
    AllSourceFilenames,
    Annotation,
    AnnotationAllSourceFiles,
    AnnotationCommonData,
    AnnotationDataAllSourceFiles,
    Config,
    Corpus,
    Export,
    ExportInput,
    Marker,
    MarkerOptional,
    OutputCommonData,
    OutputData,
    OutputMarker,
    SparvErrorMessage,
    annotator,
    exporter,
    get_logger,
    installer,
    uninstaller,
    util,
)
from sparv.api.util.mysql_wrapper import MySQL

logger = get_logger(__name__)


MAX_STRING_LENGTH = 100  # Truncate all strings to this length
MAX_STRINGEXTRA_LENGTH = 32  # Truncate all stringextra values to this length
MAX_SENTENCES = 5000  # Max number of source sentences to include in SQL export per relation

# Default relation patterns for Swedish. See the documentation of `korp.wordpicture_rel_patterns` for details.
DEFAULT_REL_PATTERNS: list[dict] = [
    {
        "head": "VB",
        "rel": "SS",
        "dep": "NN",
        "secondary": {"shared": "head", "rel": "VG", "dep": "VB"},
        "output_head": "secondary_dep",
    },  # "han har sprungit"
    {"head": "VB", "rel": "(SS|OO|IO|OA)", "dep": "NN"},
    {"head": "VB", "rel": "(RA|TA)", "dep": "(AB|NN)"},
    {
        "head": "VB",
        "rel": "(RA|TA)",
        "dep": "PP",
        "secondary": {"rel": "(PA|HD)", "dep": "NN"},
        "output_dep": "secondary_dep",
        "extra": "{dep}",
    },  # "ges vid behov"
    {"head": "NN", "rel": "(AT|ET)", "dep": "JJ"},  # "stor hund"
    {
        "head": "NN",
        "rel": "ET",
        "dep": "VB",
        "secondary": {"rel": "SS", "dep": "HP"},
        "extra": "{secondary_dep}",
    },  # "brödet som bakats"
    {
        "head": "NN",
        "rel": "ET",
        "dep": "PP",
        "secondary": {"rel": "PA", "dep": "(NN|PM)"},
        "output_dep": "secondary_dep",
        "extra": "{dep}",
    },  # "barnen i skolan", "hundarna i Sverige"
    {"head": "PP", "rel": "PA", "dep": "NN"},  # "på bordet"
    {"head": "JJ", "rel": "AA", "dep": "AB"},  # "fullständigt galen"
]

# Default null relations for Swedish: POS tags mapped to lists of dependency relations that the POS should *not* have
DEFAULT_NULL_RELS: dict[str, list[str]] = {
    "VB": ["OO"],  # Verbs missing objects
}

# Default relation grouping for Swedish (will be treated as the same relation in the database)
DEFAULT_REL_GROUPING: dict[str, str] = {
    "OO": "OBJ",
    "IO": "OBJ",
    "RA": "ADV",
    "TA": "ADV",
    "OA": "ADV",
}

# Default relation names for Swedish (all possible relation names allowed in the database)
DEFAULT_REL_NAMES: list[str] = ["SS", "OBJ", "ADV", "AA", "AT", "ET", "PA"]

# Default regex pattern to identify multi-word expressions in baseform values (matches Swedish lemgram suffixes)
DEFAULT_MULTIWORD_PATTERN = r"\.\.\w\wm\."

# Suffix for yearly word picture exports
YEARLY_SUFFIX = "_yearly"


@dataclass(frozen=True, slots=True)
class SimpleRelPattern:
    """Container for simple relation patterns."""

    primary_re: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class ComplexRelPattern(SimpleRelPattern):
    """Container for complex relation patterns."""

    shared: str
    secondary_rel_re: re.Pattern[str]
    secondary_dep_re: re.Pattern[str]
    output_head: str
    output_dep: str
    extra: str


RelPattern = SimpleRelPattern | ComplexRelPattern


def _compile_rel_patterns(rel_patterns: list[dict]) -> list[RelPattern]:
    """Compile the relation patterns from configuration.

    Each pattern dict must have 'head', 'rel', and 'dep' keys for the primary relation. For complex patterns, a
    'secondary' dict with 'rel' and 'dep' keys specifies a chained relation. The secondary's 'shared' key (default:
    "dep") indicates which primary token is the secondary head. 'output_head' and 'output_dep' (default: "head" and
    "dep") control which tokens appear in the output. An 'extra' format string (e.g. "{dep}") can reference display
    forms of tokens.

    Args:
        rel_patterns: List of relation pattern dicts.

    Returns:
        A list of precompiled relation patterns.
    """
    compiled_relations = []
    for rel in rel_patterns:
        primary_re = re.compile(rf"^{rel['head']};{rel['rel']};{rel['dep']}$")

        if "secondary" not in rel:
            compiled_relations.append(SimpleRelPattern(primary_re=primary_re))
            continue

        sec = rel["secondary"]
        compiled_relations.append(
            ComplexRelPattern(
                primary_re=primary_re,
                shared=sec.get("shared", "dep"),
                secondary_rel_re=re.compile(rf"^{sec['rel']}$"),
                secondary_dep_re=re.compile(rf"^{sec['dep']}$"),
                output_head=rel.get("output_head", "head"),
                output_dep=rel.get("output_dep", "dep"),
                extra=rel.get("extra", ""),
            )
        )

    return compiled_relations


def _year_sort_value(year: int | None) -> tuple[int, int]:
    """Return a sortable representation of a year value, placing missing years first.

    Args:
        year: Year value, or None.

    Returns:
        A tuple that can be used as a sort key.
    """
    if year is None:
        return (0, -1)
    return (1, year)


@annotator(
    "Generate dependency relation data for Korp's Word Picture\n\n"
    "This annotator processes sentences and their tokens to identify specific syntactic relations (dependencies) "
    "between words based on predefined patterns. These patterns are configured through `korp.wordpicture_rel_patterns`."
)
def wordpicture(
    out: OutputData = OutputData("korp.wordpicture", description="Wordpicture data"),
    word: Annotation = Annotation("<token:word>"),
    pos: Annotation = Annotation("[korp.wordpicture_pos]"),
    baseform: Annotation = Annotation("[korp.wordpicture_baseform]"),
    dephead: Annotation = Annotation("<token:dephead>"),
    deprel: Annotation = Annotation("<token:deprel>"),
    sentence_id: Annotation = Annotation("<sentence>:misc.id"),
    text: Annotation = Annotation("<text>"),
    ref: Annotation = Annotation("<token:ref>"),
    display_form: Annotation = Annotation("[korp.wordpicture_display_form]"),
    sort: Config = Config("korp.wordpicture_sorted"),
    rel_patterns: list[dict] = Config("korp.wordpicture_rel_patterns"),
    null_rels: dict[str, list[str]] = Config("korp.wordpicture_null_rels"),
    multiword_pattern: str = Config("korp.wordpicture_multiword_pattern"),
) -> None:
    """Find syntactic dependencies for Korp's Word Picture.

    Args:
        out: Output annotation for word picture data.
        word: Word annotation.
        pos: Part-of-speech annotation.
        baseform: Baseform annotation (or similar, e.g. lemgrams for Swedish).
        dephead: Dependency head annotation.
        deprel: Dependency relation annotation.
        sentence_id: Sentence ID annotation.
        text: Text annotation.
        ref: Sentence relative token position annotation.
        display_form: Display form annotation, used for labeling intermediate tokens in complex relations. Usually
            this should be a baseform annotation.
        sort: Whether to sort the output for easier diffing.
        rel_patterns: Relation patterns configuration.
        null_rels: POS tags mapped to missing dependency relations.
        multiword_pattern: Regex pattern for identifying multi-word expressions in baseform values.
    """
    compiled_rel_patterns = _compile_rel_patterns(rel_patterns)

    text_sentences, _ = text.get_children(sentence_id)
    text_sentences = list(text_sentences)

    sentence_tokens, _ = sentence_id.get_children(word)
    sentence_tokens = list(sentence_tokens)
    sentence_ids = list(sentence_id.read())

    logger.progress(total=len(sentence_tokens) + 1)

    annotations = list(word.read_attributes((word, pos, baseform, dephead, deprel, ref, display_form)))

    triples = set()

    for text_index, sentence_batch in enumerate(text_sentences):
        for sentence_index in sentence_batch:
            sent_id = sentence_ids[sentence_index]
            sent: list[int] = sentence_tokens[sentence_index]
            incomplete: dict[int, list[tuple[int, tuple[str, dict]]]] = {}  # Tokens looking for heads, with head as key
            tokens: dict[int, dict] = {}  # Tokens in same sentence, with token_index as key
            skip_sentence = False

            # Link the tokens together
            for token_index in sent:
                token_word, token_pos, token_bf, token_dh, token_dr, token_ref, token_df = annotations[token_index]
                if not token_dr:
                    skip_sentence = True
                    break
                token_word = token_word.lower()

                if token_bf == "|":
                    token_bf = token_word

                this = {
                    "pos": token_pos,
                    "baseform": token_bf,
                    "word": token_word,
                    "head": None,
                    "dep": [],
                    "ref": token_ref,
                    "display_form": token_df,
                }

                tokens[token_index] = this

                if token_dh != "-":
                    token_dh = int(token_dh)
                    # This token is looking for a head (token is not root)
                    dep_triple = (token_dr, this)
                    if token_dh in tokens:
                        # Found head. Link them together both ways
                        this["head"] = (token_dr, tokens[token_dh])
                        tokens[token_dh]["dep"].append(dep_triple)
                    else:
                        incomplete.setdefault(token_dh, []).append((token_index, dep_triple))

                # Is someone else looking for the current token as head?
                if token_index in incomplete:
                    for t in incomplete[token_index]:
                        tokens[t[0]]["head"] = this
                        this["dep"].append(t[1])
                    del incomplete[token_index]

            if skip_sentence:
                continue

            assert not incomplete, "incomplete is not empty"

            def _match(pattern: re.Pattern[str] | str, value: str) -> bool:
                if isinstance(pattern, re.Pattern):
                    return bool(pattern.match(value))
                return bool(re.match(rf"^{pattern}$", value))

            def _findrel(head: dict, rel: re.Pattern[str] | str, dep: re.Pattern[str]) -> dict:
                """Return a dependent of a head matching the given relation and dependent POS."""
                for d in head["dep"]:
                    if _match(rel, d[0]) and _match(dep, d[1]["pos"]):
                        return d[1]
                return {}

            # Look for relations matching the patterns
            for token_data in tokens.values():
                for d in token_data["dep"]:
                    for rel in compiled_rel_patterns:
                        if rel.primary_re.match(";".join((token_data["pos"], d[0], d[1]["pos"]))):
                            triple = None
                            if type(rel) is ComplexRelPattern:
                                # This pattern is a complex relation with intermediate tokens
                                tokens_map = {"head": token_data, "dep": d[1]}
                                shared_token = tokens_map[rel.shared]
                                result = _findrel(shared_token, rel.secondary_rel_re, rel.secondary_dep_re)
                                if result:
                                    tokens_map["secondary_dep"] = result

                                    out_head = tokens_map[rel.output_head]
                                    out_dep = tokens_map[rel.output_dep]

                                    if rel.extra:
                                        df_map = {k: v["display_form"] for k, v in tokens_map.items()}
                                        ref_map = {k: v["ref"] for k, v in tokens_map.items()}
                                        extra_val = (
                                            rel.extra.format_map(df_map),
                                            rel.extra.format_map(ref_map),
                                        )
                                    else:
                                        extra_val = ("", None)

                                    triple = (
                                        (
                                            out_head["baseform"],
                                            out_head["word"],
                                            out_head["pos"],
                                            out_head["ref"],
                                        ),
                                        d[0],
                                        (out_dep["baseform"], out_dep["word"], out_dep["pos"], out_dep["ref"]),
                                        extra_val,
                                        sent_id,
                                        out_head["ref"],
                                        out_dep["ref"],
                                    )
                            else:
                                # This pattern is a simple relation
                                triple = (
                                    (token_data["baseform"], token_data["word"], token_data["pos"], token_data["ref"]),
                                    d[0],
                                    (d[1]["baseform"], d[1]["word"], d[1]["pos"], d[1]["ref"]),
                                    ("", None),
                                    sent_id,
                                    token_data["ref"],
                                    d[1]["ref"],
                                )
                            if triple:
                                triples.update({(*t, text_index) for t in _mutate_triple(triple, multiword_pattern)})
                                break
                token_rels = [d[0] for d in token_data["dep"]]
                for nrel_pos, nrel_deps in null_rels.items():
                    if nrel_pos == token_data["pos"]:
                        missing_rels = [x for x in nrel_deps if x not in token_rels]
                        for mrel in missing_rels:
                            triple = (
                                (token_data["baseform"], token_data["word"], token_data["pos"], token_data["ref"]),
                                mrel,
                                ("", "", "", token_data["ref"]),
                                ("", None),
                                sent_id,
                                token_data["ref"],
                                token_data["ref"],
                            )
                            triples.update({(*t, text_index) for t in _mutate_triple(triple, multiword_pattern)})
            logger.progress()

    def _wordpicture_sort_key(triple: tuple) -> tuple:
        # Replace yearfrom and yearto with their sortable representations
        return (
            *triple[:-2],
            _year_sort_value(triple[-2]),
            _year_sort_value(triple[-1]),
        )

    out.write(sorted(triples, key=_wordpicture_sort_key) if sort else triples)
    logger.progress()


def _mutate_triple(triple: tuple, multiword_pattern: str = "") -> list:
    """Split |head1|head2|...| REL |dep1|dep2|...| into several separate relations.

    Also remove multi-words which are in both head and dep, and remove the :nn part from words.

    Args:
        triple: A tuple with a relation, where head and dep can have several values separated by |.
        multiword_pattern: Regex pattern for identifying multi-word expressions. If empty, no multi-word filtering is
            done.

    Returns:
        A list of tuples with new relations based on the original one.
    """
    head, rel, dep, extra, sent_id, refhead, refdep = triple

    triples = []
    is_multi_value = {}
    parts = {"head": head, "dep": dep}

    for part, val in parts.items():
        if val[0].startswith("|") and val[0].endswith("|"):
            # This is a set of multiple values. Split it and remove ':' delimited suffix if present.
            parts[part] = [w[: w.find(":")] if ":" in w else w for w in val[0].split("|") if w]
            is_multi_value[part] = True
        else:
            parts[part] = [val[0]]

    def _remove_doubles(a: str, b: str) -> None:
        """Remove multi-words which are in both."""
        if multiword_pattern and a in is_multi_value and b in is_multi_value:
            doubles = [d for d in set(parts[a]).intersection(set(parts[b])) if re.search(multiword_pattern, d)]
            for double in doubles:
                parts[a].remove(double)
                parts[b].remove(double)

    _remove_doubles("head", "dep")
    # _remove_doubles("extra", "dep")
    # _remove_doubles("head", "extra")

    # Remove multiword deps for words that are already in "extra"
    if extra[1] and dep[0].startswith("|") and dep[0].endswith("|"):
        dep_multi = [dm for dm in dep[0].split("|") if ":" in dm]
        for dm in dep_multi:
            w, _, r = dm.partition(":")
            if int(r) <= int(extra[1]) <= int(dep[3]):
                try:
                    parts["dep"].remove(w)
                except ValueError:
                    pass

    if extra[0].startswith("|") and extra[0].endswith("|"):
        extra = sorted([x for x in extra[0].split("|") if x], key=len)
        extra = extra[0] if extra else ""
    else:
        extra = extra[0]

    for new_head in parts["head"]:
        for new_dep in parts["dep"]:
            triples.extend(
                (
                    # head: baseform, dep: baseform
                    (new_head, head[2], rel, new_dep, dep[2], extra, sent_id, refhead, refdep, 1, 1, 0, 0),
                    # head: wordform, dep: baseform
                    (head[1], head[2], rel, new_dep, dep[2], extra, sent_id, refhead, refdep, 0, 1, 1, 0),
                    # head: baseform, dep: wordform
                    (new_head, head[2], rel, dep[1], dep[2], extra, sent_id, refhead, refdep, 1, 0, 0, 1),
                )
            )

    return triples


@annotator("Generate shared strings data for Word Picture exports")
def wordpicture_strings(
    out: OutputCommonData = OutputCommonData("korp.wordpicture_strings", description="Wordpicture strings table"),
    wordpicture: AnnotationDataAllSourceFiles = AnnotationDataAllSourceFiles("korp.wordpicture"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
) -> None:
    """Generate the shared strings data for Word Picture exports.

    This data annotation contains all unique strings used in the Word Picture data, mapped to unique integer IDs, which
    are then referenced in the main Word Picture data. This is done as a separate step to allow both the aggregated and
    yearly exports to share the same string data, saving space in the database.

    Raises:
        SparvErrorMessage: If the Word Picture data cannot be read (likely due to format changes).
    """
    strings = {}
    string_index = -1

    for file in source_files:
        for row in wordpicture(file).read():
            try:
                head, headpos, _, dep, deppos, extra, *_ = row
            except ValueError:
                raise SparvErrorMessage(
                    "Error reading Word Picture data. The data may have been generated with an older version of Sparv. "
                    "Run 'sparv clean' and try again."
                ) from None
            head_tuple = (head, headpos, "")
            if head_tuple not in strings:
                string_index += 1
                strings[head_tuple] = string_index
            dep_tuple = (dep, deppos, extra)
            if dep_tuple not in strings:
                string_index += 1
                strings[dep_tuple] = string_index
    out.write(pickle.dumps(strings, protocol=pickle.HIGHEST_PROTOCOL))


@exporter("Word Picture strings SQL")
def wordpicture_strings_sql(
    corpus: Corpus = Corpus(),
    out: Export = Export("korp.wordpicture/wordpicture_strings.sql"),
    wordpicture_strings: AnnotationCommonData = AnnotationCommonData("korp.wordpicture_strings"),
    table_name: str = Config("korp.wordpicture_table"),
    sorted_sql: bool = Config("korp.wordpicture_sorted"),
) -> None:
    """Write the Word Picture strings data to an SQL file.

    This exporter creates only the strings table needed for the Word Picture data, shared by both the aggregated and
    yearly exports.

    Args:
        corpus: Corpus ID.
        out: Export file for the SQL data.
        wordpicture_strings: Word picture strings data.
        table_name: Name of the database table.
        sorted_sql: Whether to sort SQL output for easier diffing.
    """
    db_table = table_name + "_" + corpus.upper()
    _write_strings_sql(
        strings=pickle.loads(wordpicture_strings.read()),
        sql_file=out,
        db_table=db_table,
        sort=sorted_sql,
    )


@exporter(
    "Word Picture SQL with aggregated data",
    config=[
        Config(
            "korp.wordpicture_no_sentences",
            default=False,
            description="Set to 'true' to skip generating sentences table.",
            datatype=bool,
        ),
        Config(
            "korp.wordpicture_sorted",
            default=False,
            description="Set to 'true' to sort output for easier diffing (mainly for testing purposes).",
            datatype=bool,
        ),
    ],
)
def wordpicture_sql(
    corpus: Corpus = Corpus(),
    out: Export = Export("korp.wordpicture/wordpicture.sql"),
    wordpicture: AnnotationDataAllSourceFiles = AnnotationDataAllSourceFiles("korp.wordpicture"),
    wordpicture_strings: AnnotationCommonData = AnnotationCommonData("korp.wordpicture_strings"),
    no_sentences: bool = Config("korp.wordpicture_no_sentences"),
    sorted_sql: bool = Config("korp.wordpicture_sorted"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    table_name: str = Config("korp.wordpicture_table"),
    rel_grouping: dict[str, str] = Config("korp.wordpicture_rel_grouping"),
    rel_names: list[str] = Config("korp.wordpicture_rel_names"),
    split: bool = False,
) -> None:
    """Calculate statistics for the aggregated Word Picture data only and save to SQL.

    Args:
        corpus: Corpus ID.
        out: Export file for the SQL data.
        wordpicture: Word picture annotation data.
        wordpicture_strings: Word picture strings data.
        no_sentences: Whether to skip generating sentences table.
        sorted_sql: Whether to sort SQL output for easier diffing.
        source_files: List of source files to process.
        table_name: Name of the database table.
        rel_grouping: Mapping of raw relation names to grouped relation names.
        rel_names: All possible relation names allowed in the database.
        split: Whether to split the data per source file.
    """
    _wordpicture_sql(
        corpus=corpus,
        out=out,
        wordpicture_data=wordpicture,
        wordpicture_strings=wordpicture_strings,
        no_sentences=no_sentences,
        source_files=source_files,
        table_name=table_name,
        rel_grouping=rel_grouping,
        rel_names=rel_names,
        split=split,
        log_label="korp:wordpicture_sql",
        sort=sorted_sql,
    )


@exporter("Word Picture SQL with yearly data")
def wordpicture_yearly_sql(
    corpus: Corpus = Corpus(),
    out: Export = Export(f"korp.wordpicture/wordpicture{YEARLY_SUFFIX}.sql"),
    wordpicture: AnnotationDataAllSourceFiles = AnnotationDataAllSourceFiles("korp.wordpicture"),
    wordpicture_strings: AnnotationCommonData = AnnotationCommonData("korp.wordpicture_strings"),
    no_sentences: bool = Config("korp.wordpicture_no_sentences"),
    sorted_sql: bool = Config("korp.wordpicture_sorted"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    table_name: str = Config("korp.wordpicture_table"),
    split: bool = False,
    datefrom: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<text>:dateformat.datefrom"),
    dateto: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<text>:dateformat.dateto"),
    rel_grouping: dict[str, str] = Config("korp.wordpicture_rel_grouping"),
    rel_names: list[str] = Config("korp.wordpicture_rel_names"),
) -> None:
    """Calculate yearly statistics of the dependencies and save to SQL.

    Args:
        corpus: Corpus ID.
        out: Export file for the SQL data.
        wordpicture: Word picture annotation data.
        wordpicture_strings: Word picture strings data.
        no_sentences: Whether to skip generating sentences table.
        sorted_sql: Whether to sort SQL output for easier diffing.
        source_files: List of source files to process.
        table_name: Name of the database table.
        split: Whether to split the data per source file.
        datefrom: Annotation with the starting year of each text.
        dateto: Annotation with the ending year of each text.
        rel_grouping: Mapping of raw relation names to grouped relation names.
        rel_names: All possible relation names allowed in the database.
    """
    _wordpicture_sql(
        corpus=corpus,
        out=out,
        wordpicture_data=wordpicture,
        wordpicture_strings=wordpicture_strings,
        no_sentences=no_sentences,
        source_files=source_files,
        table_name=table_name,
        rel_grouping=rel_grouping,
        rel_names=rel_names,
        split=split,
        log_label="korp:wordpicture_yearly_sql",
        datefrom=datefrom,
        dateto=dateto,
        sort=sorted_sql,
    )


@exporter(
    (
        "Word Picture SQL shared with yearly data\n\n"
        "This exporter creates SQL views that make the aggregated Word Picture tables reference the yearly Word "
        "Picture tables. This is useful for corpora that only contain data from a single year, to avoid redundant "
        "storage of identical data. In those cases, use this instead of the regular aggregated Word Picture SQL "
        "exporter."
    ),
)
def wordpicture_sql_shared_with_yearly(
    corpus: Corpus = Corpus(),
    out: Export = Export(f"korp.wordpicture/wordpicture_shared_with{YEARLY_SUFFIX}.sql"),
    table_name: str = Config("korp.wordpicture_table"),
) -> None:
    """Create SQL views making the aggregated Word Picture tables share data with the yearly Word Picture tables.

    This exporter creates SQL views that make the aggregated Word Picture tables reference the yearly Word Picture
    tables. This is useful for corpora that only contain data from a single year, as it avoids redundant storage of
    identical data.

    Any existing aggregated Word Picture tables and views will be dropped.

    Args:
        corpus: Corpus ID.
        out: Export file for the SQL data.
        table_name: Name of the database table.
    """
    db_table_yearly = table_name + "_" + corpus.upper() + YEARLY_SUFFIX
    db_table = table_name + "_" + corpus.upper()
    with MySQL(output=out) as db:
        for suffix in ["", "_rel", "_head_rel", "_dep_rel", "_sentences"]:
            db.drop_table(f"{db_table}{suffix}")
            db.drop_view(f"{db_table}{suffix}")
            db.execute(f"CREATE ALGORITHM=MERGE VIEW {db_table}{suffix} AS SELECT * FROM {db_table_yearly}{suffix};")


def _wordpicture_sql(
    *,
    corpus: Corpus,
    out: Export,
    wordpicture_data: AnnotationDataAllSourceFiles,
    wordpicture_strings: AnnotationCommonData,
    no_sentences: bool,
    source_files: AllSourceFilenames,
    table_name: str,
    rel_grouping: dict[str, str],
    rel_names: list[str],
    split: bool,
    log_label: str,
    datefrom: AnnotationAllSourceFiles | None = None,
    dateto: AnnotationAllSourceFiles | None = None,
    sort: bool = False,
) -> None:
    """Shared implementation for Word Picture SQL exporters."""
    db_table = (
        table_name + "_" + corpus.upper() + (YEARLY_SUFFIX if datefrom is not None and dateto is not None else "")
    )

    index = 0
    strings = pickle.loads(wordpicture_strings.read())
    freq_index = {}
    sentence_count = defaultdict(int)
    file_count = 0

    if len(source_files) == 1:
        split = False

    logger.progress(total=len(source_files) + 1)

    def _parse_year(value: str | None) -> int | None:
        if not value:
            return None
        return int(value[:4])

    datefrom_data = dateto_data = None

    for file in source_files:
        file_count += 1
        sentences = {}
        if file_count == 1 or split:
            freq = {}  # Frequency of (head, rel, dep)
            rel_count = defaultdict(int)  # Frequency of (rel)
            head_rel_count = defaultdict(int)  # Frequency of (head, rel)
            dep_rel_count = defaultdict(int)  # Frequency of (rel, dep)

        file_data = wordpicture_data(file).read()
        if datefrom is not None and dateto is not None:
            datefrom_data = [_parse_year(year) for year in datefrom(file).read()]
            dateto_data = [_parse_year(year) for year in dateto(file).read()]

        for triple in file_data:
            head, headpos, rel, dep, deppos, extra, sid, refh, refd, bfhead, bfdep, wfhead, wfdep, text_index = triple
            yearfrom = datefrom_data[text_index] if datefrom_data else None
            yearto = dateto_data[text_index] if dateto_data else None

            # Get string IDs
            head = strings[head, headpos, ""]
            dep = strings[dep, deppos, extra]

            rel = rel_grouping.get(rel, rel)

            if (head, rel, dep, yearfrom, yearto) in freq_index:
                this_index = freq_index[head, rel, dep, yearfrom, yearto]
            else:
                this_index = index
                freq_index[head, rel, dep, yearfrom, yearto] = this_index
                index += 1
            freq.setdefault((head, rel, dep, yearfrom, yearto), [this_index, 0, [0, 0, 0, 0]])
            freq[head, rel, dep, yearfrom, yearto][1] += 1  # Frequency

            if not no_sentences and sentence_count[this_index] < MAX_SENTENCES:
                sentences.setdefault(this_index, set())
                sentences[this_index].add((sid, refh, refd))  # Sentence ID and "ref" for both head and dep
                sentence_count[this_index] += 1

            freq[head, rel, dep, yearfrom, yearto][2][0] = freq[head, rel, dep, yearfrom, yearto][2][0] or bfhead
            freq[head, rel, dep, yearfrom, yearto][2][1] = freq[head, rel, dep, yearfrom, yearto][2][1] or bfdep
            freq[head, rel, dep, yearfrom, yearto][2][2] = freq[head, rel, dep, yearfrom, yearto][2][2] or wfhead
            freq[head, rel, dep, yearfrom, yearto][2][3] = freq[head, rel, dep, yearfrom, yearto][2][3] or wfdep

            if bfhead and bfdep:
                rel_count[rel, yearfrom, yearto] += 1
            if (bfhead and bfdep) or wfhead:
                head_rel_count[head, rel, yearfrom, yearto] += 1
            if (bfhead and bfdep) or wfdep:
                dep_rel_count[dep, rel, yearfrom, yearto] += 1

        # If not the last file
        if file_count != len(source_files):
            if split:
                _write_sql(
                    sentences,
                    freq,
                    rel_count,
                    head_rel_count,
                    dep_rel_count,
                    out,
                    db_table,
                    rel_names,
                    split,
                    first=(file_count == 1),
                    no_sentences=no_sentences,
                    sort=sort,
                )
            else:
                # Only save sentences data, save the rest for the last file
                _write_sql(
                    sentences,
                    {},
                    {},
                    {},
                    {},
                    out,
                    db_table,
                    rel_names,
                    split,
                    first=(file_count == 1),
                    no_sentences=no_sentences,
                    sort=sort,
                )

        logger.progress()

    # Create the final file with all data
    _write_sql(
        sentences,
        freq,
        rel_count,
        head_rel_count,
        dep_rel_count,
        out,
        db_table,
        rel_names,
        split,
        first=(file_count == 1),
        last=True,
        no_sentences=no_sentences,
        include_years=datefrom is not None and dateto is not None,
        sort=sort,
    )

    logger.progress()
    logger.info("Done creating SQL files for %s", log_label)


def _write_strings_sql(
    strings: dict,
    sql_file: str,
    db_table: str,
    sort: bool = False,
) -> None:
    """Write the Word Picture string data to an SQL file."""
    temp_table = f"temp_{db_table}_strings"
    final_table = f"{db_table}_strings"
    max_pos_length = max((len(pos) for _, pos, _ in strings), default=1)

    mysql = MySQL(output=sql_file)

    mysql.create_table(temp_table, drop=True, **get_mysql_strings(max_pos_length))
    mysql.disable_keys(temp_table)
    mysql.disable_checks()
    mysql.set_names()

    rows = []

    string_items = strings.items()
    if sort:  # For deterministic output
        string_items = sorted(strings.items())

    for string_tuple, index in string_items:
        string, pos, stringextra = string_tuple
        row = {
            "id": index,
            "string": string[:MAX_STRING_LENGTH],
            "stringextra": stringextra[:MAX_STRINGEXTRA_LENGTH],
            "pos": pos,
        }
        rows.append(row)

    mysql.add_row(temp_table, rows)

    mysql.enable_keys(temp_table)
    mysql.drop_table(final_table)
    mysql.rename_table({temp_table: final_table})
    mysql.enable_checks()

    logger.info("%s written", sql_file)


def _write_sql(
    sentences: dict,
    freq: dict,
    rel_count: dict,
    head_rel_count: dict,
    dep_rel_count: dict,
    sql_file: str,
    db_table: str,
    rel_names: list[str],
    split: bool = False,
    first: bool = False,
    last: bool = False,
    no_sentences: bool = False,
    include_years: bool = True,
    sort: bool = False,
) -> None:
    """Write the Word Picture data (excluding strings) to an SQL file."""
    temp_db_table = "temp_" + db_table
    tables = ["", "_rel", "_head_rel", "_dep_rel"]
    if not no_sentences:
        tables.append("_sentences")
    update_freq = "ON DUPLICATE KEY UPDATE freq = freq + VALUES(freq)" if split else ""

    mysql = MySQL(output=sql_file, append=True)

    if first:
        mysql_relations = get_mysql_main(rel_names, include_year=include_years)
        mysql_rel = get_mysql_rel(rel_names, include_year=include_years)
        mysql_head_rel = get_mysql_head_rel(rel_names, include_year=include_years)
        mysql_dep_rel = get_mysql_dep_rel(rel_names, include_year=include_years)
        if not split:
            del mysql_relations["constraints"]
            del mysql_rel["constraints"]
            del mysql_head_rel["constraints"]
            del mysql_dep_rel["constraints"]
        mysql.create_table(temp_db_table, drop=True, **mysql_relations)
        mysql.create_table(temp_db_table + "_rel", drop=True, **mysql_rel)
        mysql.create_table(temp_db_table + "_head_rel", drop=True, **mysql_head_rel)
        mysql.create_table(temp_db_table + "_dep_rel", drop=True, **mysql_dep_rel)
        if not no_sentences:
            mysql.create_table(temp_db_table + "_sentences", drop=True, **MYSQL_SENTENCES)

        mysql.disable_keys(*[f"{temp_db_table}{t}" for t in tables])
        mysql.disable_checks()
        mysql.set_names()

    rows = []
    freq_items = freq.items()
    if sort:

        def _freq_sort_key(item: tuple) -> tuple:
            (head, rel, dep, yearfrom, yearto), _ = item
            return (head, rel, dep, _year_sort_value(yearfrom), _year_sort_value(yearto))

        freq_items = sorted(freq.items(), key=_freq_sort_key)

    for (head, rel, dep, yearfrom, yearto), dep2 in freq_items:
        index, count, bfwf = dep2

        row = {
            "id": index,
            "head": head,
            "rel": rel,
            "dep": dep,
            "freq": count,
            "bfhead": bfwf[0],
            "bfdep": bfwf[1],
            "wfhead": bfwf[2],
            "wfdep": bfwf[3],
            **({"yearfrom": yearfrom, "yearto": yearto} if include_years else {}),
        }
        rows.append(row)

    mysql.add_row(temp_db_table, rows, update_freq)

    rows = []
    rel_items = rel_count.items()
    if sort:

        def _rel_sort_key(item: tuple) -> tuple:
            (rel, yearfrom, yearto), _ = item
            return (rel, _year_sort_value(yearfrom), _year_sort_value(yearto))

        rel_items = sorted(rel_count.items(), key=_rel_sort_key)

    for (rel, yearfrom, yearto), f in rel_items:
        row = {"rel": rel, "freq": f, **({"yearfrom": yearfrom, "yearto": yearto} if include_years else {})}
        rows.append(row)

    mysql.add_row(temp_db_table + "_rel", rows, update_freq)

    rows = []
    head_items = head_rel_count.items()
    if sort:

        def _head_rel_sort_key(item: tuple) -> tuple:
            (head, rel, yearfrom, yearto), _ = item
            return (head, rel, _year_sort_value(yearfrom), _year_sort_value(yearto))

        head_items = sorted(head_rel_count.items(), key=_head_rel_sort_key)

    for (head, rel, yearfrom, yearto), f in head_items:
        row = {
            "head": head,
            "rel": rel,
            "freq": f,
            **({"yearfrom": yearfrom, "yearto": yearto} if include_years else {}),
        }
        rows.append(row)

    mysql.add_row(temp_db_table + "_head_rel", rows, update_freq)

    rows = []
    dep_items = dep_rel_count.items()
    if sort:

        def _dep_rel_sort_key(item: tuple) -> tuple:
            (dep, rel, yearfrom, yearto), _ = item
            return (dep, rel, _year_sort_value(yearfrom), _year_sort_value(yearto))

        dep_items = sorted(dep_rel_count.items(), key=_dep_rel_sort_key)

    for (dep, rel, yearfrom, yearto), f in dep_items:
        row = {
            "dep": dep,
            "rel": rel,
            "freq": f,
            **({"yearfrom": yearfrom, "yearto": yearto} if include_years else {}),
        }
        rows.append(row)

    mysql.add_row(temp_db_table + "_dep_rel", rows, update_freq)

    if not no_sentences:
        sentence_rows = []
        sentences_items = sentences.items()
        if sort:
            sentences_items = sorted(sentences.items())

        for index, sentenceset in sentences_items:
            if sort:
                sentenceset = sorted(sentenceset)  # noqa: PLW2901

            for sentence in sentenceset:
                srow = {"id": index, "sentence": sentence[0], "start": int(sentence[1]), "end": int(sentence[2])}
                sentence_rows.append(srow)

        mysql.add_row(temp_db_table + "_sentences", sentence_rows)

    if last:
        mysql.enable_keys(*[f"{temp_db_table}{t}" for t in tables])
        mysql.drop_table(*[f"{db_table}{t}" for t in tables])
        mysql.rename_table({f"{temp_db_table}{t}": f"{db_table}{t}" for t in tables})
        mysql.enable_checks()

    logger.info("%s written", sql_file)


@installer(
    "Install Korp's Word Picture strings SQL on remote host",
    uninstaller="korp:uninstall_wordpicture_strings",
)
def install_wordpicture_strings(
    sqlfile: ExportInput = ExportInput("korp.wordpicture/wordpicture_strings.sql"),
    marker: OutputMarker = OutputMarker("korp.install_wordpicture_strings_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("korp.uninstall_wordpicture_strings_marker"),
    db_name: str = Config("korp.mysql_dbname"),
    host: str | None = Config("korp.remote_host"),
) -> None:
    """Install Korp's Word Picture strings SQL on remote host.

    Args:
        sqlfile: SQL file to be installed.
        marker: Marker file to be written.
        uninstall_marker: Uninstall marker to remove.
        db_name: Name of the database.
        host: Remote host to install to.
    """
    util.install.install_mysql(host, db_name, sqlfile)
    uninstall_marker.remove()
    marker.write()


@uninstaller("Uninstall Korp's Word Picture strings from database", name="uninstall_wordpicture_strings")
def uninstall_wordpicture_strings(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("korp.uninstall_wordpicture_strings_marker"),
    install_marker: MarkerOptional = MarkerOptional("korp.install_wordpicture_strings_marker"),
    db_name: str = Config("korp.mysql_dbname"),
    table_name: str = Config("korp.wordpicture_table"),
    host: str | None = Config("korp.remote_host"),
) -> None:
    """Remove Korp's Word Picture strings data from database.

    Args:
        corpus: Corpus ID.
        marker: Uninstall marker to write.
        install_marker: Install marker to remove.
        db_name: Name of the database.
        table_name: Name of database table.
        host: Remote host.
    """
    db_table = table_name + "_" + corpus.upper()
    sql = MySQL(database=db_name, host=host)
    sql.drop_table(db_table + "_strings")

    install_marker.remove()
    marker.write()


# Create installers and uninstallers for both variants of Word Picture SQL
for installation in (
    {
        "description": "Install Korp's aggregated Word Picture SQL on remote host",
        "uninstall_description": "Uninstall Korp's aggregated Word Picture from database",
        "suffix": "",
    },
    {
        "description": "Install Korp's yearly Word Picture SQL on remote host",
        "uninstall_description": "Uninstall Korp's yearly Word Picture data from database",
        "suffix": YEARLY_SUFFIX,
    },
):

    @installer(
        installation["description"],
        name=f"install_wordpicture{installation['suffix']}",
        uninstaller=f"korp:uninstall_wordpicture{installation['suffix']}",
    )
    def install_wordpicture(
        sqlfile: ExportInput = ExportInput(f"korp.wordpicture/wordpicture{installation['suffix']}.sql"),
        marker: OutputMarker = OutputMarker(f"korp.install_wordpicture{installation['suffix']}_marker"),
        uninstall_marker: MarkerOptional = MarkerOptional(f"korp.uninstall_wordpicture{installation['suffix']}_marker"),
        _strings_marker: Marker = Marker("korp.install_wordpicture_strings_marker"),
        db_name: str = Config("korp.mysql_dbname"),
        host: str | None = Config("korp.remote_host"),
    ) -> None:
        """Install Korp's Word Picture SQL on remote host.

        Args:
            sqlfile: SQL file to be installed.
            marker: Marker file to be written.
            uninstall_marker: Uninstall marker to remove.
            _strings_marker: Marker ensuring that strings are installed first.
            db_name: Name of the database.
            host: Remote host to install to.
        """
        util.install.install_mysql(host, db_name, sqlfile)
        uninstall_marker.remove()
        marker.write()

    @uninstaller(installation["uninstall_description"], name=f"uninstall_wordpicture{installation['suffix']}")
    def uninstall_wordpicture(
        corpus: Corpus = Corpus(),
        marker: OutputMarker = OutputMarker(f"korp.uninstall_wordpicture{installation['suffix']}_marker"),
        install_marker: MarkerOptional = MarkerOptional(f"korp.install_wordpicture{installation['suffix']}_marker"),
        db_name: str = Config("korp.mysql_dbname"),
        table_name: str = Config("korp.wordpicture_table"),
        host: str | None = Config("korp.remote_host"),
    ) -> None:
        """Remove Korp's Word Picture data from database.

        Args:
            corpus: Corpus ID.
            marker: Uninstall marker to write.
            install_marker: Install marker to remove.
            db_name: Name of the database.
            table_name: Name of database table.
            host: Remote host.
        """
        db_table = table_name + "_" + corpus.upper()
        tables = ["", "_strings", "_rel", "_head_rel", "_dep_rel", "_sentences"]

        sql = MySQL(database=db_name, host=host)
        sql.drop_table(*[db_table + t for t in tables], *["temp_" + db_table + t for t in tables])

        install_marker.remove()
        marker.write()


@installer(
    (
        "Install database views for shared Word Picture data (requires yearly data)\n\n"
        "This installer sets up database views that make the aggregated Word Picture tables reference the yearly Word "
        "Picture tables. Use this instead of the regular Word Picture installer for corpora that only contain data "
        "from a single year. This will automatically install the yearly Word Picture data if it is not already "
        "installed."
    ),
    uninstaller="korp:uninstall_wordpicture_shared",
)
def install_wordpicture_shared(
    sql_file: ExportInput = ExportInput("korp.wordpicture/wordpicture_shared_with_yearly.sql"),
    marker: OutputMarker = OutputMarker("korp.install_wordpicture_shared_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("korp.uninstall_wordpicture_shared_marker"),
    _yearly_marker: Marker = Marker(f"korp.install_wordpicture{YEARLY_SUFFIX}_marker"),
    db_name: str = Config("korp.mysql_dbname"),
    host: str | None = Config("korp.remote_host"),
) -> None:
    """Install database view for shared Word Picture data.

    Args:
        sql_file: SQL file to be installed.
        marker: Marker file to be written.
        uninstall_marker: Uninstall marker to remove.
        db_name: Name of the database.
        host: Remote host.
    """
    util.install.install_mysql(host, db_name, sql_file)
    uninstall_marker.remove()
    marker.write()


@uninstaller(
    "Uninstall database views for shared Word Picture data",
)
def uninstall_wordpicture_shared(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("korp.uninstall_wordpicture_shared_marker"),
    install_marker: MarkerOptional = MarkerOptional("korp.install_wordpicture_shared_marker"),
    db_name: str = Config("korp.mysql_dbname"),
    table_name: str = Config("korp.wordpicture_table"),
    host: str | None = Config("korp.remote_host"),
) -> None:
    """Uninstall database views for shared Word Picture data.

    Args:
        corpus: Corpus ID.
        marker: Uninstall marker to write.
        install_marker: Install marker to remove.
        db_name: Name of the database.
        table_name: Base name of database table.
        host: Remote host.
    """
    db_table = table_name + "_" + corpus.upper()
    tables = ["", "_rel", "_head_rel", "_dep_rel", "_sentences"]

    sql = MySQL(database=db_name, host=host)
    sql.drop_view(*[db_table + t for t in tables])

    install_marker.remove()
    marker.write()


################################################################################


def _make_rel_enum(rel_names: list[str]) -> str:
    """Build the MySQL ENUM type string from a list of relation names.

    Returns:
        A MySQL ENUM type definition string.
    """
    return "ENUM({})".format(", ".join(f"'{r}'" for r in rel_names))


def get_mysql_main(rel_names: list[str], include_year: bool = True) -> dict:
    """Return MySQL table definition for main relation data, optionally including year columns."""
    rel_enum = _make_rel_enum(rel_names)
    columns = [
        ("id", int, 0, "NOT NULL"),
        ("head", int, 0, "NOT NULL"),
        ("rel", rel_enum, rel_names[0], "NOT NULL"),
        ("dep", int, 0, "NOT NULL"),
        ("freq", int, 0, "NOT NULL"),
        ("bfhead", "BOOL", None, ""),
        ("bfdep", "BOOL", None, ""),
        ("wfhead", "BOOL", None, ""),
        ("wfdep", "BOOL", None, ""),
    ]
    if include_year:
        columns += [
            ("yearfrom", int, None, ""),
            ("yearto", int, None, ""),
        ]
    return {
        "columns": columns,
        "primary": "id",
        "indexes": [
            "head bfhead bfdep" + (" yearfrom yearto" if include_year else "") + " rel freq",
            "dep bfhead bfdep" + (" yearfrom yearto" if include_year else "") + " rel freq",
            "head wfhead" + (" yearfrom yearto" if include_year else "") + " rel freq",
            "dep wfdep" + (" yearfrom yearto" if include_year else "") + " rel freq",
        ],
        "constraints": [("UNIQUE INDEX", "relation", ("head", "rel", "dep"))],
        "default charset": "utf8mb4",
        "row_format": "compressed",
        # "collate": "utf8mb4_bin"
    }


def get_mysql_rel(rel_names: list[str], include_year: bool = True) -> dict:
    """Return MySQL table definition for relations, optionally including year columns."""
    rel_enum = _make_rel_enum(rel_names)
    columns = [
        ("rel", rel_enum, rel_names[0], "NOT NULL"),
        ("freq", int, 0, "NOT NULL"),
    ]
    if include_year:
        columns += [
            ("yearfrom", int, None, ""),
            ("yearto", int, None, ""),
        ]
    return {
        "columns": columns,
        "primary": None,
        "indexes": ["rel" + (" yearfrom yearto" if include_year else "")],
        "constraints": [("UNIQUE INDEX", "relation", ("rel",) + (("yearfrom", "yearto") if include_year else ()))],
        "default charset": "utf8mb4",
        "collate": "utf8mb4_bin",
        "row_format": "compressed",
    }


def get_mysql_head_rel(rel_names: list[str], include_year: bool = True) -> dict:
    """Return MySQL table definition for head relations, optionally including year columns."""
    rel_enum = _make_rel_enum(rel_names)
    columns = [
        ("head", int, 0, "NOT NULL"),
        ("rel", rel_enum, rel_names[0], "NOT NULL"),
        ("freq", int, 0, "NOT NULL"),
    ]
    if include_year:
        columns += [
            ("yearfrom", int, None, ""),
            ("yearto", int, None, ""),
        ]
    return {
        "columns": columns,
        "primary": None,
        "indexes": ["head rel" + (" yearfrom yearto" if include_year else "")],
        "constraints": [
            ("UNIQUE INDEX", "relation", ("head", "rel") + (("yearfrom", "yearto") if include_year else ()))
        ],
        "default charset": "utf8mb4",
        "collate": "utf8mb4_bin",
        "row_format": "compressed",
    }


def get_mysql_dep_rel(rel_names: list[str], include_year: bool = True) -> dict:
    """Return MySQL table definition for dependent relations, optionally including year columns."""
    rel_enum = _make_rel_enum(rel_names)
    columns = [
        ("dep", int, 0, "NOT NULL"),
        ("rel", rel_enum, rel_names[0], "NOT NULL"),
        ("freq", int, 0, "NOT NULL"),
    ]
    if include_year:
        columns += [
            ("yearfrom", int, None, ""),
            ("yearto", int, None, ""),
        ]
    return {
        "columns": columns,
        "primary": None,
        "indexes": ["dep rel" + (" yearfrom yearto" if include_year else "")],
        "constraints": [
            ("UNIQUE INDEX", "relation", ("dep", "rel") + (("yearfrom", "yearto") if include_year else ()))
        ],
        "default charset": "utf8mb4",
        "collate": "utf8mb4_bin",
        "row_format": "compressed",
    }


def get_mysql_strings(max_pos_length: int) -> dict:
    """Return MySQL table definition for Word Picture strings."""
    return {
        "columns": [
            ("id", int, 0, "NOT NULL"),
            ("string", f"varchar({MAX_STRING_LENGTH:d})", "", "NOT NULL"),
            ("stringextra", f"varchar({MAX_STRINGEXTRA_LENGTH:d})", "", "NOT NULL"),
            ("pos", f"varchar({max_pos_length:d})", "", "NOT NULL"),
        ],
        "primary": "id",
        "indexes": ["string pos stringextra"],
        "default charset": "utf8mb4",
        "collate": "utf8mb4_bin",
        "row_format": "compressed",
    }


MYSQL_SENTENCES = {
    "columns": [
        ("id", int, None, ""),
        ("sentence", "varchar(64)", "", "NOT NULL"),
        ("start", int, None, ""),
        ("end", int, None, ""),
    ],
    "indexes": ["id"],
    "default charset": "utf8mb4",
    "collate": "utf8mb4_bin",
    "row_format": "compressed",
}
