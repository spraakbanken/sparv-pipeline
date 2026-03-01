"""Small annotators that don't fit as standalone python files."""

import operator
import re
import unicodedata

from sparv.api import Annotation, Config, Output, SourceFilename, SparvErrorMessage, Text, Wildcard, annotator, util
from sparv.api.util.tagsets import pos_to_upos, suc_to_feats, tagmappings


@annotator(
    "Text content of tokens",
    config=[
        Config(
            "misc.keep_formatting_chars",
            default=False,
            description="Set to True if you don't want formatting characters (e.g. soft hyphens) to be removed from "
            "tokens in the output.",
            datatype=bool,
        )
    ],
)
def text_spans(
    text: Text = Text(),
    chunk: Annotation = Annotation("<token>"),
    out: Output = Output("<token>:misc.word", cls="token:word", description="Text content of every token"),
    keep_formatting_chars: bool | None = Config("misc.keep_formatting_chars"),
) -> None:
    """Add the text content for each token span as a new annotation.

    Args:
        text: Text content of source file.
        chunk: Annotation with spans.
        out: Output annotation for text content.
        keep_formatting_chars: If True, keep formatting characters (e.g. soft hyphens) in the output.
    """
    corpus_text = text.read()
    if isinstance(chunk, (str, Annotation)):
        chunk = chunk.read_spans()
    out_annotation = []
    for span in chunk:
        token = corpus_text[span[0] : span[1]]
        if not keep_formatting_chars:
            new_token = util.misc.remove_formatting_characters(token)
            # If this token consists entirely of formatting characters, don't remove them. Empty tokens are bad!
            if new_token:
                token = new_token
        out_annotation.append(token)
    if out:
        out.write(out_annotation)
    else:
        return out_annotation
    return None


@annotator(
    "Head and tail whitespace characters for tokens\n\n"
    "Spaces are encoded as '\\s', newlines as '\\n', and tabs as '\\t'.\n\n"
    "The whitespace doesn't overlap, meaning that whitespace covered by one token's 'tail' will not be included in the "
    "following token's 'head'.",
    config=[
        Config(
            "misc.head_tail_max_length",
            description="Truncate misc.head and misc.tail to this number of characters.",
            datatype=int,
        )
    ],
)
def text_headtail(
    text: Text = Text(),
    chunk: Annotation = Annotation("<token>"),
    out_head: Output = Output("<token>:misc.head", description="Whitespace characters preceding every token"),
    out_tail: Output = Output("<token>:misc.tail", description="Whitespace characters following every token"),
    truncate_after: int | None = Config("misc.head_tail_max_length"),
) -> None:
    """Extract "head" and "tail" whitespace characters for tokens.

    Args:
        text: Text content of source file.
        chunk: Annotation with spans.
        out_head: Output annotation for whitespace characters preceding every token.
        out_tail: Output annotation for whitespace characters following every token.
        truncate_after: Truncate the output to this number of characters.
    """

    def escape(t: str) -> str:
        """Return a string with whitespace characters escaped.

        All characters in the Unicode category "Zs" (space separators) are treated as normal spaces.
        """
        t = "".join(" " if unicodedata.category(c) == "Zs" else c for c in t)
        return t.replace(" ", "\\s").replace("\n", "\\n").replace("\t", "\\t")

    out_head_annotation = chunk.create_empty_attribute()
    out_tail_annotation = chunk.create_empty_attribute()
    head_text = None

    corpus_text = text.read()
    chunk = list(chunk.read_spans())

    for i, span in enumerate(chunk):
        if head_text:
            if truncate_after:
                out_head_annotation[i] = escape(head_text)[:truncate_after]
            else:
                out_head_annotation[i] = escape(head_text)
            head_text = None

        if i < len(chunk) - 1:
            tail_start = span[1]
            tail_end = chunk[i + 1][0]
            tail_text = corpus_text[tail_start:tail_end]

            try:
                n_pos = tail_text.rindex("\n")
            except ValueError:
                n_pos = None
            if n_pos is not None and n_pos + 1 < len(tail_text):
                head_text = tail_text[n_pos + 1 :]
                tail_text = tail_text[: n_pos + 1]

            if tail_text:
                if truncate_after:
                    out_tail_annotation[i] = escape(tail_text)[:truncate_after]
                else:
                    out_tail_annotation[i] = escape(tail_text)

    out_head.write(out_head_annotation)
    out_tail.write(out_tail_annotation)


