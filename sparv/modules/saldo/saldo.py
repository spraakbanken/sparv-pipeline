"""Create annotations from SALDO."""

import itertools
import re
from typing import List, Optional

from sparv.api import Annotation, Config, Model, Output, annotator, get_logger, util

from .saldo_model import SaldoLexicon

logger = get_logger(__name__)

# The minimum precision difference for two annotations to be considered equal
PRECISION_DIFF = 0.01


def preloader(models):
    """Preload SALDO models."""
    if not isinstance(models, list):
        models = [models]
    return {m.path.stem: SaldoLexicon(m.path) for m in models}


@annotator("SALDO annotations", language=["swe"], config=[
    Config("saldo.model", default="saldo/saldo.pickle", description="Path to SALDO model"),
    Config("saldo.delimiter", default=util.constants.DELIM, description="Character to put between ambiguous results"),
    Config("saldo.affix", default=util.constants.AFFIX, description="Character to put before and after sets of results"),
    Config("saldo.precision", "",
           description="Format string for appending precision to each value (e.g. ':%.3f')"),
    Config("saldo.precision_filter", default="max",
           description="Precision filter with values 'max' (only use the annotations that are most probable), "
                       "'first' (only use the most probable annotation(s)), 'none' (use all annotations)"),
    Config("saldo.min_precision", default=0.66,
           description="Only use annotations with a probability score higher than this"),
    Config("saldo.skip_multiword", default=False, description="Whether to disable annotation of multiword expressions"),
    Config("saldo.max_mwe_gaps", default=1, description="Max amount of gaps allowed within a multiword expression"),
    Config("saldo.allow_multiword_overlap", default=False,
           description="Whether all multiword expressions may overlap with each other. "
                       "If set to False, some cleanup is done."),
    Config("saldo.word_separator", default="",
           description="Character used to split the values of 'word' into several word variations"),
], preloader=preloader, preloader_params=["models"], preloader_target="models_preloaded")
def annotate(token: Annotation = Annotation("<token>"),
             word: Annotation = Annotation("<token:word>"),
             sentence: Annotation = Annotation("<sentence>"),
             reference: Annotation = Annotation("<token:ref>"),
             out_sense: Output = Output("<token>:saldo.sense", cls="token:sense", description="SALDO identifiers"),
             out_lemgram: Output = Output("<token>:saldo.lemgram", cls="token:lemgram", description="SALDO lemgrams"),
             out_baseform: Output = Output("<token>:saldo.baseform", cls="token:baseform",
                                           description="Baseforms from SALDO"),
             models: List[Model] = [Model("[saldo.model]")],
             msd: Optional[Annotation] = Annotation("<token:msd>"),
             delimiter: str = Config("saldo.delimiter"),
             affix: str = Config("saldo.affix"),
             precision: str = Config("saldo.precision"),
             precision_filter: str = Config("saldo.precision_filter"),
             min_precision: float = Config("saldo.min_precision"),
             skip_multiword: bool = Config("saldo.skip_multiword"),
             max_gaps: int = Config("saldo.max_mwe_gaps"),
             allow_multiword_overlap: bool = Config("saldo.allow_multiword_overlap"),
             word_separator: str = Config("saldo.word_separator"),
             models_preloaded: Optional[dict] = None):
    """Use the Saldo lexicon model to annotate msd-tagged words.

    Args:
        token (Annotation): Input annotation with token spans. Defaults to Annotation("<token>").
        word (Annotation): Input annotation with token strings. Defaults to Annotation("<token:word>").
        sentence (Annotation): Input annotation with sentence spans. Defaults to Annotation("<sentence>").
        reference (Annotation): Input annotation with token indices for each sentence.
            Defaults to Annotation("<token:ref>").
        out_sense (Output): Output annotation with senses from SALDO. Defaults to Output("<token>:saldo.sense").
        out_lemgram (Output): Output annotation with lemgrams from SALDO. Defaults to Output("<token>:saldo.lemgram").
        out_baseform (Output): Output annotation with baseforms from SALDO.
            Defaults to Output("<token>:saldo.baseform").
        models (List[Model]): A list of pickled lexicons, typically the SALDO model (saldo.pickle)
            and optional lexicons for older Swedish. Defaults to [Model("[saldo.model]")].
        msd (Annotation, optional): Input annotation with POS and morphological descriptions.
            Defaults to Annotation("<token:msd>").
        delimiter (str): Character to put between ambiguous results. Defaults to Config("saldo.delimiter").
        affix (str): Character to put before and after sets of results. Defaults to Config("saldo.affix").
        precision (str): Format string for appending precision to each value (e.g. ':%.3f'). use empty string for no
            precision. Defaults to Config("saldo.precision").
        precision_filter (str): Precision filter with values 'max' (only use the annotations that are most probable),
            'first' (only use the most probable annotation(s)), 'none' (use all annotations)".
            Defaults to Config("saldo.precision_filter").
        min_precision (float): Only use annotations with a probability score higher than this.
            Defaults to Config("saldo.min_precision").
        skip_multiword (bool): Whether to disable annotation of multiword expressions.
            Defaults to Config("saldo.skip_multiword").
        max_gaps (int): Max amount of gaps allowed within a multiword expression. Defaults to Config("saldo.max_gaps").
        allow_multiword_overlap (bool): Whether all multiword expressions may overlap with each other. If set to False,
            some cleanup is done. Defaults to Config("saldo.allow_multiword_overlap").
        word_separator (str): Character used to split the values of 'word' into several word variations.
            Defaults to Config("saldo.word_separator").
        models_preloaded (dict, optional): Preloaded models. Defaults to None.
    """
    main(token=token, word=word, sentence=sentence, reference=reference, out_sense=out_sense, out_lemgram=out_lemgram,
         out_baseform=out_baseform, models=models, msd=msd, delimiter=delimiter, affix=affix, precision=precision,
         precision_filter=precision_filter, min_precision=min_precision, skip_multiword=skip_multiword,
         max_gaps=max_gaps, allow_multiword_overlap=allow_multiword_overlap, word_separator=word_separator,
         models_preloaded=models_preloaded)


