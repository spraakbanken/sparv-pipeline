"""POS tagging, lemmatization and dependency parsing with Stanza."""

from sparv.api import Config

from . import models, stanza, stanza_swe

__config__ = [
    Config(
        "stanza.resources_file",
        default="stanza/[metadata.language]/resources.json",
        description="Stanza resources file",
        datatype=str,
    ),
    Config("stanza.use_gpu", default=True, description="Use GPU instead of CPU if available", datatype=bool),
    Config(
        "stanza.batch_size",
        default=5000,
        description="Limit Stanza batch size. Sentences with a token count exceeding this value will be excluded "
        "from analysis.",
        datatype=int,
    ),
    Config(
        "stanza.max_sentence_length",
        default=250,
        description="Max length (in number of tokens) of sentences that will get dependence annotations (set to 0 "
        "for no limit)",
        datatype=int,
    ),
    Config(
        "stanza.cpu_fallback",
        default=False,
        description="Fall back to CPU for sentences exceeding the max_sentence_length, instead of "
        "excluding them from dependence parsing. Only usable with use_gpu enabled.",
        datatype=bool,
    ),
    Config(
        "stanza.max_token_length",
        default=0,
        description="Max number of characters per token. Any sentence containing a token exceeding this limit will "
        "be excluded from analysis. Disabled by default.",
        datatype=int,
    ),
    Config(
        "stanza.sentence_chunk",
        default="<text>",
        description="Text chunk (annotation) to use as input when segmenting sentences (not used for Swedish)",
        datatype=str,
    ),
    Config(
        "stanza.sentence_annotation",
        description="Optional existing sentence segmentation annotation (not used for Swedish)",
        datatype=str,
    ),
    Config(
        "stanza.token_annotation", description="Optional existing token annotation (not used for Swedish)", datatype=str
    ),
    # Config for Swedish
    Config(
        "stanza.swe_lem_model",
        default="stanza/swe/lem/sv_suc_lemmatizer.pt",
        description="Stanza lemmatization model for Swedish",
        datatype=str,
    ),
    Config(
        "stanza.swe_pos_model",
        default="stanza/swe/pos/sv_talbanken_tagger.pt",
        description="Stanza POS model for Swedish",
        datatype=str,
    ),
    Config(
        "stanza.swe_pretrain_pos_model",
        default="stanza/swe/sv_talbanken.pretrain.pt",
        description="Stanza pretrain POS model for Swedish",
        datatype=str,
    ),
    Config(
        "stanza.swe_dep_model",
        default="stanza/swe/dep/sv_talbanken_parser.pt",
        description="Stanza dependency model for Swedish",
        datatype=str,
    ),
    Config(
        "stanza.swe_pretrain_dep_model",
        default="stanza/swe/sv_talbanken.pretrain.pt",
        description="Stanza pretrain dependency model for Swedish",
        datatype=str,
    ),
]