@annotator(
    "Fake head and tail whitespace characters for tokens\n\n"
    "Instead of using the existing whitespace from the source text, this annotator annotates every token with a "
    "space as the 'tail' (encoded as '\\s'), up to a specified line length. When the line length is reached, a newline "
    "character (encoded as '\\n') is used instead, resetting the line length counter. The 'head' is always an empty "
    "string.\n\n"
    "This is useful when 'head' and 'tail' annotations are needed, but the source text has no useful whitespace, such "
    "as source files with one token per line.",
    config=[Config("misc.fake_headtail_line_length", description="Max line length", default=120, datatype=int)],
)
def fake_text_headtail(
    chunk: Annotation = Annotation("<token:word>"),
    out_head: Output = Output("<token>:misc.fake_head", description="Whitespace characters preceding every token"),
    out_tail: Output = Output("<token>:misc.fake_tail", description="Whitespace characters following every token"),
    max_line_length: int = Config("misc.fake_headtail_line_length"),
) -> None:
    """Create fake "head" and "tail" whitespace characters for tokens."""
    word_annotation = chunk.read()
    out_head_annotation = []
    out_tail_annotation = []
    line_length = 0
    # Loop through all words, adding whitespace after each word until the line length is reached, then add a newline
    for word in word_annotation:
        if out_tail_annotation and line_length + len(word) > max_line_length:
            # Change previous line to end with a newline
            out_tail_annotation[-1] = "\\n"
            line_length = 0
        out_head_annotation.append("")
        out_tail_annotation.append("\\s")
        line_length += len(word) + 1

    out_head.write(out_head_annotation)
    out_tail.write(out_tail_annotation)


@annotator("Convert part-of-speech tags, specified by the mapping")
def translate_tag(out: Output, tag: Annotation, mapping: dict | str) -> None:
    """Convert part-of-speech tags, specified by the mapping.

    Example mappings: parole_to_suc, suc_to_simple, ...

    Args:
        out: Output annotation.
        tag: Input annotation with part-of-speech tags.
        mapping: Mapping to use for conversion. If a string is given, it will be looked up in tagmappings.mappings.
    """
    if isinstance(mapping, str):
        mapping = tagmappings.mappings[mapping]
    out.write(mapping.get(t, t) for t in tag.read())


@annotator("Convert SUC POS tags to UPOS", language=["swe"])
def upostag(
    out: Output = Output("<token>:misc.upos", cls="token:upos", description="Part-of-speeches in UD"),
    pos: Annotation = Annotation("<token:pos>"),
) -> None:
    """Convert SUC POS tags to UPOS.

    Args:
        out: Output annotation.
        pos: Input annotation with SUC POS tags.
    """
    pos_tags = pos.read()
    out_annotation = [pos_to_upos(tag, "swe", "SUC") for tag in pos_tags]
    out.write(out_annotation)


@annotator("Convert SUC MSD tags to universal features", language=["swe"])
def ufeatstag(
    out: Output = Output("<token>:misc.ufeats", cls="token:ufeats", description="Universal morphological features"),
    pos: Annotation = Annotation("<token:pos>"),
    msd: Annotation = Annotation("<token:msd>"),
) -> None:
    """Convert SUC MSD tags to universal features.

    Args:
        out: Output annotation.
        pos: Input annotation with SUC POS tags.
        msd: Input annotation with SUC MSD tags.
    """
    pos_tags = pos.read()
    msd_tags = msd.read()
    out_annotation = []

    for pos_tag, msd_tag in zip(pos_tags, msd_tags, strict=True):
        feats = suc_to_feats(pos_tag, msd_tag)
        out_annotation.append(util.misc.cwbset(feats))

    out.write(out_annotation)


@annotator(
    "Convert {struct}:{attr} into a token annotation",
    wildcards=[Wildcard("struct", Wildcard.ANNOTATION), Wildcard("attr", Wildcard.ATTRIBUTE)],
)
def struct_to_token(
    attr: Annotation = Annotation("{struct}:{attr}"),
    token: Annotation = Annotation("<token>"),
    out: Output = Output(
        "<token>:misc.from_struct_{struct}_{attr}", description="Token attribute based on {struct}:{attr}"
    ),
) -> None:
    """Convert an attribute on a structural annotation into a token attribute.

    Args:
        attr: Structural annotation with the attribute to convert.
        token: Token annotation.
        out: Output annotation for the token attribute.
    """
    token_parents = token.get_parents(attr)
    attr_values = list(attr.read())
    out_values = [attr_values[p] if p is not None else "" for p in token_parents]
    out.write(out_values)


