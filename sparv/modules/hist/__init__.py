"""Annotations for historical Swedish texts."""

from sparv.api import Config, util

from . import diapivot, hist, models

__config__ = [
    Config("hist.dalin_model", default="hist/dalin.pickle", description="Path to Dalin model"),
    Config("hist.swedberg_model", default="hist/swedberg.pickle", description="Path to Swedberg model"),
    Config("hist.fsv_model", default="hist/fsvm.pickle", description="Path to model for fornsvenska morphology"),
    Config("hist.fsv_spelling", default="hist/fsv-spelling-variants.txt",
           description="Path to model for fornsvenska spelling variants"),
    # Set max_mwe_gaps to 0 since many (most?) multi-word in the old lexicons are unseparable (half öre etc)
    Config("hist.max_mwe_gaps", default=0, description="Max amount of gaps allowed within a multiword expression"),
    Config("hist.delimiter", default=util.constants.DELIM, description="Character to put between ambiguous results"),
    Config("hist.affix", default=util.constants.AFFIX, description="Character to put before and after sets of results"),
    Config("hist.extralemgrams", default="", description="Additional lemgram annotation")
]
