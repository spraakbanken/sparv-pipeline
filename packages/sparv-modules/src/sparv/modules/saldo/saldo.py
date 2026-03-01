"""Create annotations from SALDO."""

import itertools
import operator
import re
from collections.abc import Iterable

from sparv.api import Annotation, Config, Model, Output, annotator, get_logger, util

from .saldo_model import SaldoLexicon

logger = get_logger(__name__)

# The minimum precision difference for two annotations to be considered equal
PRECISION_DIFF = 0.01


def preloader(models: list[Model]) -> dict:
    """Preload SALDO models.

    Args:
        models: A list of SALDO models to preload.

    Returns:
        A dictionary with the preloaded models.
    """
    if not isinstance(models, list):
        models = [models]
    return {m.path.stem: SaldoLexicon(m.path) for m in models}


@annotator(
    "SALDO annotations",
    config=[
        Config("saldo.model", default="saldo/saldo.pickle", description="Path to SALDO model", datatype=str),
        Config(
            "saldo.delimiter",
            default=util.constants.DELIM,
            description="Character to put between ambiguous results",
            datatype=str,
        ),
        Config(
            "saldo.affix",
            default=util.constants.AFFIX,
            description="Character to put before and after sets of results",
            datatype=str,
        ),
        Config(
            "saldo.precision",
            description="Format string for appending precision to each value (e.g. ':%.3f')",
            datatype=str,
        ),
        Config(
            "saldo.precision_filter",
            default="max",
            description="Precision filter with possible values 'max' (only use the most probable annotations), "
            "'first' (only use the single most probable annotation), 'none' (use all annotations)",
            datatype=str,
            choices=("max", "first", "none"),
        ),
        Config(
            "saldo.min_precision",
            default=0.66,
            description="Only use annotations with a probability score greater than or equal to this. "
            "0.25: part-of-speech does not match, 0.5: part-of-speech is missing, 0.66: part-of-speech "
            "matches, 0.75: morphosyntactic descriptor matches",
            datatype=float,
        ),
        Config(
            "saldo.skip_multiword",
            default=False,
            description="Whether to disable annotation of multiword expressions",
            datatype=bool,
        ),
        Config(
            "saldo.max_mwe_gaps",
            default=1,
            description="Max amount of gaps allowed within a multiword expression",
            datatype=int,
        ),
        Config(
            "saldo.allow_multiword_overlap",
            default=False,
            description="Whether all multiword expressions may overlap with each other. "
            "If set to False, some cleanup is done.",
            datatype=bool,
        ),
        Config(
            "saldo.word_separator",
            description="Character used to split the values of 'word' into several word variations",
            datatype=str,
        ),
    ],
    preloader=preloader,
    preloader_params=["models"],
    preloader_target="models_preloaded",
)
def annotate(
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("<token:word>"),
    sentence: Annotation = Annotation("<sentence>"),
    reference: Annotation = Annotation("<token:ref>"),
    out_sense: Output = Output("<token>:saldo.sense", cls="token:sense", description="SALDO identifiers"),
    out_lemgram: Output = Output("<token>:saldo.lemgram", cls="token:lemgram", description="SALDO lemgrams"),
    out_baseform: Output = Output("<token>:saldo.baseform", cls="token:baseform", description="Baseforms from SALDO"),
    models: Iterable[Model] = (Model("[saldo.model]"),),
    msd: Annotation | None = Annotation("<token:msd>"),
    delimiter: str = Config("saldo.delimiter"),
    affix: str = Config("saldo.affix"),
    precision: str | None = Config("saldo.precision"),
    precision_filter: str = Config("saldo.precision_filter"),
    min_precision: float = Config("saldo.min_precision"),
    skip_multiword: bool = Config("saldo.skip_multiword"),
    max_gaps: int = Config("saldo.max_mwe_gaps"),
    allow_multiword_overlap: bool = Config("saldo.allow_multiword_overlap"),
    word_separator: str | None = Config("saldo.word_separator"),
    models_preloaded: dict | None = None,
) -> None:
    """Use the Saldo lexicon model to annotate msd-tagged words.

    Args:
        token: Input annotation with token spans.
        word: Input annotation with token strings.
        sentence: Input annotation with sentence spans.
        reference: Input annotation with token indices for each sentence.
        out_sense: Output annotation with senses from SALDO.
        out_lemgram: Output annotation with lemgrams from SALDO.
        out_baseform: Output annotation with baseforms from SALDO.
        models: A list of pickled lexicons, typically the SALDO model (saldo.pickle)
            and optional lexicons for older Swedish.
        msd: Input annotation with POS and morphological descriptions.
        delimiter: Character to put between ambiguous results.
        affix: Character to put before and after sets of results.
        precision: Optional format string for appending precision to each value (e.g. ':%.3f').
        precision_filter: Precision filter with values 'max' (only use the annotations that are most probable),
            'first' (only use the most probable annotation(s)), 'none' (use all annotations).
        min_precision: Only use annotations with a probability score higher than this.
        skip_multiword: Whether to disable annotation of multiword expressions.
        max_gaps (int): Max amount of gaps allowed within a multiword expression.
        allow_multiword_overlap: Whether all multiword expressions may overlap with each other. If set to False,
            some cleanup is done.
        word_separator: Character used to split the values of 'word' into several word variations.
        models_preloaded: Preloaded models.
    """
    main(
        token=token,
        word=word,
        sentence=sentence,
        reference=reference,
        out_sense=out_sense,
        out_lemgram=out_lemgram,
        out_baseform=out_baseform,
        models=models,
        msd=msd,
        delimiter=delimiter,
        affix=affix,
        precision=precision,
        precision_filter=precision_filter,
        min_precision=min_precision,
        skip_multiword=skip_multiword,
        max_gaps=max_gaps,
        allow_multiword_overlap=allow_multiword_overlap,
        word_separator=word_separator,
        models_preloaded=models_preloaded,
    )


