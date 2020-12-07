"""Annotate words with lexical classes from Blingbring or SweFN."""

import logging
from typing import List

import sparv.util as util
from sparv import Annotation, Config, Model, Output, annotator

log = logging.getLogger(__name__)


@annotator("Annotate tokens with Blingbring classes", language=["swe"], config=[
    Config("lexical_classes.bb_word_model", default="lexical_classes/blingbring.pickle",
           description="Path to Blingbring model")
])
def blingbring_words(out: Output = Output("<token>:lexical_classes.blingbring",
                                          description="Lexical classes for tokens from Blingbring"),
                     model: Model = Model("[lexical_classes.bb_word_model]"),
                     saldoids: Annotation = Annotation("<token:sense>"),
                     pos: Annotation = Annotation("<token:pos>"),
                     pos_limit: List[str] = ["NN", "VB", "JJ", "AB"],
                     class_set: str = "bring",
                     disambiguate: bool = True,
                     connect_ids: bool = False,
                     delimiter: str = util.DELIM,
                     affix: str = util.AFFIX,
                     scoresep: str = util.SCORESEP,
                     lexicon=None):
    """Blingbring specific wrapper for annotate_words. See annotate_words for more info."""
    # pos_limit="NN VB JJ AB" | None

    if class_set not in ["bring", "roget_head", "roget_subsection", "roget_section", "roget_class"]:
        log.warning("Class '%s' not available. Fallback to 'bring'.")
        class_set = "bring"

    # Blingbring annotation function
    def annotate_bring(saldo_ids, lexicon, connect_IDs=False, scoresep=util.SCORESEP):
        rogetid = set()
        if saldo_ids:
            for sid in saldo_ids:
                if connect_IDs:
                    rogetid = rogetid.union(set(i + scoresep + sid for i in lexicon.lookup(sid, default=set())))
                else:
                    rogetid = rogetid.union(lexicon.lookup(sid, default=dict()).get(class_set, set()))
        return sorted(rogetid)

    annotate_words(out, model, saldoids, pos, annotate_bring, pos_limit=pos_limit, disambiguate=disambiguate,
                   class_set=class_set, connect_ids=connect_ids, delimiter=delimiter, affix=affix, scoresep=scoresep,
                   lexicon=lexicon)


@annotator("Annotate tokens with Blingbring classes", language=["swe"], config=[
    Config("lexical_classes.swefn_word_model", default="lexical_classes/swefn.pickle",
           description="Path to SweFN model")
])
def swefn_words(out: Output = Output("<token>:lexical_classes.swefn",
                                     description="Lexical classes for tokens from SweFN"),
                model: Model = Model("[lexical_classes.swefn_word_model]"),
                saldoids: Annotation = Annotation("<token:sense>"),
                pos: Annotation = Annotation("<token:pos>"),
                pos_limit: List[str] = ["NN", "VB", "JJ", "AB"],
                disambiguate: bool = True,
                connect_ids: bool = False,
                delimiter: str = util.DELIM,
                affix: str = util.AFFIX,
                scoresep: str = util.SCORESEP,
                lexicon=None):
    """Swefn specific wrapper for annotate_words. See annotate_words for more info."""

    # SweFN annotation function
    def annotate_swefn(saldo_ids, lexicon, connect_IDs=False, scoresep=util.SCORESEP):
        swefnid = set()
        if saldo_ids:
            for sid in saldo_ids:
                if connect_IDs:
                    swefnid = swefnid.union(set(i + scoresep + sid for i in lexicon.lookup(sid, default=set())))
                else:
                    swefnid = swefnid.union(lexicon.lookup(sid, default=set()))
        return sorted(swefnid)

    annotate_words(out, model, saldoids, pos, annotate_swefn, pos_limit=pos_limit, disambiguate=disambiguate,
                   connect_ids=connect_ids, delimiter=delimiter, affix=affix, scoresep=scoresep, lexicon=lexicon)


def annotate_words(out: Output, model: Model, saldoids: Annotation, pos: Annotation, annotate, pos_limit: List[str],
                   class_set=None, disambiguate=True, connect_ids=False, delimiter=util.DELIM, affix=util.AFFIX,
                   scoresep=util.SCORESEP, lexicon=None):
    """
    Annotate words with blingbring classes (rogetID).

    - out_sent: resulting annotation file.
    - model: pickled lexicon with saldoIDs as keys.
    - saldoids, pos: existing annotation with saldoIDs/parts of speech.
    - annotate: annotation function, returns an iterable containing annotations
        for one token ID. (annotate_bring() or annotate_swefn())
    - pos_limit: parts of speech that will be annotated.
        Set to None to annotate all pos.
    - class_set: output Bring classes or Roget IDs ("bring", "roget_head",
        "roget_subsection", "roget_section" or "roget_class").
        Set to None when not annotating blingbring.
    - disambiguate: use WSD and use only the most likely saldo ID.
    - connect_IDs: for sweFN: paste saldo ID after each sweFN ID.
    - delimiter: delimiter character to put between ambiguous results
    - affix: optional character to put before and after results to mark a set.
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. This argument must be last.
    """
    if not lexicon:
        lexicon = util.PickledLexicon(model.path)
    # Otherwise use pre-loaded lexicon (from catapult)

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

        if wsd and util.SCORESEP in token_sense:
            ranked_saldo = token_sense.strip(util.AFFIX).split(util.DELIM) \
                if token_sense != util.AFFIX else None
            saldo_tuples = [(i.split(util.SCORESEP)[0], i.split(util.SCORESEP)[1]) for i in ranked_saldo]

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
            saldo_ids = token_sense.strip(util.AFFIX).split(util.DELIM) \
                if token_sense != util.AFFIX else None

        result = annotate(saldo_ids, lexicon, connect_ids, scoresep)
        out_annotation[token_index] = util.cwbset(result, delimiter, affix) if result else affix
    out.write(out_annotation)


def pos_ok(token_pos, token_index, pos_limit):
    """If there is a pos_limit, check if token has correct part of speech. Pass all tokens otherwise."""
    if pos_limit:
        return token_pos[token_index] in pos_limit
    else:
        return True
