"""Part of Speech annotation using Hunpos."""

from sparv.api import Config, util

from . import hunpos, morphtable, morphtable_hist

__config__ = [
    Config("hunpos.binary", default="hunpos-tag", description="Hunpos executable"),
    Config("hunpos.encoding", default=util.constants.UTF8, description="Encoding of the input text"),

    # Config for modern Swedish
    Config("hunpos.model", default="hunpos/suc3_suc-tags_default-setting_utf8.model",
           description="Path to Hunpos model"),
    Config("hunpos.morphtable", default="hunpos/saldo_suc-tags.morphtable",
           description="Path to optional Hunpos morphtable file"),
    Config("hunpos.patterns", default="hunpos/suc.patterns", description="Path to optional patterns file"),
    Config("hunpos.tag_mapping", default=None, description="Optional tag mapping for translating the output tags"),

    # Config for swe-1800
    Config("hunpos.model_hist", default="hunpos/suc3_suc-tags_default-setting_utf8.model",
           description="Path to Hunpos model (older Swedish)"),
    Config("hunpos.morphtable_hist", default="hunpos/hist/dalinm-swedberg_saldo_suc-tags.morphtable",
           description="Path to optional Hunpos morphtable file (older Swedish)"),
    Config("hunpos.tag_mapping_hist", default=None,
           description="Optional tag mapping for translating the output tags (older Swedish)")
]
