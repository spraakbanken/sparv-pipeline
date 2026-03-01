"""Annotators for historical Swedish."""

import operator
import re
from collections.abc import Iterable
from pathlib import Path

from sparv.api import Annotation, Config, Model, Output, annotator, get_logger, util
from sparv.api.util.tagsets import tagmappings
from sparv.modules.saldo import saldo

logger = get_logger(__name__)


@annotator(
    "Annotations from SALDO, Dalin and Swedberg",
    language=["swe-1800"],
    order=1,
    preloader=saldo.preloader,
    preloader_params=["models"],
    preloader_target="models_preloaded",
)
def annotate_saldo(
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("<token:word>"),
    sentence: Annotation = Annotation("<sentence>"),
    reference: Annotation = Annotation("<token:ref>"),
    out_sense: Output = Output(
        "<token>:hist.sense", cls="token:sense", description="Sense identifiers from SALDO, Dalin and Swedberg"
    ),
    out_lemgram: Output = Output(
        "<token>:hist.lemgram", cls="token:lemgram", description="Lemgrams from SALDO, Dalin and Swedberg"
    ),
    out_baseform: Output = Output(
        "<token>:hist.baseform", cls="token:baseform", description="Baseforms from SALDO, Dalin and Swedberg"
    ),
    models: Iterable[Model] = (Model("[saldo.model]"), Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")),
    msd: Annotation | None = Annotation("<token:msd>"),
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
    precision: str | None = Config("saldo.precision"),
    precision_filter: str = Config("saldo.precision_filter"),
    min_precision: float = Config("saldo.min_precision"),
    skip_multiword: bool = Config("saldo.skip_multiword"),
    max_gaps: int = Config("hist.max_mwe_gaps"),
    allow_multiword_overlap: bool = Config("saldo.allow_multiword_overlap"),
    word_separator: str | None = Config("saldo.word_separator"),
    models_preloaded: dict | None = None,
) -> None:
    """Use lexicon models (SALDO, Dalin and Swedberg) to annotate (potentially msd-tagged) words."""
    saldo.main(
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


@annotator(
    "Annotations from Schlyter and Söderwall",
    language=["swe-fsv"],
    preloader=saldo.preloader,
    preloader_params=["models"],
    preloader_target="models_preloaded",
    config=[
        Config(
            "hist.fsv_min_precision",
            default=0.25,
            description="Only use annotations with a probability score higher than this",
        )
    ],
)
def annotate_saldo_fsv(
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("<token>:hist.all_spelling_variants"),
    sentence: Annotation = Annotation("<sentence>"),
    reference: Annotation = Annotation("<token:ref>"),
    out_sense: Output = Output(
        "<token>:hist.sense", cls="token:sense", description="Sense identifiers from SALDO (empty dummy annotation)"
    ),
    out_lemgram: Output = Output(
        "<token>:hist.lemgram", cls="token:lemgram", description="Lemgrams from Schlyter and Söderwall"
    ),
    out_baseform: Output = Output(
        "<token>:hist.baseform", cls="token:baseform", description="Baseforms from Schlyter and Söderwall"
    ),
    models: Iterable[Model] = (Model("[hist.fsv_model]"),),
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
    precision: str | None = Config("saldo.precision"),
    precision_filter: str = Config("saldo.precision_filter"),
    min_precision: float = Config("hist.fsv_min_precision"),
    skip_multiword: bool = Config("saldo.skip_multiword"),
    max_gaps: int = Config("hist.max_mwe_gaps"),
    allow_multiword_overlap: bool = Config("saldo.allow_multiword_overlap"),
    word_separator: str = "|",
    models_preloaded: dict | None = None,
) -> None:
    """Use lexicon models (Schlyter and Söderwall) to annotate words."""
    saldo.main(
        token=token,
        word=word,
        sentence=sentence,
        reference=reference,
        out_sense=out_sense,
        out_lemgram=out_lemgram,
        out_baseform=out_baseform,
        models=models,
        msd="",
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


@annotator("Extract POS tags (homograph sets) from lemgrams", language=["swe-fsv"])
def extract_pos(
    out: Output = Output("<token>:hist.homograph_set", description="Sets of POS extracted from lemgrams"),
    lemgrams: Annotation = Annotation("<token:lemgram>"),
    extralemgrams: Annotation | None = Annotation("[hist.extralemgrams]"),
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
) -> None:
    """Extract POS tags from lemgrams.

    Args:
        out: The output annotation with sets of POS tags.
        lemgrams: Input lemgram annotation.
        extralemgrams: Additional annotation from which more pos-tags can be extracted.
        delimiter: Character to put between ambiguous results.
        affix: Character to put before and after sets of results.
    """

    def oktag(tag: re.Match | None) -> bool:
        return tag is not None and tag.group(1) not in {"e", "sxc", "mxc"}

    def mkpos(_: int, thelems: list[str]) -> list[str]:
        pos = [re.search(r"\.\.(.*?)\.", lem) for lem in thelems]
        mapping = tagmappings.mappings["saldo_pos_to_suc"]
        pos_lists = [mapping.get(p.group(1), []) for p in pos if oktag(p)]
        return sorted({y for x in pos_lists for y in x})

    _annotate_standard(out, lemgrams, mkpos, extralemgrams, delimiter=delimiter, affix=affix)


@annotator(
    "Get fallback lemgrams from Dalin or Swedberg",
    language=["swe-1800"],
    order=2,
    config=[
        Config("hist.lemgram_key", default="lem", description="Key to lookup in the lexicon"),
    ],
    preloader=saldo.preloader,
    preloader_params=["models"],
    preloader_target="models_preloaded",
)
def lemgram_fallback(
    out: Output = Output(
        "<token>:hist.lemgram", cls="token:lemgram", description="Fallback lemgrams from Dalin or Swedberg"
    ),
    word: Annotation = Annotation("<token:word>"),
    msd: Annotation = Annotation("<token:msd>"),
    lemgram: Annotation = Annotation("<token>:saldo.lemgram"),
    key: str = Config("hist.lemgram_key"),
    models: Iterable[Model] = (Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")),
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
    models_preloaded: dict | None = None,
) -> None:
    """Lookup lemgrams in models for words that do not already have a lemgram.

    Args:
        out: The output annotation.
        word: Input annotation with token strings.
        msd: Input annotation with POS and morphosyntactig desciptions.
        lemgram: Input annotation with SALDO lemgrams.
        key: Key to lookup in the models.
        models: A list of lexicon models.
        delimiter: Character to put between ambiguous results.
        affix: Character to put before and after sets of results.
        models_preloaded: Preloaded models.

    """
    _annotate_fallback(
        out=out,
        word=word,
        msd=msd,
        main_annotation=lemgram,
        key=key,
        models=models,
        delimiter=delimiter,
        affix=affix,
        models_preloaded=models_preloaded,
    )


@annotator(
    "Get fallback baseforms from Dalin or Swedberg",
    language=["swe-1800"],
    order=2,
    config=[
        Config("hist.baseform_key", default="gf", description="Key to lookup in the lexicon"),
    ],
    preloader=saldo.preloader,
    preloader_params=["models"],
    preloader_target="models_preloaded",
)
def baseform_fallback(
    out: Output = Output(
        "<token>:hist.baseform", cls="token:baseform", description="Fallback baseforms from Dalin or Swedberg"
    ),
    word: Annotation = Annotation("<token:word>"),
    msd: Annotation = Annotation("<token:msd>"),
    baseform: Annotation = Annotation("<token>:saldo.baseform"),
    key: str = Config("hist.baseform_key"),
    models: Iterable[Model] = (Model("[hist.dalin_model]"), Model("[hist.swedberg_model]")),
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
    models_preloaded: dict | None = None,
) -> None:
    """Lookup baseforms in models for words that do not already have a baseform.

    Args:
        out: The output annotation.
        word: Input annotation with token strings.
        msd: Input annotation with POS and morphosyntactig desciptions.
        baseform: Input annotation with SALDO baseforms.
        key: Key to lookup in the models.
        models: A list of lexicon models.
        delimiter: Character to put between ambiguous results.
        affix: Character to put before and after sets of results.
        models_preloaded: Preloaded models.

    """
    _annotate_fallback(
        out=out,
        word=word,
        msd=msd,
        main_annotation=baseform,
        key=key,
        models=models,
        delimiter=delimiter,
        affix=affix,
        models_preloaded=models_preloaded,
    )


@annotator("Convert POS into sets", language=["swe-1800"])
def posset(
    pos: Annotation = Annotation("<token:pos>"),
    out: Output = Output("<token>:hist.homograph_set", description="POS converted into sets"),
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
) -> None:
    """Annotate with POS sets by converting a single POS into a set (mostly used to make corpora comparable).

    Args:
        pos: Input annotation with part-of-speech tags.
        out: Output annotation with sets of part-of-speech tags.
        delimiter: Character to put between ambiguous results.
        affix: Character to put before and after sets of results.
    """

    def makeset(_: int, thepos: str) -> list[str]:
        """Annotate thepos with separators (dummy function)."""  # noqa: DOC201
        return [thepos]

    _annotate_standard(out, pos, makeset, delimiter=delimiter, affix=affix, split=False)


@annotator(
    "Get spelling variants from spelling model for Old Swedish",
    language=["swe-fsv"],
    preloader=saldo.preloader,
    preloader_params=["model"],
    preloader_target="model_preloaded",
)
def spelling_variants(
    word: Annotation = Annotation("<token:word>"),
    out: Output = Output("<token>:hist.spelling_variants", description="token spelling variants"),
    spellingmodel: Model = Model("[hist.fsv_spelling]"),
    # model: Model = Model("[hist.fsv_model]"),
    delimiter: str = Config("hist.delimiter"),
    affix: str = Config("hist.affix"),
    # model_preloaded: dict | None = None
) -> None:
    """Use a lexicon model and a spelling model to annotate words with their spelling variants.

    Args:
        word: Input annotation with token strings.
        out: Output annotation with spelling variations.
        spellingmodel: The spelling model.
        model: The lexicon model.
        delimiter: Character to put between ambiguous results.
        affix: Character to put before and after sets of results.
        model_preloaded: Preloaded morphology model.
    """
    # # Load model
    # model_name = model.path.stem
    # if not model_preloaded:
    #     lexicon = (model_name, saldo.SaldoLexicon(model.path))
    # # Use pre-loaded lexicon
    # else:
    #     assert model_preloaded.get(model_name, None) is not None, "Lexicon %s not found!" % model_name
    #     lexicon = (model_name, model_preloaded[model_name])

    def parsevariant(modelfile: Path) -> dict[str, list[tuple[str, float]]]:
        # spellingmodel -> {word : [(variant, dist)]}
        d = {}

        def addword(res: dict, word: str, info: str) -> None:
            for part in info.strip().split("^^"):
                if part:
                    xs = part.split(",")
                    res.setdefault(word, []).append((xs[0], float(xs[1])))

        with modelfile.open(encoding="utf8") as f:
            for line in f:
                wd, info = line.split(":::")
                addword(d, wd, info)
        return d

    variations = parsevariant(spellingmodel.path)

    def findvariants(_: int, theword: str) -> list[str]:
        variants = [x_d for x_d in variations.get(theword.lower(), []) if x_d[0] != theword]
        return sorted({v for v, d in variants})
        # variants_lists = [_get_single_annotation([lexicon], v, "lem", "") for v, _d in variants]
        # return set([y for x in variants_lists for y in x])

    _annotate_standard(out, word, findvariants, delimiter=delimiter, affix=affix, split=False)


@annotator("Merge token and spelling variants into one annotation", language=["swe-fsv"])
def all_spelling_variants(
    out: Output = Output("<token>:hist.all_spelling_variants", description="Original token and spelling variants"),
    word: Annotation = Annotation("<token:word>"),
    variants: Annotation = Annotation("<token>:hist.spelling_variants"),
) -> None:
    """Merge token and spelling variants into one annotation."""
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.merge_to_set(out, left=word, right=variants, unique=False, sort=False)


################################################################################
# Auxiliaries
################################################################################


def _annotate_standard(
    out: Output,
    input_annotation: Annotation,
    annotator: callable,
    extra_input: str = "",
    delimiter: str = util.constants.DELIM,
    affix: str = util.constants.AFFIX,
    split: bool = True,
) -> None:
    """Apply the 'annotator' function to the annotations in 'input_annotation' and write the new output to 'out'.

    Args:
        out: The output annotation.
        input_annotation: The input annotation.
        annotator: function which is to be applied to the input annotation.
        extra_input: An additional input annotation.
        delimiter: Delimiter character to put between ambiguous results.
        affix: Character to put before and after results.
        split: Defines whether the input annotation is a set, with elements separated by delimiter.
            If so, return a list. Else, return one single element.
    """
    # Join input_annotation and extra_input with delimiter
    annotations = input_annotation.read()
    if extra_input:
        annotations = [delimiter.join([x, y]) for x, y in zip(annotations, extra_input.read(), strict=True)]

    out_annotation = []
    for token_index, annot in enumerate(annotations):
        if split:
            annot = [x for x in annot.split(delimiter) if x]  # noqa: PLW2901

        # Pass annot to annotator and convert into cwbset
        annots = list(dict.fromkeys(annotator(token_index, annot)))
        out_annotation.append(util.misc.cwbset(annots, delimiter=delimiter, affix=affix))

    out.write(out_annotation)


def _annotate_fallback(
    out: Output,
    word: Annotation,
    msd: Annotation,
    main_annotation: Annotation,
    key: str,
    models: Iterable[Model],
    delimiter: str,
    affix: str,
    models_preloaded: dict | None = None,
) -> None:
    """Lookup 'key' in models for words that are lacking 'main_annotation'."""
    # Allow use of multiple lexicons
    models_list = [(m.path.stem, m) for m in models]
    if not models_preloaded:
        lexicon_list = [(name, saldo.SaldoLexicon(lex.path)) for name, lex in models_list]
    # Use pre-loaded lexicons
    else:
        lexicon_list = []
        for name, _lex in models_list:
            assert models_preloaded.get(name, None) is not None, f"Lexicon {name} not found!"
            lexicon_list.append((name, models_preloaded[name]))

    word_annotation = list(word.read())
    msd_annotation = list(msd.read())

    def annotate_empties(token_index: int, annotation: str) -> list[str]:
        fallbacks = []
        if not annotation:
            word = word_annotation[token_index]
            msdtag = msd_annotation[token_index]
            fallbacks.extend(_get_single_annotation(lexicon_list, word, key, msdtag))
        return fallbacks

    _annotate_standard(out, main_annotation, annotate_empties, delimiter=delimiter, affix=affix)


def _get_single_annotation(
    lexicons: list[tuple[str, saldo.SaldoLexicon]], word: str, key: str, msdtag: str
) -> list[str]:
    """Get 'key' from lexicon(s) for a word.

    Only the first lexicon that returns a result is used.

    Args:
        lexicons: List of lexicon tuples (name, lexicon).
        word: The word to look up.
        key: The key to look up in the lexicon.
        msdtag: The MSD tag for the word.

    Returns:
        A list of annotations for the word.
    """
    annotation = []
    for _, lexicon in lexicons:
        # Get precision and 'key' annotation
        annotation = [
            (saldo.get_precision(msdtag, msdtags), ann)
            for (ann, msdtags, wordslist, _, _) in lexicon.lookup(word)
            if not wordslist
        ]
        if annotation:
            break
    # Sort by precision (descending) and remove precision values
    annotation_lists = [a.get(key, []) for _, a in sorted(annotation, reverse=True, key=operator.itemgetter(0))]
    return [y for x in annotation_lists for y in x]