def main(token, word, sentence, reference, out_sense, out_lemgram, out_baseform, models, msd, delimiter, affix,
         precision, precision_filter, min_precision, skip_multiword, max_gaps, allow_multiword_overlap, word_separator,
         models_preloaded):
    """Do SALDO annotations with models."""
    # Allow use of multiple lexicons
    logger.progress()
    models_list = [(m.path.stem, m) for m in models]
    if not models_preloaded:
        lexicon_list = [(name, SaldoLexicon(lex.path)) for name, lex in models_list]
    # Use pre-loaded lexicons
    else:
        lexicon_list = []
        for name, _lex in models_list:
            assert models_preloaded.get(name, None) is not None, "Lexicon %s not found!" % name
            lexicon_list.append((name, models_preloaded[name]))

    # Combine annotation names in SALDO lexicon with out annotations
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
    skip_pos_check = (min_precision == 0.0)

    word_annotation = list(word.read())
    ref_annotation = list(reference.read())
    if msd:
        msd_annotation = list(msd.read())
    else:
        msd_annotation = word.create_empty_attribute()

    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)

    if orphans:
        logger.warning(f"Found {len(orphans)} tokens not belonging to any sentence. These will not be annotated.")

    out_annotation = word.create_empty_attribute()
    logger.progress(total=len(sentences) + 1)

    for sent in sentences:
        incomplete_multis = []  # [{annotation, words, [ref], is_particle, lastwordWasGap, numberofgaps}]
        complete_multis = []    # ([ref], annotation)
        sentence_tokens = {}

        for token_index in sent:
            theword = word_annotation[token_index]
            ref = ref_annotation[token_index]
            msdtag = msd_annotation[token_index] if msd else ""

            annotation_info = {}
            sentence_tokens[ref] = {"token_index": token_index, "annotations": annotation_info}

            # Support for multiple values of word
            if word_separator:
                thewords = [w for w in theword.split(word_separator) if w]
            else:
                thewords = [theword]

            # First use MSD tags to find the most probable single word annotations
            ann_tags_words = _find_single_word(thewords, lexicon_list, msdtag, precision, min_precision,
                                               precision_filter, annotation_info)

            # Find multi-word expressions
            if not skip_multiword:
                _find_multiword_expressions(incomplete_multis, complete_multis, thewords, ref, msdtag, max_gaps,
                                            ann_tags_words, msd_annotation, sent, skip_pos_check)

            # Loop to next token
        logger.progress()

        if not allow_multiword_overlap:
            # Check that we don't have any unwanted overlaps
            _remove_unwanted_overlaps(complete_multis)

        # Then save the rest of the multi word expressions in sentence_tokens
        _save_multiwords(complete_multis, sentence_tokens)

        for tok in list(sentence_tokens.values()):
            out_annotation[tok["token_index"]] = _join_annotation(tok["annotations"], delimiter, affix)

        # Loop to next sentence

    for out_annotation_obj, annotation_name in annotations:
        out_annotation_obj.write([v.get(annotation_name, delimiter) if v is not None else None for v in out_annotation])
    logger.progress()


################################################################################
# Auxiliaries
################################################################################

