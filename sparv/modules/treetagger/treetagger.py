"""Process tokens with TreeTagger."""

import logging

import sparv.util as util
from sparv import Annotation, Binary, Config, Document, Language, Model, ModelOutput, Output, annotator, modelbuilder

log = logging.getLogger(__name__)

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
    # TODO: Write tag translations for: spa, fra, ita, rus
}


@annotator("Part-of-speech tags and baseforms from TreeTagger",
           language=["bul", "est", "fin", "lat", "nld", "pol", "ron", "slk", "eng"],
           config=[
               Config("treetagger.binary", "treetagger/tree-tagger"),
               Config("treetagger.model", "treetagger/[language].par")
           ])
def annotate(doc: str = Document,
             lang: str = Language,
             model: str = Model("[treetagger.model]"),
             tt_binary: str = Binary("[treetagger.binary]"),
             out_upos: str = Output("<token>:treetagger.upos", cls="token:upos", description="Part-of-speeches in UD"),
             out_pos: str = Output("<token>:treetagger.pos", cls="token:pos",
                                   description="Part-of-speeches from TreeTagger"),
             out_baseform: str = Output("<token>:treetagger.baseform", description="Baseforms from TreeTagger"),
             word: str = Annotation("<token:word>"),
             sentence: str = Annotation("<sentence>"),
             encoding: str = util.UTF8):
    """POS/MSD tag and lemmatize using TreeTagger."""
    sentences, _orphans = util.get_children(doc, sentence, word)
    word_annotation = list(util.read_annotation(doc, word))
    stdin = SENT_SEP.join(TOK_SEP.join(word_annotation[token_index] for token_index in sent)
                          for sent in sentences)
    args = ["-token", "-lemma", "-cap-heuristics", "-no-unknown", "-eos-tag", "<eos>", model]

    stdout, stderr = util.system.call_binary(tt_binary, args, stdin, encoding=encoding)
    log.debug("Message from TreeTagger:\n%s", stderr)

    # Write pos and upos annotations.
    out_upos_annotation = util.create_empty_attribute(doc, word_annotation)
    out_pos_annotation = util.create_empty_attribute(doc, word_annotation)
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            out_pos_annotation[token_id] = tag
            out_upos_annotation[token_id] = util.convert_to_upos(tag, lang, TAG_SETS.get(lang))
    util.write_annotation(doc, out_pos, out_pos_annotation)
    util.write_annotation(doc, out_upos, out_upos_annotation)

    # Write lemma annotations.
    out_lemma_annotation = util.create_empty_attribute(doc, word_annotation)
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            lem = tagged_token.strip().split(TAG_SEP)[LEM_COLUMN]
            out_lemma_annotation[token_id] = lem
    util.write_annotation(doc, out_baseform, out_lemma_annotation)


@modelbuilder("TreeTagger model for Bulgarian", optional=True)
def get_bul_model(out: str = ModelOutput("treetagger/bul.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/bulgarian.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/bulgarian.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Estonian", optional=True)
def get_est_model(out: str = ModelOutput("treetagger/est.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/estonian.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/estonian.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Finnish", optional=True)
def get_fin_model(out: str = ModelOutput("treetagger/fin.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/finnish.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/finnish.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Latin", optional=True)
def get_lat_model(out: str = ModelOutput("treetagger/lat.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/latin.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/latin.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Dutch", optional=True)
def get_nld_model(out: str = ModelOutput("treetagger/nld.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/dutch.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/dutch.par.gz", gzip)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Polish", optional=True)
def get_pol_model(out: str = ModelOutput("treetagger/pol.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/polish.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/polish.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Romanian", optional=True)
def get_ron_model(out: str = ModelOutput("treetagger/ron.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/romanian.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/romanian.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Slovak", optional=True)
def get_slk_model(out: str = ModelOutput("treetagger/slk.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/slovak.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/slovak.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


# These can also be processed with Freeling:


@modelbuilder("TreeTagger model for Spanish", optional=True)
def get_spa_model(out: str = ModelOutput("treetagger/spa.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/spanish.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/spanish.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for German", optional=True)
def get_deu_model(out: str = ModelOutput("treetagger/deu.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/german.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/german.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for English", optional=True)
def get_eng_model(out: str = ModelOutput("treetagger/eng.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/english.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/english.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for French", optional=True)
def get_fra_model(out: str = ModelOutput("treetagger/fra.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/french.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/french.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Italian", optional=True)
def get_ita_model(out: str = ModelOutput("treetagger/ita.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/italian.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/italian.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])


@modelbuilder("TreeTagger model for Russian", optional=True)
def get_rus_model(out: str = ModelOutput("treetagger/rus.par"),
                  tt_binary: str = Binary("[treetagger.binary]")):
    """Download TreeTagger language model."""
    gzip = "treetagger/russian.par.gz"
    util.download_model("http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/russian.par.gz", out)
    util.ungzip_model(gzip, out)
    util.remove_model_files([gzip])
