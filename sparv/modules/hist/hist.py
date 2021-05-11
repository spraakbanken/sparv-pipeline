"""Annotators for historical Swedish."""

import re
from typing import List, Optional

import sparv.modules.saldo.saldo as saldo
import sparv.util as util
from sparv import Annotation, Config, Model, Output, annotator

log = util.get_logger(__name__)


def annotate_variants(word, out, spellmodel, model=None):
    """Use a lexicon model and a spelling model to annotate words with their spelling variants.

    - word is existing annotations for wordforms
    - out is a string containing the resulting annotation file
    - spellmodel is the spelling model
    - model is the lexicon model
    """
    # model -> {word : [(variant, dist)]}
    def parsevariant(modelfile):
        d = {}

        def addword(res, word, info):
            for part in info.strip().split("^^"):
                if part:
                    xs = part.split(",")
                    res.setdefault(word, []).append((xs[0], float(xs[1])))

        with open(modelfile, encoding="utf8") as f:
            for line in f:
                wd, info = line.split(":::")
                addword(d, wd, info)
        return d

    # if model is None:
    #     lexicon = saldo.SaldoLexicon(model)

    variations = parsevariant(spellmodel)

    def findvariants(_tokid, theword):
        variants = [x_d for x_d in variations.get(theword.lower(), []) if x_d[0] != theword]
        # variants_lists = [get_single_annotation(lexicon, v, "lemgram") for v, d in variants]
        # return set([y for x in variants_lists for y in x])
        return set([v for v, d in variants])

    annotate_standard(out, word, findvariants, split=False)


@annotator("Extract POS tags (homograph sets) from lemgrams", language=["swe-1800"], order=2)
def extract_pos(out: Output = Output("<token>:hist.homograph_set", description="Sets of POS extracted from lemgrams"),
                lemgrams: Annotation = Annotation("<token>:saldo.lemgram"),
                extralemgrams: Optional[Annotation] = Annotation("[hist.extralemgrams]")):
    """Extract POS tags from lemgrams.

    Args:
        out (Output): The output annotation. Defaults to Output("<token>:hist.homograph_set").
        lemgrams (Annotation): Input lemgram annotation. Defaults to Annotation("<token>:saldo.lemgram").
        extralemgrams (Optional[Annotation], optional): Additional annotation from which more pos-tags can be extracted.
            Defaults to Annotation("[hist.extralemgrams]").
    """
    def oktag(tag):
        return tag is not None and tag.group(1) not in ["e", "sxc", "mxc"]

    def mkpos(thelems):
        pos = [re.search(r"\.\.(.*?)\.", lem) for lem in thelems]
        mapping = util.tagsets.mappings["saldo_pos_to_suc"]
        pos_lists = [mapping.get(p.group(1), []) for p in pos if oktag(p)]
        return set([y for x in pos_lists for y in x])

    annotate_standard(out, lemgrams, mkpos, extralemgrams)


