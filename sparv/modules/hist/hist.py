"""Annotators for historical Swedish."""

import re
from typing import List, Optional

import sparv.modules.saldo.saldo as saldo
from sparv.api import Annotation, Config, Model, Output, annotator, get_logger, util
from sparv.api.util.tagsets import tagmappings

logger = get_logger(__name__)


@annotator("Annotations from SALDO, Dalin and Swedberg", language=["swe-1800"], order=1, preloader=saldo.preloader,
           preloader_params=["models"], preloader_target="models_preloaded")
def annotate_saldo(
        token: Annotation = Annotation("<token>"),
        word: Annotation = Annotation("<token:word>"),
        sentence: Annotation = Annotation("<sentence>"),
        reference: Annotation = Annotation("<token:ref>"),
        out_sense: Output = Output("<token>:hist.sense", cls="token:sense",
                                   description="Sense identifiers from SALDO, Dalin and Swedberg"),
        out_lemgram: Output = Output("<token>:hist.lemgram", cls="token:lemgram",
                                     description="Lemgrams from SALDO, Dalin and Swedberg"),
        out_baseform: Output = Output("<token>:hist.baseform", cls="token:baseform",
                                      description="Baseforms from SALDO, Dalin and Swedberg"),
        models: List[Model] = [Model("[saldo.model]"), Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")],
        msd: Optional[Annotation] = Annotation("<token:msd>"),
        delimiter: str = Config("hist.delimiter"),
        affix: str = Config("hist.affix"),
        precision: str = Config("saldo.precision"),
        precision_filter: str = Config("saldo.precision_filter"),
        min_precision: float = Config("saldo.min_precision"),
        skip_multiword: bool = Config("saldo.skip_multiword"),
        max_gaps: int = Config("hist.max_mwe_gaps"),
        allow_multiword_overlap: bool = Config("saldo.allow_multiword_overlap"),
        word_separator: str = Config("saldo.word_separator"),
        models_preloaded: Optional[dict] = None):
    """Use lexicon models (SALDO, Dalin and Swedberg) to annotate (potentially msd-tagged) words."""
    saldo.main(token=token, word=word, sentence=sentence, reference=reference, out_sense=out_sense,
               out_lemgram=out_lemgram, out_baseform=out_baseform, models=models, msd=msd, delimiter=delimiter,
               affix=affix, precision=precision, precision_filter=precision_filter, min_precision=min_precision,
               skip_multiword=skip_multiword, max_gaps=max_gaps, allow_multiword_overlap=allow_multiword_overlap,
               word_separator=word_separator, models_preloaded=models_preloaded)


@annotator("Annotations from Schlyter and Söderwall", language=["swe-fsv"],
           preloader=saldo.preloader, preloader_params=["models"], preloader_target="models_preloaded",
           config=[Config("hist.fsv_min_precision", default=0.25,
                   description="Only use annotations with a probability score higher than this")])
def annotate_saldo_fsv(
        token: Annotation = Annotation("<token>"),
        word: Annotation = Annotation("<token>:hist.all_spelling_variants"),
        sentence: Annotation = Annotation("<sentence>"),
        reference: Annotation = Annotation("<token:ref>"),
        out_sense: Output = Output("<token>:hist.sense", cls="token:sense",
                                   description="Sense identifiers from SALDO (empty dummy annotation)"),
        out_lemgram: Output = Output("<token>:hist.lemgram", cls="token:lemgram",
                                     description="Lemgrams from Schlyter and Söderwall"),
        out_baseform: Output = Output("<token>:hist.baseform", cls="token:baseform",
                                      description="Baseforms from Schlyter and Söderwall"),
        models: List[Model] = [Model("[hist.fsv_model]")],
        delimiter: str = Config("hist.delimiter"),
        affix: str = Config("hist.affix"),
        precision: str = Config("saldo.precision"),
        precision_filter: str = Config("saldo.precision_filter"),
        min_precision: float = Config("hist.fsv_min_precision"),
        skip_multiword: bool = Config("saldo.skip_multiword"),
        max_gaps: int = Config("hist.max_mwe_gaps"),
        allow_multiword_overlap: bool = Config("saldo.allow_multiword_overlap"),
        word_separator: str = "|",
        models_preloaded: Optional[dict] = None):
    """Use lexicon models (Schlyter and Söderwall) to annotate words."""
    saldo.main(token=token, word=word, sentence=sentence, reference=reference, out_sense=out_sense,
               out_lemgram=out_lemgram, out_baseform=out_baseform, models=models, msd="", delimiter=delimiter,
               affix=affix, precision=precision, precision_filter=precision_filter, min_precision=min_precision,
               skip_multiword=skip_multiword, max_gaps=max_gaps, allow_multiword_overlap=allow_multiword_overlap,
               word_separator=word_separator, models_preloaded=models_preloaded)


@annotator("Extract POS tags (homograph sets) from lemgrams", language=["swe-fsv"])
def extract_pos(out: Output = Output("<token>:hist.homograph_set", description="Sets of POS extracted from lemgrams"),
                lemgrams: Annotation = Annotation("<token:lemgram>"),
                extralemgrams: Optional[Annotation] = Annotation("[hist.extralemgrams]"),
                delimiter: str = Config("hist.delimiter"),
                affix: str = Config("hist.affix")):
    """Extract POS tags from lemgrams.

    Args:
        out (Output): The output annotation. Defaults to Output("<token>:hist.homograph_set").
        lemgrams (Annotation): Input lemgram annotation. Defaults to Annotation("<token>:saldo.lemgram").
        extralemgrams (Optional[Annotation], optional): Additional annotation from which more pos-tags can be extracted.
            Defaults to Annotation("[hist.extralemgrams]").
        delimiter (str): Character to put between ambiguous results. Defaults to Config("hist.delimiter").
        affix (str): Character to put before and after sets of results. Defaults to Config("hist.affix").
    """
    def oktag(tag):
        return tag is not None and tag.group(1) not in ["e", "sxc", "mxc"]

    def mkpos(_, thelems):
        pos = [re.search(r"\.\.(.*?)\.", lem) for lem in thelems]
        mapping = tagmappings.mappings["saldo_pos_to_suc"]
        pos_lists = [mapping.get(p.group(1), []) for p in pos if oktag(p)]
        return sorted(list(set([y for x in pos_lists for y in x])))

    _annotate_standard(out, lemgrams, mkpos, extralemgrams, delimiter=delimiter, affix=affix)


@annotator("Get fallback lemgrams from Dalin or Swedberg", language=["swe-1800"], order=2, config=[
    Config("hist.lemgram_key", default="lem", description="Key to lookup in the lexicon"),
], preloader=saldo.preloader, preloader_params=["models"], preloader_target="models_preloaded")
def lemgram_fallback(
    out: Output = Output("<token>:hist.lemgram", cls="token:lemgram",
                         description="Fallback lemgrams from Dalin or Swedberg"),
    word: Annotation = Annotation("<token:word>"),
    msd: Annotation = Annotation("<token:msd>"),
    lemgram: Annotation = Annotation("<token>:saldo.lemgram"),
    key: str = Config("hist.lemgram_key"),
    models: List[Model] = [Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")],
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
    models_preloaded: Optional[dict] = None
):
    """Lookup lemgrams in models for words that do not already have a lemgram.

    Args:
        out (Output): The output annotation. Defaults to Output("<token>:hist.lemgram").
        word (Annotation): Input annotation with token strings. Defaults to Annotation("<token:word>").
        msd (Annotation): Input annotation with POS and morphosyntactig desciptions. Defaults to Annotation("<token:msd>").
        lemgram (Annotation): Input annotation with SALDO lemgrams. Defaults to Annotation("<token>:saldo.lemgram").
        key (str): Key to lookup in the models. Defaults to Config("hist.lemgram_key").
        models (List[Model], optional): A list of lexicon models. Defaults to [Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")].
        delimiter (str): Character to put between ambiguous results. Defaults to Config("hist.delimiter").
        affix (str): Character to put before and after sets of results. Defaults to Config("hist.affix").
        models_preloaded (dict, optional): Preloaded models. Defaults to None.

    """
    _annotate_fallback(out=out, word=word, msd=msd, main_annotation=lemgram, key=key, models=models, delimiter=delimiter,
                       affix=affix, models_preloaded=models_preloaded)


@annotator("Get fallback baseforms from Dalin or Swedberg", language=["swe-1800"], order=2, config=[
    Config("hist.baseform_key", default="gf", description="Key to lookup in the lexicon"),
], preloader=saldo.preloader, preloader_params=["models"], preloader_target="models_preloaded")
def baseform_fallback(
    out: Output = Output("<token>:hist.baseform", cls="token:baseform",
                         description="Fallback baseforms from Dalin or Swedberg"),
    word: Annotation = Annotation("<token:word>"),
    msd: Annotation = Annotation("<token:msd>"),
    baseform: Annotation = Annotation("<token>:saldo.baseform"),
    key: str = Config("hist.baseform_key"),
    models: List[Model] = [Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")],
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
    models_preloaded: Optional[dict] = None
):
    """Lookup baseforms in models for words that do not already have a baseform.

    Args:
        out (Output): The output annotation. Defaults to Output("<token>:hist.baseform").
        word (Annotation): Input annotation with token strings. Defaults to Annotation("<token:word>").
        msd (Annotation): Input annotation with POS and morphosyntactig desciptions. Defaults to Annotation("<token:msd>").
        baseform (Annotation): Input annotation with SALDO baseforms. Defaults to Annotation("<token>:saldo.baseform").
        key (str): Key to lookup in the models. Defaults to Config("hist.baseform_key").
        models (List[Model], optional): A list of lexicon models. Defaults to [Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")].
        delimiter (str): Character to put between ambiguous results. Defaults to Config("hist.delimiter").
        affix (str): Character to put before and after sets of results. Defaults to Config("hist.affix").
        models_preloaded (dict, optional): Preloaded models. Defaults to None.

    """
    _annotate_fallback(out=out, word=word, msd=msd, main_annotation=baseform, key=key, models=models, delimiter=delimiter,
                       affix=affix, models_preloaded=models_preloaded)


@annotator("Convert POS into sets", language=["swe-1800"])
def posset(pos: Annotation = Annotation("<token:pos>"),
           out: Output = Output("<token>:hist.homograph_set", description="POS converted into sets"),
           delimiter: str = Config("hist.delimiter"),
           affix: str = Config("hist.affix")):
    """Annotate with POS sets by converting a single POS into a set (mostly used to make corpora comparable).

    Args:
        pos (Annotation, optional): Input annotation with part-of-speech tags. Defaults to Annotation("<token:pos>").
        out (Output, optional): Output annotation with sets of part-of-speech tags.
            Defaults to Output("<token>:hist.homograph_set").
        delimiter (str): Character to put between ambiguous results. Defaults to Config("hist.delimiter").
        affix (str): Character to put before and after sets of results. Defaults to Config("hist.affix").
    """
    def makeset(_, thepos):
        """Annotate thepos with separators (dummy function)."""
        return [thepos]

    _annotate_standard(out, pos, makeset, delimiter=delimiter, affix=affix, split=False)


@annotator("Get spelling variants from spelling model for Old Swedish", language=["swe-fsv"],
           preloader=saldo.preloader, preloader_params=["model"], preloader_target="model_preloaded")
def spelling_variants(word: Annotation = Annotation("<token:word>"),
                      out: Output = Output("<token>:hist.spelling_variants", description="token spelling variants"),
                      spellingmodel: Model = Model("[hist.fsv_spelling]"),
                      # model: Model = Model("[hist.fsv_model]"),
                      delimiter: str = Config("hist.delimiter"),
                      affix: str = Config("hist.affix"),
                      # model_preloaded: Optional[dict] = None
                      ):
    """Use a lexicon model and a spelling model to annotate words with their spelling variants.

    Args:
        word (Annotation, optional): Input annotation with token strings. Defaults to Annotation("<token:word>").
        out (Output, optional): Output annotation with spelling variations. Defaults to Output("").
        spellingmodel (Model): The spelling model. Defaults to Model("[hist.fsv_spelling]")
        model (Model): The lexicon model. Defaults to Model("[hist.fsv_model]")
        delimiter (str): Character to put between ambiguous results. Defaults to Config("hist.delimiter").
        affix (str): Character to put before and after sets of results. Defaults to Config("hist.affix").
        model_preloaded (dict, optional): Preloaded morphology model. Defaults to None.
    """
    # # Load model
    # model_name = model.path.stem
    # if not model_preloaded:
    #     lexicon = (model_name, saldo.SaldoLexicon(model.path))
    # # Use pre-loaded lexicon
    # else:
    #     assert model_preloaded.get(model_name, None) is not None, "Lexicon %s not found!" % model_name
    #     lexicon = (model_name, model_preloaded[model_name])

    def parsevariant(modelfile):
        # spellingmodel -> {word : [(variant, dist)]}
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

    variations = parsevariant(spellingmodel.path)

    def findvariants(_, theword):
        variants = [x_d for x_d in variations.get(theword.lower(), []) if x_d[0] != theword]
        return sorted(list(set([v for v, d in variants])))
        # variants_lists = [_get_single_annotation([lexicon], v, "lem", "") for v, _d in variants]
        # return set([y for x in variants_lists for y in x])

    _annotate_standard(out, word, findvariants, delimiter=delimiter, affix=affix, split=False)


@annotator("Merge token and spelling variants into one annotation", language=["swe-fsv"])
def all_spelling_variants(
        out: Output = Output("<token>:hist.all_spelling_variants", description="Original token and spelling variants"),
        word: Annotation = Annotation("<token:word>"),
        variants: Annotation = Annotation("<token>:hist.spelling_variants")):
    """Merge token and spelling variants into one annotation."""
    from sparv.modules.misc import misc
    misc.merge_to_set(out, left=word, right=variants, unique=False, sort=False)


################################################################################
# Auxiliaries
################################################################################

def _annotate_standard(out, input_annotation, annotator, extra_input="", delimiter: str = util.constants.DELIM,
                       affix: str = util.constants.AFFIX, split=True):
    """Apply the 'annotator' function to the annotations in 'input_annotation' and write the new output to 'out'.

    Args:
        out: The output annotation.
        input_annotation: The input annotation.
        annotator: function which is to be applied to the input annotation.
            It should have type :: oldannotations -> newannotations
        extra_input (str, optional): An additional input annotation. Defaults to "".
        delimiter (str, optional): Delimiter character to put between ambiguous results. Defaults to
            util.constants.DELIM.
        affix (str, optional): Character to put before and after results. Defaults to util.constants.AFFIX.
        split (bool, optional): Defines whether the input annatoation is a set, with elements separated by delimiter.
            If so, return a list. Else, return one single element. Defaults to True.
    """
    # Join input_annotation and extra_input with delimiter
    annotations = input_annotation.read()
    if extra_input:
        annotations = [delimiter.join([x, y]) for x, y in zip(annotations, extra_input.read())]

    out_annotation = []
    for token_index, annot in enumerate(annotations):
        if split:
            annot = [x for x in annot.split(delimiter) if x != ""]

        # Pass annot to annotator and convert into cwbset
        annots = list(dict.fromkeys(annotator(token_index, annot)))
        out_annotation.append(util.misc.cwbset(annots, delimiter=delimiter, affix=affix))

    out.write(out_annotation)


def _annotate_fallback(out, word, msd, main_annotation, key, models, delimiter, affix, models_preloaded):
    """Lookup 'key' in models for words that are lacking 'main_annotation'."""
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

    def annotate_empties(token_index, annotation):
        fallbacks = []
        if not annotation:
            word = word_annotation[token_index]
            msdtag = msd_annotation[token_index]
            fallbacks.extend(_get_single_annotation(lexicon_list, word, key, msdtag))
        return fallbacks

    _annotate_standard(out, main_annotation, annotate_empties, delimiter=delimiter, affix=affix)


def _get_single_annotation(lexicons, word, key, msdtag):
    """Get 'key' from lexicon(s) for each token."""
    annotation = []
    for _, lexicon in lexicons:
        # Get precision and 'key' annotation
        annotation = [(saldo.get_precision(msdtag, msdtags), ann) for (ann, msdtags, wordslist, _, _) in lexicon.lookup(word)
                      if not wordslist]
        if annotation:
            break
    # Sort by precision (descending) and remove precision values
    annotation_lists = [a.get(key, []) for _, a in sorted(annotation, reverse=True, key=lambda x: x[0])]
    return [y for x in annotation_lists for y in x]