def main(
    token: Annotation,
    word: Annotation,
    sentence: Annotation,
    reference: Annotation,
    out_sense: Output,
    out_lemgram: Output,
    out_baseform: Output,
    models: Iterable[Model],
    msd: Annotation | None,
    delimiter: str,
    affix: str,
    precision: str | None,
    precision_filter: str,
    min_precision: float,
    skip_multiword: bool,
    max_gaps: int,
    allow_multiword_overlap: bool,
    word_separator: str | None,
    models_preloaded: dict | None,
) -> None:
    """Do SALDO annotations with models."""
    logger.progress()
    # Allow use of multiple lexicons
    models_list = [(m.path.stem, m) for m in models]
    if not models_preloaded:
        lexicon_list = [(name, SaldoLexicon(lex.path)) for name, lex in models_list]
    # Use pre-loaded lexicons
    else:
        lexicon_list = []
        for name, _lex in models_list:
            assert models_preloaded.get(name, None) is not None, f"Lexicon {name} not found!"
            lexicon_list.append((name, models_preloaded[name]))

    # Combine annotation names in SALDO lexicon without annotations
    annotations = []
    if out_baseform:
        annotations.append((out_baseform, "gf"))
    if out_lemgram:
        annotations.append((out_lemgram, "lem"))
    if out_sense:
        annotations.append((out_sense, "saldo"))

    if skip_multiword:
        logger.info("Skipping multi word annotations")

    min_precision = float(min_precision)

    # If min_precision is 0, skip almost all part-of-speech checking (verb multi-word expressions still won't be
    # allowed to span over other verbs)
    skip_pos_check = min_precision == 0.0

    word_annotation = list(word.read())
    ref_annotation = list(reference.read())
    msd_annotation = list(msd.read()) if msd else word.create_empty_attribute()

    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)

    if orphans:
        logger.warning("Found %d tokens not belonging to any sentence. These will not be annotated.", len(orphans))

    out_annotation = word.create_empty_attribute()
    logger.progress(total=len(sentences) + 1)

    for sent in sentences:
        incomplete_multis = []  # [{annotation, words, [ref], is_particle, lastwordWasGap, numberofgaps}]
        complete_multis = []  # ([ref], annotation)
        sentence_tokens = {}

        for token_index in sent:
            theword = word_annotation[token_index]
            ref = ref_annotation[token_index]
            msdtag = msd_annotation[token_index] if msd else ""

            annotation_info = {}
            sentence_tokens[ref] = {"token_index": token_index, "annotations": annotation_info}

            # Support for multiple values of word
            thewords = [w for w in theword.split(word_separator) if w] if word_separator else [theword]

            # First use MSD tags to find the most probable single word annotations
            ann_tags_words = _find_single_word(
                thewords, lexicon_list, msdtag, precision, min_precision, precision_filter, annotation_info
            )

            # Find multi-word expressions
            if not skip_multiword:
                _find_multiword_expressions(
                    incomplete_multis,
                    complete_multis,
                    thewords,
                    ref,
                    msdtag,
                    max_gaps,
                    ann_tags_words,
                    msd_annotation,
                    sent,
                    skip_pos_check,
                )

            # Loop to next token
        logger.progress()

        if not allow_multiword_overlap:
            # Check that we don't have any unwanted overlaps
            _remove_unwanted_overlaps(complete_multis)

        # Then save the rest of the multi-word expressions in sentence_tokens
        _save_multiwords(complete_multis, sentence_tokens)

        for tok in sentence_tokens.values():
            out_annotation[tok["token_index"]] = _join_annotation(tok["annotations"], delimiter, affix)

        # Loop to next sentence

    for out_annotation_obj, annotation_name in annotations:
        out_annotation_obj.write([v.get(annotation_name, delimiter) if v is not None else None for v in out_annotation])
    logger.progress()