@annotator(
    "Inherit {attr} from {parent}:{attr} to {child}",
    wildcards=[
        Wildcard("parent", Wildcard.ANNOTATION),
        Wildcard("child", Wildcard.ANNOTATION),
        Wildcard("attr", Wildcard.ATTRIBUTE),
    ],
)
def inherit(
    parent: Annotation = Annotation("{parent}:{attr}"),
    child: Annotation = Annotation("{child}"),
    out: Output = Output(
        "{child}:misc.inherit_{parent}_{attr}", description="Attribute on {child} inherited from {parent}:{attr}"
    ),
) -> None:
    """Inherit attribute from a structural parent annotation to a child.

    Args:
        parent: Structural parent annotation with the attribute to inherit.
        child: Child annotation.
        out: Output attribute for the child annotation, with the inherited values.
    """
    child_parents = child.get_parents(parent)
    attr_values = list(parent.read())
    out_values = [attr_values[p] if p is not None else "" for p in child_parents]
    out.write(out_values)


# TODO: Do we still need this? struct_to_token probably mostly replaces it
def chain(out, annotations, default=None):  # noqa
    """Create a functional composition of a list of annotations.

    E.g., token.sentence + sentence.id -> token.sentence-id
    """
    if isinstance(annotations, str):
        annotations = annotations.split()
    annotations = [a.read() for a in annotations]
    out.write(util.misc.chain(annotations, default))


@annotator("Create new annotation, with spans as values")
def span_as_value(chunk: Annotation, out: Output) -> None:
    """Create new annotation, with spans as values.

    Args:
        chunk: Annotation with spans.
        out: Output annotation with spans as values.
    """
    out.write((f"{start}-{end}" for start, end in chunk.read_spans()))


@annotator("Select a specific index from the values of an annotation")
def select(out: Output, annotation: Annotation, index: int = 0, separator: str = " ") -> None:
    """Select a specific index from the values of an annotation.

    The given annotation values are separated by 'separator', by default whitespace, with at least index + 1 elements.

    Args:
        out: Output annotation.
        annotation: Input annotation with values.
        index: Index to select from the values of the annotation.
        separator: Separator used to split the values of the annotation.
    """
    if isinstance(index, str):
        index = int(index)
    out.write(value.split(separator)[index] for value in annotation.read())


@annotator("Create an annotation with a constant value")
def constant(chunk: Annotation, out: Output, value: str = "") -> None:
    """Create an annotation with a constant value.

    Args:
        chunk: Input annotation.
        out: Output annotation.
        value: Constant value to use.
    """
    out.write(value for _ in chunk.read())


@annotator("Add prefix and/or suffix to an annotation")
def affix(chunk: Annotation, out: Output, prefix: str = "", suffix: str = "") -> None:
    """Add prefix and/or suffix to annotation.

    Args:
        chunk: Input annotation.
        out: Output annotation.
        prefix: Prefix to add to the annotation values.
        suffix: Suffix to add to the annotation values.
    """
    out.write([(prefix + val + suffix) for val in chunk.read()])


@annotator("Replace every character in an annotation with an anonymous character")
def anonymise(chunk: Annotation, out: Output, anonym_char: str = "*") -> None:
    """Replace every character in an annotation with an anonymous character (* per default).

    Args:
        chunk: Input annotation.
        out: Output annotation.
        anonym_char: Character to use for anonymisation.
    """
    out.write([(anonym_char * len(val)) for val in chunk.read()])


@annotator("Find and replace whole annotation")
def replace(chunk: Annotation, out: Output, find: str = "", sub: str = "") -> None:
    """Find and replace whole annotation. Find string must match whole annotation.

    Args:
        chunk: Input annotation.
        out: Output annotation.
        find: String to find in the annotation values.
        sub: Replacement string.
    """
    out.write(sub if val == find else val for val in chunk.read())


