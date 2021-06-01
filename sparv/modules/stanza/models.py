"""Download models for Stanza."""

import json
import logging

import iso639

from sparv.api import Language, Model, ModelOutput, modelbuilder, get_logger

logger = get_logger(__name__)


@modelbuilder("Stanza resources file for Swedish", language=["swe"])
def stanza_resources_file(resources_file: ModelOutput = ModelOutput("stanza/swe/resources.json")):
    """Download and unzip the Stanza dependency model."""
    # Write resources.json file to keep Stanza from complaining
    res = json.dumps({
        "sv": {
            "lang_name": "Swedish",
            "tokenize": {
                "orchid": {},
                "best": {}
            },
            "default_processors": {
                "tokenize": "orchid"
            },
            "default_dependencies": {},
        }})
    resources_file.write(res)


@modelbuilder("Stanza pretrain (embeddings) model for Swedish", language=["swe"])
def stanza_pretrain_model(model: ModelOutput = ModelOutput("stanza/swe/sv_talbanken.pretrain.pt")):
    """Download and unzip the Stanza pretrain (embeddings) model."""
    zip_model = Model("stanza/swe/stanza_pretrain.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/!svn/bc/230835/pub/stanza/stanza_pretrain.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza POS-tagging model for Swedish", language=["swe"])
def stanza_pos_model(model: ModelOutput = ModelOutput("stanza/swe/pos/sv_talbanken_tagger.pt")):
    """Download and unzip the Stanza POS-tagging model."""
    zip_model = Model("stanza/swe/pos/synt_stanza_full2.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/!svn/bc/230835/pub/stanza/morph_stanza_full2.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza lemmatisation model for Swedish", language=["swe"])
def stanza_lem_model(model: ModelOutput = ModelOutput("stanza/swe/lem/sv_suc_lemmatizer.pt")):
    """Download and unzip the Stanza POS-tagging model."""
    zip_model = Model("stanza/swe/lem/lem_stanza.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/!svn/bc/230835/pub/stanza/lem_stanza.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza dependency model for Swedish", language=["swe"])
def stanza_dep_model(model: ModelOutput = ModelOutput("stanza/swe/dep/sv_talbanken_parser.pt")):
    """Download and unzip the Stanza dependency model."""
    zip_model = Model("stanza/swe/dep/synt_stanza_full2.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/!svn/bc/230835/pub/stanza/synt_stanza_full2.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza models for other languages than Swedish", language=["eng"])
def get_model(lang: Language = Language(),
              resources_file: ModelOutput = ModelOutput("stanza/[metadata.language]/resources.json")):
    """Download Stanza language models."""
    import stanza
    lang_name = iso639.languages.get(part3=lang).name if lang in iso639.languages.part3 else lang
    stanza_lang = iso639.languages.get(part3=lang).part1
    logger.info(f"Downloading Stanza language model for {lang_name}")
    stanza.download(lang=stanza_lang, model_dir=str(resources_file.path.parent), verbose=False,
                    logging_level=logging.WARNING)
    zip_file = Model(f"stanza/{lang}/{stanza_lang}/default.zip")
    zip_file.remove()