def _find_single_word(thewords, lexicon_list, msdtag, precision, min_precision, precision_filter, annotation_info):
    ann_tags_words = []

    for w in thewords:
        for name, lexicon in lexicon_list:
            if name == "saldo" or len(lexicon_list) == 1:
                prefix = ""
            else:
                prefix = name + "m--"
            annotation = []
            for a in lexicon.lookup(w):
                annotation.append(a + (prefix,))
            ann_tags_words += annotation
            # # Set break if each word only gets annotations from first lexicon that has entry for word
            # break

    annotation_precisions = [(get_precision(msdtag, msdtags), annotation, prefix)
                             for (annotation, msdtags, wordslist, _, _, prefix) in ann_tags_words if not wordslist]

    if min_precision > 0:
        annotation_precisions = [x for x in annotation_precisions if x[0] >= min_precision]
    annotation_precisions = _normalize_precision(annotation_precisions)
    annotation_precisions.sort(reverse=True, key=lambda x: x[0])

    if precision_filter and annotation_precisions:
        if precision_filter == "first":
            annotation_precisions = annotation_precisions[:1]
        elif precision_filter == "max":
            maxprec = annotation_precisions[0][0]

            # ismax = lambda lemprec: lemprec[0] >= maxprec - PRECISION_DIFF
            def ismax(lemprec):
                return lemprec[0] >= maxprec - PRECISION_DIFF
            annotation_precisions = itertools.takewhile(ismax, annotation_precisions)

    if precision:
        for (prec, annotation, prefix) in annotation_precisions:
            for key in annotation:
                annotation_entry = []
                for item in annotation[key]:
                    if not item.startswith(prefix):
                        annotation_entry.append(prefix + item)
                    else:
                        annotation_entry.append(item)
                annotation_info.setdefault(key, []).extend([a + precision % prec for a in annotation_entry])
    else:
        for (prec, annotation, prefix) in annotation_precisions:
            for key in annotation:
                annotation_entry = []
                for item in annotation[key]:
                    if not item.startswith(prefix):
                        annotation_entry.append(prefix + item)
                    else:
                        annotation_entry.append(item)
                annotation_info.setdefault(key, []).extend(annotation_entry)

    return ann_tags_words


def _find_multiword_expressions(incomplete_multis, complete_multis, thewords, ref, msdtag, max_gaps, ann_tags_words,
                                msd_annotation, sent, skip_pos_check):
    todelfromincomplete = []  # list to keep track of which expressions that have been completed

    for i, x in enumerate(incomplete_multis):
        # x = (annotations, following_words, [ref], gap_allowed, is_particle, [part-of-gap-boolean, gap_count])
        seeking_word = x[1][0]  # The next word we are looking for in this multi-word expression

        # Is a gap necessary in this position for this expression?
        if seeking_word == "*":
            if x[1][1].lower() in (w.lower() for w in thewords):
                seeking_word = x[1][1]
                del x[1][0]

        # If current gap is greater than max_gaps, stop searching
        if x[5][1] > max_gaps:
            todelfromincomplete.append(i)
        #                                                         |  Last word may not be PP if this is a particle-multi-word                      |
        elif seeking_word.lower() in (w.lower() for w in thewords) and (skip_pos_check or not (len(x[1]) == 1 and x[4] and msdtag.startswith("PP"))):
            x[5][0] = False     # last word was not a gap
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
                        if tag[:2] in ("NN", "PM", "UO"):
                            complete_multis.append((x[2], x[0]))
                            break

                else:
                    complete_multis.append((x[2], x[0]))

        else:
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
    looking_for = [(annotation, words, [ref], gap_allowed, is_particle, [False, 0])
                   for (annotation, _, wordslist, gap_allowed, is_particle, _) in ann_tags_words if wordslist for words in wordslist]
    if len(looking_for) > 0:
        incomplete_multis.extend(looking_for)


def _remove_unwanted_overlaps(complete_multis):
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
            if not a == b and re.search(r"\.(\w\w?)m?\.", a[1]["lem"][0]).groups()[0] == re.search(
                    r"\.(\w\w?)m?\.", b[1]["lem"][0]).groups()[0]:
                if b[0][0] < a[0][0] < b[0][-1] < a[0][-1]:
                    # A case of b1 a1 b2 a2. Remove a.
                    remove.add(ai)
                elif a[0][0] < b[0][0] and a[0][-1] == b[0][-1] and not all((x in a[0]) for x in b[0]):
                    # A case of a1 b1 ab2. Remove a.
                    remove.add(ai)

    for a in sorted(remove, reverse=True):
        del complete_multis[a]


def _save_multiwords(complete_multis, sentence_tokens):
    for c in complete_multis:
        first = True
        first_ref = ""
        for tok_ref in c[0]:
            if first:
                first_ref = tok_ref
            for ann, val in list(c[1].items()):
                if not first:
                    val = [x + ":" + first_ref for x in val]
                sentence_tokens[tok_ref]["annotations"].setdefault(ann, []).extend(val)
            first = False


def _join_annotation(annotation, delimiter, affix):
    """Convert annotations into cwb sets with unique values."""
    return dict([(a, util.misc.cwbset(list(dict.fromkeys(annotation[a])), delimiter=delimiter, affix=affix))
                 for a in annotation])


def get_precision(msd, msdtags):
    """
    Calculate the precision of a Saldo annotation.

    If the the word's msdtag is among the annotation's possible msdtags,
    we return a high value (0.75), a partial match returns 0.66, missing MSD returns 0.5,
    and otherwise a low value (0.25).
    """
    return (0.5 if msd is None else
            0.75 if msd in msdtags else
            0.66 if "." in msd and [partial for partial in msdtags if partial.startswith(msd[:msd.find(".")])] else
            0.25)


def _normalize_precision(annotations):
    """Normalize the rankings in the annotation list so that the sum is 1."""
    total_precision = sum(prec for (prec, _annotation, prefix) in annotations)
    return [(prec / total_precision, annotation, prefix) for (prec, annotation, prefix) in annotations]
