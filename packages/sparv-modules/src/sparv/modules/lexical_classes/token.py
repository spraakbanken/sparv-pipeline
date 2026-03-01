"""Annotate words with lexical classes from Blingbring or SweFN."""

from collections.abc import Iterable

from sparv.api import Annotation, Config, Model, Output, annotator, get_logger, util
from sparv.api.util.constants import AFFIX, DELIM, SCORESEP

logger = get_logger(__name__)


@annotator(
    "Annotate tokens with Blingbring classes",
    language=["swe"],
    config=[
        Config(
            "lexical_classes.bb_word_model",
            default="lexical_classes/blingbring.pickle",
            description="Path to Blingbring model",
            datatype=str,
        )
    ],
)
def blingbring_words(
    out: Output = Output(
        "<token>:lexical_classes.blingbring", description="Lexical classes for tokens from Blingbring"
    ),
    model: Model = Model("[lexical_classes.bb_word_model]"),
    saldoids: Annotation = Annotation("<token:sense>"),
    pos: Annotation = Annotation("<token:pos>"),
    pos_limit: Iterable[str] = ("NN", "VB", "JJ", "AB"),
    class_set: str = "bring",
    disambiguate: bool = True,
    connect_ids: bool = False,
    delimiter: str = DELIM,
    affix: str = AFFIX,
    scoresep: str = SCORESEP,
    lexicon: util.misc.PickledLexicon | None = None,
) -> None:
    """Blingbring specific wrapper for annotate_words. See annotate_words for more info."""
    if class_set not in {"bring", "roget_head", "roget_subsection", "roget_section", "roget_class"}:
        logger.warning("Class '%s' not available. Fallback to 'bring'.")
        class_set = "bring"

    # Blingbring annotation function
    def annotate_bring(
        saldo_ids: list[str], lexicon: util.misc.PickledLexicon, connect_ids: bool = False, scoresep: str = SCORESEP
    ) -> list[str]:
        rogetid = set()
        if saldo_ids:
            for sid in saldo_ids:
                if connect_ids:
                    rogetid = rogetid.union({i + scoresep + sid for i in lexicon.lookup(sid, default=set())})
                else:
                    rogetid = rogetid.union(lexicon.lookup(sid, default={}).get(class_set, set()))
        return sorted(rogetid)

    annotate_words(
        out,
        model,
        saldoids,
        pos,
        annotate_bring,
        pos_limit=pos_limit,
        disambiguate=disambiguate,
        connect_ids=connect_ids,
        delimiter=delimiter,
        affix=affix,
        scoresep=scoresep,
        lexicon=lexicon,
    )


@annotator(
    "Annotate tokens with SweFN classes",
    language=["swe"],
    config=[
        Config(
            "lexical_classes.swefn_word_model",
            default="lexical_classes/swefn.pickle",
            description="Path to SweFN model",
            datatype=str,
        )
    ],
)
def swefn_words(
    out: Output = Output("<token>:lexical_classes.swefn", description="Lexical classes for tokens from SweFN"),
    model: Model = Model("[lexical_classes.swefn_word_model]"),
    saldoids: Annotation = Annotation("<token:sense>"),
    pos: Annotation = Annotation("<token:pos>"),
    pos_limit: Iterable[str] = ("NN", "VB", "JJ", "AB"),
    disambiguate: bool = True,
    connect_ids: bool = False,
    delimiter: str = DELIM,
    affix: str = AFFIX,
    scoresep: str = SCORESEP,
    lexicon: util.misc.PickledLexicon | None = None,
) -> None:
    """Swefn specific wrapper for annotate_words. See annotate_words for more info."""

    # SweFN annotation function
    def annotate_swefn(
        saldo_ids: list[str], lexicon: util.misc.PickledLexicon, connect_ids: bool = False, scoresep: str = SCORESEP
    ) -> list[str]:
        swefnid = set()
        if saldo_ids:
            for sid in saldo_ids:
                if connect_ids:
                    swefnid = swefnid.union({i + scoresep + sid for i in lexicon.lookup(sid, default=set())})
                else:
                    swefnid = swefnid.union(lexicon.lookup(sid, default=set()))
        return sorted(swefnid)

    annotate_words(
        out,
        model,
        saldoids,
        pos,
        annotate_swefn,
        pos_limit=pos_limit,
        disambiguate=disambiguate,
        connect_ids=connect_ids,
        delimiter=delimiter,
        affix=affix,
        scoresep=scoresep,
        lexicon=lexicon,
    )


