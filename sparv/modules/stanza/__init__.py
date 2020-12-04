"""POS tagging, lemmatisation and dependency parsing with Stanza."""

from sparv import Config

from . import stanza, models

__config__ = [
    Config("stanza.resources_file", default="stanza/resources.json", description="Stanza resources file"),
    Config("stanza.lem_model", default="stanza/lem/sv_suc_lemmatizer.pt", description="Stanza lemmatisation model"),
    Config("stanza.pos_model", default="stanza/pos/full_sv_talbanken_tagger.pt", description="Stanza POS model"),
    Config("stanza.pretrain_pos_model", default="stanza/pos/full_sv_talbanken.pretrain.pt",
           description="Stanza pretrain POS model"),
    Config("stanza.dep_model", default="stanza/dep/sv_talbanken_parser.pt", description="Stanza dependency model"),
    Config("stanza.pretrain_dep_model", default="stanza/pos/full_sv_talbanken.pretrain.pt",
           description="Stanza pretrain dependency model")
]