################################################################################
# Auxiliaries
################################################################################


def _find_single_word(
    thewords: list,
    lexicon_list: list,
    msdtag: str,
    precision: str | None,
    min_precision: float,
    precision_filter: str,
    annotation_info: dict,
) -> list:
    """Find the most probable single word annotations using MSD tags.

    Args:
        thewords: List of words to annotate (usually a single word).
        lexicon_list: List of lexicons to use for annotation.
        msdtag: The MSD tag of the word.
        precision: Optional format string for appending precision to each value.
        min_precision: Minimum precision for annotations.
        precision_filter: Precision filter to apply.
        annotation_info: Dictionary to store the resulting annotations.

    Returns:
        Unfiltered list of annotations for the words, to be used for finding multiword expressions.
    """
    ann_tags_words = []

    for w in thewords:
        for name, lexicon in lexicon_list:
            prefix = "" if name == "saldo" or len(lexicon_list) == 1 else name + "m--"
            annotation = [(*a, prefix) for a in lexicon.lookup(w)]
            ann_tags_words += annotation
            # # Set break if each word only gets annotations from first lexicon that has entry for word
            # break

    annotation_precisions = [
        (get_precision(msdtag, msdtags), annotation, prefix)
        for (annotation, msdtags, wordslist, _, _, prefix) in ann_tags_words
        if not wordslist
    ]

    if min_precision > 0:
        annotation_precisions = [x for x in annotation_precisions if x[0] >= min_precision]
    annotation_precisions = _normalize_precision(annotation_precisions)
    annotation_precisions.sort(reverse=True, key=operator.itemgetter(0))

    if precision_filter and annotation_precisions:
        if precision_filter == "first":
            annotation_precisions = annotation_precisions[:1]
        elif precision_filter == "max":
            maxprec = annotation_precisions[0][0]

            def ismax(lemprec: tuple) -> bool:
                return lemprec[0] >= maxprec - PRECISION_DIFF

            annotation_precisions = itertools.takewhile(ismax, annotation_precisions)

    if precision:
        for prec, annotation, prefix in annotation_precisions:
            for key in annotation:
                annotation_entry = []
                for item in annotation[key]:
                    if not item.startswith(prefix):
                        annotation_entry.append(prefix + item)
                    else:
                        annotation_entry.append(item)
                annotation_info.setdefault(key, []).extend([a + precision % prec for a in annotation_entry])
    else:
        for _prec, annotation, prefix in annotation_precisions:
            for key in annotation:
                annotation_entry = []
                for item in annotation[key]:
                    if not item.startswith(prefix):
                        annotation_entry.append(prefix + item)
                    else:
                        annotation_entry.append(item)
                annotation_info.setdefault(key, []).extend(annotation_entry)

    return ann_tags_words