def annotate_words(
    out: Output,
    model: Model,
    saldoids: Annotation,
    pos: Annotation,
    annotate: callable,
    pos_limit: Iterable[str],
    disambiguate: bool = True,
    connect_ids: bool = False,
    delimiter: str = DELIM,
    affix: str = AFFIX,
    scoresep: str = SCORESEP,
    lexicon: util.misc.PickledLexicon | None = None,
) -> None:
    """Annotate words with blingbring classes (rogetID).

    Args:
        out: Resulting annotation.
        model: Model to use for annotation.
        saldoids: Existing annotation with saldoIDs.
        pos: Existing annotation with parts of speech.
        annotate: Annotation function, returns an iterable containing annotations
            for one token ID. (annotate_bring() or annotate_swefn())
        pos_limit: Parts of speech that will be annotated.
            Set to None to annotate all pos.
        disambiguate: Use WSD and use only the most likely saldo ID.
        connect_ids: For sweFN: paste saldo ID after each sweFN ID.
        delimiter: Delimiter character to put between ambiguous results
        affix: Optional character to put before and after results to mark a set.
        scoresep: Separator for the score and the saldo ID.
        lexicon: Optional preloaded lexicon.
    """
    if not lexicon:
        lexicon = util.misc.PickledLexicon(model.path)
    # Otherwise use preloaded lexicon

    sense = saldoids.read()
    token_pos = list(pos.read())
    out_annotation = pos.create_empty_attribute()

    # Check if the saldo IDs are ranked (= word senses have been disambiguated)
    wsd = saldoids.split()[1].split(".")[0] == "wsd"

    for token_index, token_sense in enumerate(sense):
        # Check if part of speech of this token is allowed
        if not pos_ok(token_pos, token_index, pos_limit):
            saldo_ids = None
            out_annotation[token_index] = affix
            continue

        if wsd and SCORESEP in token_sense:
            ranked_saldo = token_sense.strip(AFFIX).split(DELIM) if token_sense != AFFIX else None
            saldo_tuples = [(i.split(SCORESEP)[0], i.split(SCORESEP)[1]) for i in ranked_saldo]

            if not disambiguate:
                saldo_ids = [i[0] for i in saldo_tuples]

            # Only take the most likely analysis into account.
            # Handle wsd with equal probability for several words
            else:
                saldo_ids = [saldo_tuples[0]]
                del saldo_tuples[0]
                while saldo_tuples and (saldo_tuples[0][1] == saldo_ids[0][1]):
                    saldo_ids = [saldo_tuples[0]]
                    del saldo_tuples[0]

                saldo_ids = [i[0] for i in saldo_ids]

        else:  # No WSD
            saldo_ids = token_sense.strip(AFFIX).split(DELIM) if token_sense != AFFIX else None

        result = annotate(saldo_ids, lexicon, connect_ids, scoresep)
        out_annotation[token_index] = util.misc.cwbset(result, delimiter, affix) if result else affix
    out.write(out_annotation)


def pos_ok(token_pos: list[str], token_index: int, pos_limit: Iterable[str]) -> bool:
    """Check if the token's part of speech is in the allowed list.

    If no pos_limit is given, all tokens are allowed.

    Args:
        token_pos: List of part of speech tags for each token.
        token_index: Index of the current token.
        pos_limit: Iterable containing allowed part of speech tags.

    Returns:
        True if the token's part of speech is in the allowed list, False otherwise.
    """
    if not pos_limit:
        return True

    return token_pos[token_index] in pos_limit