@annotator("Find and replace whole annotation values")
def replace_list(chunk: Annotation, out: Output, find: str = "", sub: str = "") -> None:
    """Find and replace annotations.

    Find string must match whole annotation.
    `find` and `sub` are whitespace separated lists of words to replace and their replacement.

    Args:
        chunk: Input annotation.
        out: Output annotation.
        find: String to find in the annotation values. Can be a list of words separated by whitespace.
        sub: Replacement string. Can be a list of words separated by whitespace.

    Raises:
        SparvErrorMessage: If the number of words in `find` and `sub` do not match.
    """
    find = find.split()
    sub = sub.split()
    if len(find) != len(sub):
        raise SparvErrorMessage("Find and sub must have the same number of words.")
    translate = dict(zip(find, sub, strict=True))
    out.write(translate.get(val, val) for val in chunk.read())


@annotator("Find and replace parts of or whole annotation")
def find_replace(chunk: Annotation, out: Output, find: str = "", sub: str = "") -> None:
    """Find and replace parts of or whole annotation.

    Args:
        chunk: Input annotation.
        out: Output annotation.
        find: String to find in the annotation values.
        sub: Replacement string.
    """
    out.write(val.replace(find, sub) for val in chunk.read())


@annotator("Do find and replace in values of annotation using a regular expressions")
def find_replace_regex(chunk: Annotation, out: Output, find: str = "", sub: str = "") -> None:
    """Do find and replace in values of annotation using a regular expressions.

    N.B: When writing regular expressions in YAML they should be enclosed in single quotes.

    Args:
        chunk: Input annotation.
        out: Output annotation.
        find: Regular expression to find in the annotation values.
        sub: Replacement string.
    """
    out.write(re.sub(find, sub, val) for val in chunk.read())


@annotator("Concatenate values from two annotations, with an optional separator")
def concat(out: Output, left: Annotation, right: Annotation, separator: str = "", merge_twins: bool = False) -> None:
    """Concatenate values from two annotations, with an optional separator.

    Args:
        out: Output annotation.
        left: Left annotation.
        right: Right annotation.
        separator: Separator to use between the values of the two annotations.
        merge_twins: If True, no concatenation will be performed if the values are the same.
    """
    b = list(right.read())
    out.write(
        f"{val_a}{separator}{b[n]}" if not (merge_twins and val_a == b[n]) else val_a
        for (n, val_a) in enumerate(left.read())
    )


@annotator("Concatenate two or more annotations, with an optional separator")
def concat2(out: Output, annotations: list[Annotation], separator: str = "") -> None:
    """Concatenate two or more annotations, with an optional separator.

    Args:
        out: Output annotation.
        annotations: List of annotations to concatenate.
        separator: Separator to use between the values of the annotations.
    """
    annotations = [list(a.read()) for a in annotations]
    out.write([separator.join([a[n] for a in annotations]) for (n, _) in enumerate(annotations[0])])


@annotator("Replace empty values in 'chunk' with values from 'backoff'")
def backoff(chunk: Annotation, backoff: Annotation, out: Output) -> None:
    """Replace empty values in 'chunk' with values from 'backoff'.

    Args:
        chunk: Input annotation.
        backoff: Annotation with values to use as backoff.
        out: Output annotation.
    """
    backoff = list(backoff.read())
    out.write(val or backoff[n] for (n, val) in enumerate(chunk.read()))


@annotator(
    "Replace empty values in 'chunk' with values from 'backoff' and output info about which annotator each "
    "annotation was produced with."
)
def backoff_with_info(
    chunk: Annotation, backoff: Annotation, out: Output, out_info: Output, chunk_name: str = "", backoff_name: str = ""
) -> None:
    """Replace empty values in 'chunk' with values from 'backoff'.

    Args:
        chunk: Input annotation.
        backoff: Annotation with values to use as backoff.
        out: Output annotation.
        out_info: Output annotation with info about which annotator each annotation was produced with.
        chunk_name: Name of the chunk annotation.
        backoff_name: Name of the backoff annotation.
    """
    backoffs = list(backoff.read())
    out_annotation = []
    out_info_annotation = []
    if not chunk_name:
        chunk_name = chunk.name
    if not backoff_name:
        backoff_name = backoff.name

    for n, val in enumerate(chunk.read()):
        if val:
            out_annotation.append(val)
            out_info_annotation.append(chunk_name)
        else:
            out_annotation.append(backoffs[n])
            out_info_annotation.append(backoff_name)
    out.write(out_annotation)
    out_info.write(out_info_annotation)


