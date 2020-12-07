"""Download models for Stanza."""

import json

from sparv import Model, ModelOutput, modelbuilder


@modelbuilder("Stanza resources file", language=["swe"])
def stanza_resources_file(resources_file: ModelOutput = ModelOutput("stanza/resources.json")):
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


@modelbuilder("Stanza POS-tagging model", language=["swe"])
def stanza_pos_model(model: ModelOutput = ModelOutput("stanza/pos/full_sv_talbanken_tagger.pt"),
                     pretrain: ModelOutput = ModelOutput("stanza/pos/full_sv_talbanken.pretrain.pt")):
    """Download and unzip the Stanza POS-tagging model."""
    zip_model = Model("stanza/pos/synt_stanza_full.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/stanza/morph_stanza_full.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza lemmatisation model", language=["swe"])
def stanza_lem_model(model: ModelOutput = ModelOutput("stanza/lem/sv_suc_lemmatizer.pt")):
    """Download and unzip the Stanza POS-tagging model."""
    zip_model = Model("stanza/lem/synt_stanza_full.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/stanza/lem_stanza.zip")
    zip_model.unzip()
    zip_model.remove()


@modelbuilder("Stanza dependency model", language=["swe"])
def stanza_dep_model(model: ModelOutput = ModelOutput("stanza/dep/sv_talbanken_parser.pt"),
                     pretrain: ModelOutput = ModelOutput("stanza/dep/sv_talbanken.pretrain.pt")):
    """Download and unzip the Stanza dependency model."""
    zip_model = Model("stanza/dep/synt_stanza_full.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/stanza/synt_stanza_full.zip")
    zip_model.unzip()
    zip_model.remove()