def _find_multiword_expressions(
    incomplete_multis: list,
    complete_multis: list,
    thewords: list,
    ref: str,
    msdtag: str,
    max_gaps: int,
    ann_tags_words: list,
    msd_annotation: list,
    sent: list[int],
    skip_pos_check: bool,
) -> None:
    """Find multiword expressions.

    Args:
        incomplete_multis: List of incomplete multiword expressions.
        complete_multis: List of completed multiword expressions.
        thewords: List of words to check for multiword expressions (usually a single word).
        ref: Reference ID of the current word.
        msdtag: The MSD tag of the current word.
        max_gaps: Maximum number of gaps allowed in a multiword expression.
        ann_tags_words: List of possible annotations for the words.
        msd_annotation: MSD annotation for whole source file.
        sent: Token indices for the current sentence.
        skip_pos_check: Whether to skip part-of-speech checking.
    """
    todelfromincomplete = []  # list to keep track of which expressions that have been completed

    for i, x in enumerate(incomplete_multis):
        # x = (annotations, following_words, [ref], gap_allowed, is_particle, [part-of-gap-boolean, gap_count])
        seeking_word = x[1][0]  # The next word we are looking for in this multi-word expression

        # Is a gap necessary in this position for this expression?
        if seeking_word == "*" and x[1][1].lower() in (w.lower() for w in thewords):
            seeking_word = x[1][1]
            del x[1][0]

        # If current gap is greater than max_gaps, stop searching
        if x[5][1] > max_gaps:
            todelfromincomplete.append(i)
        elif seeking_word.lower() in (w.lower() for w in thewords) and (
            # Last word may not be PP if this is a particle-multi-word
            skip_pos_check or not (len(x[1]) == 1 and x[4] and msdtag.startswith("PP"))
        ):
            x[5][0] = False  # last word was not a gap
            del x[1][0]
            x[2].append(ref)

            # Is current word the last word we are looking for?
            if len(x[1]) == 0:
                todelfromincomplete.append(i)

                # Create a list of msdtags of words belonging to the completed multi-word expr.
                msdtag_list = [msd_annotation[sent[int(ref) - 1]] for ref in x[2]]

                # For completed verb multis, check that at least one of the words is a verb:
                if not skip_pos_check and "..vbm." in x[0]["lem"][0]:
                    for tag in msdtag_list:
                        if tag.startswith("VB"):
                            complete_multis.append((x[2], x[0]))
                            break

                # For completed noun multis, check that at least one of the words is a noun:
                elif not skip_pos_check and "..nnm." in x[0]["lem"][0]:
                    for tag in msdtag_list:
                        if tag[:2] in {"NN", "PM", "UO"}:
                            complete_multis.append((x[2], x[0]))
                            break

                else:
                    complete_multis.append((x[2], x[0]))

        else:  # noqa: PLR5501
            # We've reached a gap
            # Are gaps allowed?
            if x[3]:
                # If previous word was NOT part of a gap, this is a new gap, so increment gap counter
                if not x[5][0]:
                    x[5][1] += 1
                x[5][0] = True  # Mark that this word was part of a gap

                # Avoid having another verb within a verb multi-word expression:
                # delete current incomplete multi-word expr. if it starts with a verb and if current word has POS tag VB
                if "..vbm." in x[0]["lem"][0] and msdtag.startswith("VB"):
                    todelfromincomplete.append(i)

            else:
                # Gaps are not allowed for this multi-word expression
                todelfromincomplete.append(i)

    # Delete seeking words from incomplete_multis
    for x in todelfromincomplete[::-1]:
        del incomplete_multis[x]

    # Collect possible multiword expressions:
    # Is this word a possible beginning of a multi-word expression?
    looking_for = [
        (annotation, words, [ref], gap_allowed, is_particle, [False, 0])
        for (annotation, _, wordslist, gap_allowed, is_particle, _) in ann_tags_words
        if wordslist
        for words in wordslist
    ]
    if len(looking_for) > 0:
        incomplete_multis.extend(looking_for)


