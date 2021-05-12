"""Annotations for historical Swedish texts."""

from sparv import Config

from . import diapivot, hist, models

__config__ = [
    Config("hist.dalin_model", default="hist/dalin.pickle", description="Path to Dalin model"),
    Config("hist.swedberg_model", default="hist/swedberg.pickle", description="Path to Swedberg model"),
    Config("hist.fsv_model", default="hist/fsvm.pickle", description="Path to model for fornsvenska morphology"),
    Config("hist.fsv_spelling", default="hist/fsv-spelling-variants.txt",
           description="Path to model for fornsvenska spelling variants"),
    Config("hist.delimiter", default="|", description="Character to put between ambiguous results"),
    Config("hist.affix", default="|", description="Character to put before and after sets of results"),
    Config("hist.extralemgrams", default="", description="Additional lemgram annotation")
]


    # Config("hist.delimiter", default=util.DELIM, description="Character to put between ambiguous results"),
    # Config("hist.affix", default=util.AFFIX, description="Character to put before and after sets of results"),