@annotator("Replace values in 'chunk' with non empty values from 'repl'")
def override(chunk: Annotation, repl: Annotation, out: Output) -> None:
    """Replace values in 'chunk' with non-empty values from 'repl'.

    Args:
        chunk: Input annotation.
        repl: Annotation with values to use as replacements.
        out: Output annotation.
    """

    def empty(val: str) -> bool:
        if not val:
            return True
        return val == "|"

    repl = list(repl.read())
    out.write(repl[n] if not empty(repl[n]) else val for (n, val) in enumerate(chunk.read()))


@annotator("Round floats to the given number of decimals")
def roundfloat(chunk: Annotation, out: Output, decimals: int = 2) -> None:
    """Round floats to the given number of decimals.

    Args:
        chunk: Input annotation.
        out: Output annotation.
        decimals: Number of decimals to round to.
    """
    decimals = int(decimals)
    strformat = "%." + str(decimals) + "f"
    out.write(strformat % round(float(val), decimals) for val in chunk.read())


@annotator("Merge two annotations (which may be sets) into one set")
def merge_to_set(out: Output, left: Annotation, right: Annotation, unique: bool = True, sort: bool = True) -> None:
    """Merge two sets of annotations (which may be sets) into one set.

    Args:
        out: Output annotation.
        left: Left annotation.
        right: Right annotation.
        unique: If True, remove duplicate values.
        sort: If True, sort the values within the new set.
    """
    le = left.read()
    ri = right.read()
    out_annotation = []
    for left_annot, right_annot in zip(le, ri, strict=True):
        annots = util.misc.set_to_list(left_annot) + util.misc.set_to_list(right_annot)
        if unique:
            annots = list(dict.fromkeys(annots))
        out_annotation.append(util.misc.cwbset(annots, sort=sort))
    out.write(out_annotation)


@annotator("Source filename as attribute on text annotation")
def source(
    out: Output = Output("<text>:misc.source", description="Source filename"),
    name: SourceFilename = SourceFilename(),
    text: Annotation = Annotation("<text>"),
) -> None:
    """Create a text attribute based on the filename of the source file.

    Args:
        out: Output annotation.
        name: Source filename.
        text: Text annotation.
    """
    out.write(name for _ in text.read())


@annotator("Get the first annotation from a cwb set")
def first_from_set(out: Output, chunk: Annotation) -> None:
    """Get the first annotation from a set.

    Args:
        out: Output annotation.
        chunk: Input annotation.
    """
    out_annotation = [util.misc.set_to_list(val)[0] if util.misc.set_to_list(val) else "" for val in chunk.read()]
    out.write(out_annotation)


@annotator("Get the best annotation from a cwb set with scores")
def best_from_set(out: Output, chunk: Annotation, is_sorted: bool = False, score_sep: str = ":") -> None:
    """Get the best annotation from a set with scores.

    Args:
        out: Output annotation.
        chunk: Input annotation.
        is_sorted: If True, the input is already sorted, and the first value is taken.
        score_sep: Separator used to separate the score from the value.
    """
    out_annotation = []
    for val in chunk.read():
        if is_sorted:
            values = [(v.split(score_sep)[1], v.split(score_sep)[0]) for v in util.misc.set_to_list(val)]
        else:
            values = sorted(
                [(v.split(score_sep)[1], v.split(score_sep)[0]) for v in util.misc.set_to_list(val)],
                key=operator.itemgetter(0),
                reverse=True,
            )
        out_annotation.append(values[0][1] if values else "")
    out.write(out_annotation)


@annotator(
    "Extract metadata from filename of source file using a regular expression\n\n"
    "The regular expression should contain one group, which will be extracted as metadata. The metadata will by "
    "default be assigned to the text annotation.",
)
def metadata_from_filename(
    out: Output,
    pattern: str,
    text: Annotation = Annotation("<text>"),
    source_file: SourceFilename = SourceFilename(),
) -> None:
    """Extract metadata from the filename of the source file using a regular expression.

    Args:
        out: Output annotation.
        pattern: Regular expression pattern.
        text: Text annotation.
        source_file: Source filename.
    """
    match = re.search(pattern, source_file)
    if match:
        metadata = match.group(1)
        out.write([metadata] * len(text))
    else:
        out.write([""] * len(text))