def _remove_unwanted_overlaps(complete_multis: list) -> None:
    """Remove certain overlapping MWEs if they have identical POS (remove 'a' if 'b1 a1 b2 a2' or 'a1 b1 ab2')."""
    remove = set()
    for ai, a in enumerate(complete_multis):
        # For historical texts: Since we allow many words for one token (spelling variations) we must make sure that
        # two words of an MWE are not made up by two variants of one token. That is, that the same ref ID is not
        # used twice in an MWE.
        if len(set(a[0])) != len(a[0]):
            remove.add(ai)
            continue
        for b in complete_multis:
            # Check if both are of same POS
            if (
                a != b
                and re.search(r"\.(\w\w?)m?\.", a[1]["lem"][0]).groups()[0]
                == re.search(r"\.(\w\w?)m?\.", b[1]["lem"][0]).groups()[0]
            ):
                if b[0][0] < a[0][0] < b[0][-1] < a[0][-1]:
                    # A case of b1 a1 b2 a2. Remove a.
                    remove.add(ai)
                elif a[0][0] < b[0][0] and a[0][-1] == b[0][-1] and not all((x in a[0]) for x in b[0]):
                    # A case of a1 b1 ab2. Remove a.
                    remove.add(ai)

    for a in sorted(remove, reverse=True):
        del complete_multis[a]


def _save_multiwords(complete_multis: list, sentence_tokens: dict) -> None:
    """Save multiword expressions to the sentence tokens."""
    for c in complete_multis:
        first = True
        first_ref = ""
        for tok_ref in c[0]:
            if first:
                first_ref = tok_ref
            for ann, val in c[1].items():
                if not first:
                    val = [x + ":" + first_ref for x in val]  # noqa: PLW2901
                sentence_tokens[tok_ref]["annotations"].setdefault(ann, []).extend(val)
            first = False


def _join_annotation(annotation: dict, delimiter: str, affix: str) -> dict:
    """Convert annotations into CWB sets with unique values.

    Args:
        annotation: Dictionary of annotations to join.
        delimiter: Delimiter to use for joining.
        affix: Affix to use for joining.

    Returns:
        Dictionary of joined annotations.
    """
    return {
        a: util.misc.cwbset(list(dict.fromkeys(annotation[a])), delimiter=delimiter, affix=affix) for a in annotation
    }


def get_precision(msd: str, msdtags: list) -> float:
    """Calculate the precision of a SALDO annotation.

    If the word's msdtag is among the annotation's possible msdtags,
    we return a high value (0.75), a partial match returns 0.66, missing MSD returns 0.5,
    and otherwise a low value (0.25).

    Args:
        msd: The MSD tag of the word.
        msdtags: List of possible MSD tags for the annotation.

    Returns:
        The precision of the annotation.
    """
    return (
        0.5
        if msd is None
        else 0.75
        if msd in msdtags
        else 0.66
        if "." in msd and [partial for partial in msdtags if partial.startswith(msd[: msd.find(".")])]
        else 0.25
    )


def _normalize_precision(annotations: list) -> list:
    """Normalize the rankings in the annotation list so that the sum is 1.

    Args:
        annotations: List of tuples containing precision, annotation, and prefix.

    Returns:
        List of tuples with normalized precision.
    """
    total_precision = sum(prec for (prec, _annotation, prefix) in annotations)
    return [(prec / total_precision, annotation, prefix) for (prec, annotation, prefix) in annotations]
