"""Download models for Stanza."""

import json
import logging

from sparv.api import Language, Model, ModelOutput, get_logger, modelbuilder, util

logger = get_logger(__name__)


@modelbuilder("Stanza resources file for Swedish", language=["swe"])
def stanza_resources_file(resources_file: ModelOutput = ModelOutput("stanza/swe/resources.json")) -> None:
    """Download and unzip the Stanza dependency model.

    Args:
        resources_file: Path to the resources.json file to be created.
    """
    # Write resources.json file to keep Stanza from complaining
    res = json.dumps(
        {
            "sv": {
                "lang_name": "Swedish",
                "tokenize": {"orchid": {}, "best": {}},
                "default_processors": {"tokenize": "orchid"},
                "default_dependencies": {},
                "packages": {"default": {"tokenize": "orchid"}},
            }
        }
    )
    resources_file.write(res)


@modelbuilder("Stanza pretrain (embeddings) model for Swedish", language=["swe"])
def stanza_pretrain_model(_model: ModelOutput = ModelOutput("stanza/swe/sv_talbanken.pretrain.pt")) -> None:
    """Download and unzip the Stanza pretrain (embeddings) model.

    Args:
        _model: The pretrain model to be downloaded.
    """
    zip_model = Model("stanza/swe/stanza_pretrain.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/!svn/bc/246558/pub/stanza/stanza_pretrain.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza POS-tagging model for Swedish", language=["swe"])
def stanza_pos_model(_model: ModelOutput = ModelOutput("stanza/swe/pos/sv_talbanken_tagger.pt")) -> None:
    """Download and unzip the Stanza POS-tagging model.

    Args:
        _model: The POS-tagging model to be downloaded.
    """
    zip_model = Model("stanza/swe/pos/synt_stanza_full2.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/!svn/bc/230835/pub/stanza/morph_stanza_full2.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza lemmatization model for Swedish", language=["swe"])
def stanza_lem_model(_model: ModelOutput = ModelOutput("stanza/swe/lem/sv_suc_lemmatizer.pt")) -> None:
    """Download and unzip the Stanza POS-tagging model.

    Args:
        _model: The lemmatization model to be downloaded.
    """
    zip_model = Model("stanza/swe/lem/lem_stanza.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/!svn/bc/230835/pub/stanza/lem_stanza.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza dependency model for Swedish", language=["swe"])
def stanza_dep_model(_model: ModelOutput = ModelOutput("stanza/swe/dep/sv_talbanken_parser.pt")) -> None:
    """Download and unzip the Stanza dependency model.

    Args:
        _model: The dependency model file to be downloaded.
    """
    zip_model = Model("stanza/swe/dep/synt_stanza_full2.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/!svn/bc/230835/pub/stanza/synt_stanza_full2.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza models for other languages than Swedish", language=["eng"])
def get_model(
    lang: Language = Language(), resources_file: ModelOutput = ModelOutput("stanza/[metadata.language]/resources.json")
) -> None:
    """Download Stanza language models.

    Args:
        lang: The language code.
        resources_file: Path to the resources.json file to be downloaded.
    """
    import stanza  # noqa: PLC0415

    lang_name = util.misc.get_language_name_by_part3(lang) or lang
    stanza_lang = util.misc.get_language_part1_by_part3(lang)
    logger.info("Downloading Stanza language model for %s", lang_name)
    stanza.download(
        lang=stanza_lang, model_dir=str(resources_file.path.parent), verbose=False, logging_level=logging.WARNING
    )
    zip_file = Model(f"stanza/{lang}/{stanza_lang}/default.zip")
    zip_file.remove()