# TODO: Split into fallback_lemgram and fallback_baseform?
@annotator("Convert POS into sets", language=["swe-1800"], config=[
    Config("hist.lemgram_key", default="lemgram", description="Key to lookup in the lexicon"),
])  # preloader=preloader, preloader_params=["models"], preloader_target="models_preloaded")
def annotate_fallback(
    out: Output = Output("<token>:hist.lemgram", description="Fallback lemgrams from Dalin or Swedberg"),
    word: Annotation = Annotation("<token:word>"),
    msd: Annotation = Annotation("<token:msd>"),
    lemgram: Annotation = Annotation("<token>:saldo.lemgram"),
    models: List[Model] = [Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")],
    key: str = Config("hist.lemgram_key"),
    models_preloaded: Optional[dict] = None
):
    """Lookup lemgrams in models for words that do not already have a lemgram.

    Args:
        out (Output): The output annotation. Defaults to Output("<token>:hist.lemgram").
        word (Annotation): Input annotation with token strings. Defaults to Annotation("<token:word>").
        msd (Annotation): Input annotation with POS and morphosyntactig desciptions. Defaults to Annotation("<token:msd>").
        lemgram (Annotation): Input annotation with SALDO lemgrams. Defaults to Annotation("<token>:saldo.lemgram").
        models (List[Model], optional): A list of lexicon models. Defaults to [Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")].
        key (str): Key to lookup in the models. Defaults to Config("hist.lemgram_key").
        models_preloaded (dict, optional): ??

    """
    # Allow use of multiple lexicons
    models_list = [(m.path.stem, m) for m in models]
    if not models_preloaded:
        lexicon_list = [(name, saldo.SaldoLexicon(lex.path)) for name, lex in models_list]
    # Use pre-loaded lexicons
    else:
        lexicon_list = []
        for name, _lex in models_list:
            assert models_preloaded.get(name, None) is not None, "Lexicon %s not found!" % name
            lexicon_list.append((name, models_preloaded[name]))

    word_annotation = list(word.read())
    msd_annotation = list(msd.read())

    def annotate_empties(tokid, lemgrams):
        fallbacks = []
        if not lemgrams:
            word = word_annotation[tokid]
            msdtag = msd_annotation[tokid]
            fallbacks.extend(get_single_annotation(lexicon_list, word, key, msdtag))
        return fallbacks

    annotate_standard(out, lemgram, annotate_empties)


@annotator("Convert POS into sets", language=["swe-1800"], order=1)
def posset(out: Output = Output("<token>:hist.homograph_set", description="POS converted into sets"),
           pos: Annotation = Annotation("<token:pos>")):
    """Annotate with POS sets by converting a single POS into a set."""
    def makeset(thepos):
        """Annotate thepos with separators (dummy function)."""
        return [thepos]

    annotate_standard(out, pos, makeset, split=False)


@annotator("Convert POS into sets", language=["swe-1800"], config=[
    Config("hist.precision", "",
           description="Format string for appending precision to each value (e.g. ':%.3f')")
]) # preloader=preloader, preloader_params=["models"], preloader_target="models_preloaded")
def annotate_full(token: Annotation = Annotation("<token>"),
                  word: Annotation = Annotation("<token:word>"),
                  sentence: Annotation = Annotation("<sentence>"),
                  reference: Annotation = Annotation("<token>:misc.number_rel_<sentence>"),
                  out_sense: Output = Output("<token>:hist.sense", cls="token:sense", description="SALDO identifier"),
                  out_lemgram: Output = Output("<token>:hist.lemgram", description="SALDO lemgram"),
                  out_baseform: Output = Output("<token>:hist.baseform", cls="token:baseform",
                                                description="Baseform from SALDO"),
                  models: List[Model] = [Model("[saldo.model]"), Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")],
                  msd: Optional[Annotation] = Annotation("<token:msd>"),
                  delimiter: str = util.DELIM,
                  affix: str = util.AFFIX,
                  precision: str = Config("hist.precision"),
                  precision_filter: str = "",
                  min_precision: float = 0.0,
                  skip_multiword: bool = False,
                  allow_multiword_overlap: bool = False,
                  word_separator: str = "",
                  models_preloaded: Optional[dict] = None):
    # TODO merge with saldo.py
    """Use an lmf-lexicon model to annotate (pos-tagged) words.

    - word, msd are existing annotations for wordforms and part-of-speech
    - sentence is an existing annotation for sentences and their children (words)
    - reference is an existing annotation for word references, to be used when
      annotating multi-word units
    - out is a string containing a whitespace separated list of the resulting annotation files
    - annotations is a string containing a whitespace separate list of annotations to be written.
      Currently: gf (= baseform), lem (=lemgram)
      Number of annotations and their order must correspond to the list in the 'out' argument.
    - model is the Saldo model
    - delimiter is the delimiter character to put between ambiguous results
    - affix is an optional character to put before and after results
    - precision is a format string for how to print the precision for each annotation
      (use empty string for no precision)
    - precision_filter is an optional filter, currently there are the following values:
      max: only use the annotations that are most probable
      first: only use the most probable annotation (or one of the most probable if more than one)
    - min_precision: only use annotations with a probability score higher than this
    - skip_multiword can be set to True to disable multi word annotations
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. This argument must be last.
    """
    # Allow use of multiple lexicons
    models_list = [(m.path.stem, m) for m in models]
    if not models_preloaded:
        lexicon_list = [(name, saldo.SaldoLexicon(lex.path)) for name, lex in models_list]
    # Use pre-loaded lexicons
    else:
        lexicon_list = []
        for name, _lex in models_list:
            assert models_preloaded.get(name, None) is not None, "Lexicon %s not found!" % name
            lexicon_list.append((name, models_preloaded[name]))

    # Maximum number of gaps in multi-word units.
    # Set to 0 since many (most?) multi-word in the old lexicons are unseparable (half öre etc)
    max_gaps = 0

    # Combine annotation names in SALDO lexicon with out annotations
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

    if orphans:
        log.warning(f"Found {len(orphans)} tokens not belonging to any sentence. These will not be annotated.")

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
            ann_tags_words = saldo.find_single_word(thewords, lexicon_list, msdtag, precision, min_precision,
                                                    precision_filter, annotation_info)
            # Find multi-word expressions
            if not skip_multiword:
                saldo.find_multiword_expressions(incomplete_multis, complete_multis, thewords, ref, msdtag, max_gaps,
                                                 ann_tags_words, msd_annotation, sent, skip_pos_check)

            # Loop to next token

        if not allow_multiword_overlap:
            # Check that we don't have any unwanted overlaps
            saldo.remove_unwanted_overlaps(complete_multis)

        # Then save the rest of the multi word expressions in sentence_tokens
        saldo.save_multiwords(complete_multis, sentence_tokens)

        for tok in list(sentence_tokens.values()):
            out_annotation[tok["token_index"]] = saldo._join_annotation(tok["annotations"], delimiter, affix)

        # Loop to next sentence

    for out_annotation_obj, annotation_name in annotations:
        out_annotation_obj.write([v.get(annotation_name, delimiter) if v is not None else None for v in out_annotation])


################################################################################
# Auxiliaries
################################################################################

def annotate_standard(out, input_annotation, annotator, extra_input="", delimiter: str = util.DELIM,
                      affix: str = util.AFFIX, split=True):
    """Apply the 'annotator' function to the annotations in 'input_annotation' and write the new output to 'out'.

    Args:
        out: The output annotation.
        input_annotation: The input annotation.
        annotator: function which is to be applied to the input annotation.
            It should have type :: oldannotations -> newannotations
        extra_input (str, optional): An additional input annotation. Defaults to "".
        delimiter (str, optional): Delimiter character to put between ambiguous results. Defaults to "|".
        affix (str, optional): Character to put before and after results. Defaults to "|".
        split (bool, optional): Defines whether the input annatoation is a set, with elements separated by delimiter.
            If so, return a list. Else, return one single element. Defaults to True.
    """
    # Join input_annotation and extra_input with delimiter
    annotations = input_annotation.read()
    if extra_input:
        annotations = [delimiter.join([x, y]) for x, y in zip(annotations, extra_input.read())]

    out_annotation = []
    for annot in annotations:
        if split:
            annot = [x for x in annot.split(delimiter) if x != ""]

        # Pass annot to annotator and convert into cwbset
        out_annotation.append(util.cwbset(set(annotator(annot)), delimiter=delimiter, affix=affix))

    out.write(out_annotation)


def get_single_annotation(lexicons, word, key, msdtag):
    """Get 'key' from lexicon(s) for each token."""
    annotation = []
    for _, lexicon in lexicons:
        # Get precision and 'key' annotation
        annotation = [(saldo.get_precision(msdtag, msdtags), ann) for (ann, msdtags, wordslist, _, _) in lexicon.lookup(word)
                      if not wordslist]
        if annotation:
            break
    # Sort by precision (descending) and remove precision values
    annotation_lists = [a.get(key) for _, a in sorted(annotation, reverse=True)]
    return [y for x in annotation_lists for y in x]
