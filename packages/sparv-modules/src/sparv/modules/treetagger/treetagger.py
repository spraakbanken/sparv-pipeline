"""Process tokens with TreeTagger.

Requires TreeTagger version 3.2.3 (https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/).
May work with newer versions.
Please make sure you have the tree-tagger binary file in your path.
You do not need to download any parameter files as Sparv will download these for you when necessary.
"""

from sparv.api import (
    Annotation,
    Binary,
    Config,
    Language,
    Model,
    ModelOutput,
    Output,
    annotator,
    get_logger,
    modelbuilder,
    util,
)
from sparv.api.util.tagsets import pos_to_upos

logger = get_logger(__name__)

SENT_SEP = "\n<eos>\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1
LEM_COLUMN = 2

TAG_SETS = {
    "bul": "BulTreeBank",
    "est": "TreeTagger",
    "fin": "FinnTreeBank",
    "lat": "TreeTagger",
    "nld": "TreeTagger",
    "pol": "NationalCorpusofPolish",
    "ron": "MULTEXT",
    "slk": "SlovakNationalCorpus",
    "deu": "STTS",
    "eng": "Penn",
    "fra": "TreeTagger",
    "spa": "TreeTagger",
    "ita": "TreeTagger",
    "rus": "TreeTagger",
}


@annotator(
    "Part-of-speech tags and baseforms from TreeTagger",
    language=["bul", "est", "fin", "lat", "nld", "pol", "ron", "slk", "deu", "eng", "fra", "spa", "ita", "rus"],
    config=[
        Config("treetagger.binary", "tree-tagger", description="TreeTagger executable"),
        Config("treetagger.model", "treetagger/[metadata.language].par", description="Path to TreeTagger model"),
    ],
)
def annotate(
    lang: Language = Language(),
    model: Model = Model("[treetagger.model]"),
    tt_binary: Binary = Binary("[treetagger.binary]"),
    out_upos: Output = Output("<token>:treetagger.upos", cls="token:upos", description="Part-of-speeches in UD"),
    out_pos: Output = Output("<token>:treetagger.pos", cls="token:pos", description="Part-of-speeches from TreeTagger"),
    out_baseform: Output = Output("<token>:treetagger.baseform", description="Baseforms from TreeTagger"),
    word: Annotation = Annotation("<token:word>"),
    sentence: Annotation = Annotation("<sentence>"),
    encoding: str = util.constants.UTF8,
) -> None:
    """POS/MSD tag and lemmatize using TreeTagger.

    Args:
        lang: Language of the corpus.
        model: Path to the TreeTagger model.
        tt_binary: Path to the TreeTagger binary.
        out_upos: Output for the universal POS tags.
        out_pos: Output for the TreeTagger POS tags.
        out_baseform: Output for the baseforms.
        word: Word annotation.
        sentence: Sentence annotation.
        encoding: Encoding to use for the input and output.
    """
    sentences, _orphans = sentence.get_children(word)
    word_annotation = list(word.read())
    stdin = SENT_SEP.join(TOK_SEP.join(word_annotation[token_index] for token_index in sent) for sent in sentences)
    args = ["-token", "-lemma", "-no-unknown", "-eos-tag", "<eos>", model.path]

    stdout, stderr = util.system.call_binary(tt_binary, args, stdin, encoding=encoding)
    logger.debug("Message from TreeTagger:\n%s", stderr)

    # Write pos and upos annotations.
    out_upos_annotation = word.create_empty_attribute()
    out_pos_annotation = word.create_empty_attribute()
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP), strict=True):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP), strict=True):
            cols = tagged_token.strip().split(TAG_SEP)
            if len(cols) >= TAG_COLUMN + 1:
                tag = cols[TAG_COLUMN]
            else:
                logger.warning("TreeTagger failed to produce a POS tag for token '%s'!", cols[0])
                tag = ""
            out_pos_annotation[token_id] = tag
            out_upos_annotation[token_id] = pos_to_upos(tag, lang, TAG_SETS.get(lang))
    out_pos.write(out_pos_annotation)
    out_upos.write(out_upos_annotation)

    # Write lemma annotations.
    out_lemma_annotation = word.create_empty_attribute()
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP), strict=True):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP), strict=True):
            cols = tagged_token.strip().split(TAG_SEP)
            if len(cols) >= LEM_COLUMN + 1:
                lem = cols[LEM_COLUMN]
            else:
                logger.warning(
                    "TreeTagger failed to produce a baseform for token '%s'! Using the wordform as baseform.", cols[0]
                )
                lem = cols[0]
            out_lemma_annotation[token_id] = lem
    out_baseform.write(out_lemma_annotation)


@modelbuilder("TreeTagger model for Bulgarian", language=["bul"])
def get_bul_model(
    out: ModelOutput = ModelOutput("treetagger/bul.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/bulgarian.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/bulgarian.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Estonian", language=["est"])
def get_est_model(
    out: ModelOutput = ModelOutput("treetagger/est.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/estonian.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/estonian.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Finnish", language=["fin"])
def get_fin_model(
    out: ModelOutput = ModelOutput("treetagger/fin.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/finnish.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/finnish.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Latin", language=["lat"])
def get_lat_model(
    out: ModelOutput = ModelOutput("treetagger/lat.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/latin.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/latin.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Dutch", language=["nld"])
def get_nld_model(
    out: ModelOutput = ModelOutput("treetagger/nld.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/dutch.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/dutch.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Polish", language=["pol"])
def get_pol_model(
    out: ModelOutput = ModelOutput("treetagger/pol.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/polish.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/polish.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Romanian", language=["ron"])
def get_ron_model(
    out: ModelOutput = ModelOutput("treetagger/ron.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/romanian.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/romanian.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Slovak", language=["slk"])
def get_slk_model(
    out: ModelOutput = ModelOutput("treetagger/slk.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/slovak.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/slovak.par.gz"
    _download(url, gzip, out)


# These can also be processed with Freeling:


@modelbuilder("TreeTagger model for Spanish", language=["spa"])
def get_spa_model(
    out: ModelOutput = ModelOutput("treetagger/spa.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/spanish.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/spanish.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for German", language=["deu"])
def get_deu_model(
    out: ModelOutput = ModelOutput("treetagger/deu.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/german.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/german.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for English", language=["eng"])
def get_eng_model(
    out: ModelOutput = ModelOutput("treetagger/eng.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/english.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/english.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for French", language=["fra"])
def get_fra_model(
    out: ModelOutput = ModelOutput("treetagger/fra.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/french.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/french.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Italian", language=["ita"])
def get_ita_model(
    out: ModelOutput = ModelOutput("treetagger/ita.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/italian.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/italian.par.gz"
    _download(url, gzip, out)


@modelbuilder("TreeTagger model for Russian", language=["rus"])
def get_rus_model(
    out: ModelOutput = ModelOutput("treetagger/rus.par"), _tt_binary: Binary = Binary("[treetagger.binary]")
) -> None:
    """Download TreeTagger language model."""
    gzip = "treetagger/russian.par.gz"
    url = "https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/russian.par.gz"
    _download(url, gzip, out)


def _download(url: str, gzip: str, out: ModelOutput) -> None:
    """Download and unzip the TreeTagger model."""
    gzip_model = Model(gzip)
    gzip_model.download(url)
    gzip_model.ungzip(out.path)
    gzip_model.remove()
