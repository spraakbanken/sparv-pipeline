"""Create annotations from SALDO."""

import itertools
import logging
import re
from typing import List, Optional

import sparv.util as util
from sparv import Annotation, Config, Model, Output, annotator
from sparv.modules.saldo.saldo_model import SaldoLexicon

log = logging.getLogger(__name__)

# The minimum precision difference for two annotations to be considered equal
PRECISION_DIFF = 0.01


@annotator("SALDO annotations", language=["swe"], config=[
    Config("saldo.model", default="saldo/saldo.pickle", description="Path to SALDO model"),
    Config("saldo.precision", "",
           description="Format string for appending precision to each value")
])
def annotate(token: Annotation = Annotation("<token>"),
             word: Annotation = Annotation("<token:word>"),
             sentence: Annotation = Annotation("<sentence>"),
             reference: Annotation = Annotation("<token>:misc.number_rel_<sentence>"),
             out_sense: Output = Output("<token>:saldo.sense", cls="token:sense", description="SALDO identifier"),
             out_lemgram: Output = Output("<token>:saldo.lemgram", description="SALDO lemgram"),
             out_baseform: Output = Output("<token>:saldo.baseform", cls="token:baseform",
                                           description="Baseform from SALDO"),
             models: List[Model] = [Model("[saldo.model]")],
             msd: Optional[Annotation] = Annotation("<token:msd>"),
             delimiter: str = util.DELIM,
             affix: str = util.AFFIX,
             precision: str = Config("saldo.precision"),
             precision_filter: str = "max",
             min_precision: float = 0.66,
             skip_multiword: bool = False,
             allow_multiword_overlap: bool = False,
             word_separator: str = "",
             lexicons=None):
    """Use the Saldo lexicon model (and optionally other older lexicons) to annotate pos-tagged words.

    - token, word, msd, sentence, reference: existing annotations
    - out_baseform, out_lemgram, out_sense: resulting annotations to be written
    - models: a list of pickled lexica, typically the Saldo model (saldo.pickle)
      and optional lexicons for older Swedish.
    - delimiter: delimiter character to put between ambiguous results
    - affix: an optional character to put before and after results
    - precision: a format string for how to print the precision for each annotation, e.g. ":%.3f"
      (use empty string for no precision)
    - precision_filter: an optional filter, currently there are the following values:
        max: only use the annotations that are most probable
        first: only use the most probable annotation (or one of the most probable if more than one)
        none: use all annotations
    - min_precision: only use annotations with a probability score higher than this
    - skip_multiword: set to True to disable multi word annotations
    - allow_multiword_overlap: by default we do some cleanup among overlapping multi word annotations.
      By setting this to True, all overlaps will be allowed.
    - word_separator: an optional character used to split the values of "word" into several word variations
    - lexicons: this argument cannot be set from the command line, but is used in the catapult.
      This argument must be last.
    """
    # Allow use of multiple lexicons
    models_list = [(m.path.stem, m) for m in models]
    if not lexicons:
        lexicon_list = [(name, SaldoLexicon(lex.path)) for name, lex in models_list]
    # Use pre-loaded lexicons (from catapult)
    else:
        lexicon_list = []
        for name, _lex in models_list:
            assert lexicons.get(name, None) is not None, "Lexicon %s not found!" % name
            lexicon_list.append((name, lexicons[name]))

    # Maximum number of gaps in multi-word units.
    # TODO: Set to 0 for hist-mode? since many (most?) multi-word in the old lexicons are inseparable (half öre etc)
    max_gaps = 1

    # Combine annotation names i SALDO lexicon with out annotations
    annotations = []
    if out_baseform:
        annotations.append((out_baseform, "gf"))
    if out_lemgram:
        annotations.append((out_lemgram, "lem"))
    if out_sense:
        annotations.append((out_sense, "saldo"))

    if skip_multiword:
        log.info("Skipping multi word annotations")

    min_precision = float(min_precision)

    # If min_precision is 0, skip almost all part-of-speech checking (verb multi-word expressions still won't be
    # allowed to span over other verbs)
    skip_pos_check = (min_precision == 0.0)

    word_annotation = list(word.read())
    ref_annotation = list(reference.read())
    if msd:
        msd_annotation = list(msd.read())

    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)

    out_annotation = word.create_empty_attribute()

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
            ann_tags_words = find_single_word(thewords, lexicon_list, msdtag, precision, min_precision,
                                              precision_filter, annotation_info)

            # Find multi-word expressions
            if not skip_multiword:
                find_multiword_expressions(incomplete_multis, complete_multis, thewords, ref, msdtag, max_gaps,
                                           ann_tags_words, msd_annotation, sent, skip_pos_check)

            # Loop to next token

        if not allow_multiword_overlap:
            # Check that we don't have any unwanted overlaps
            remove_unwanted_overlaps(complete_multis)

        # Then save the rest of the multi word expressions in sentence_tokens
        save_multiwords(complete_multis, sentence_tokens)

        for tok in list(sentence_tokens.values()):
            out_annotation[tok["token_index"]] = _join_annotation(tok["annotations"], delimiter, affix)

        # Loop to next sentence

    for out_annotation_obj, annotation_name in annotations:
        out_annotation_obj.write([v.get(annotation_name, delimiter) for v in out_annotation])


################################################################################
# Auxiliaries
################################################################################


def find_single_word(thewords, lexicon_list, msdtag, precision, min_precision, precision_filter, annotation_info):
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
            # Set break if each word only gets annotations from first lexicon that has entry for word
            # break

    annotation_precisions = [(get_precision(msdtag, msdtags), annotation, prefix)
                             for (annotation, msdtags, wordslist, _, _, prefix) in ann_tags_words if not wordslist]

    if min_precision > 0:
        annotation_precisions = [x for x in annotation_precisions if x[0] >= min_precision]
    annotation_precisions = normalize_precision(annotation_precisions)
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


def find_multiword_expressions(incomplete_multis, complete_multis, thewords, ref, msdtag, max_gaps, ann_tags_words,
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


def remove_unwanted_overlaps(complete_multis):
    remove = set()
    for ai, a in enumerate(complete_multis):
        for b in complete_multis:
            # Check if both are of same POS
            if not a == b and re.search(r"\.(\w\w?)m?\.", a[1]["lem"][0]).groups()[0] == re.search(r"\.(\w\w?)m?\.", b[1]["lem"][0]).groups()[0]:
                if b[0][0] < a[0][0] < b[0][-1] < a[0][-1]:
                    # A case of b1 a1 b2 a2. Remove a.
                    remove.add(ai)
                elif a[0][0] < b[0][0] and a[0][-1] == b[0][-1] and not all((x in a[0]) for x in b[0]):
                    # A case of a1 b1 ab2. Remove a.
                    remove.add(ai)

    for a in sorted(remove, reverse=True):
        del complete_multis[a]


def save_multiwords(complete_multis, sentence_tokens):
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
    seen = set()
    return dict([(a, affix + delimiter.join(b for b in annotation[a] if b not in seen and not seen.add(b)) + affix) for a in annotation])


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


def normalize_precision(annotations):
    """Normalize the rankings in the annotation list so that the sum is 1."""
    total_precision = sum(prec for (prec, _annotation, prefix) in annotations)
    return [(prec / total_precision, annotation, prefix) for (prec, annotation, prefix) in annotations]
