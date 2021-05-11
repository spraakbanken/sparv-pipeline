"""Annotations for historical Swedish texts."""

from sparv import Config

from . import diapivot, hist, models

__config__ = [
    Config("hist.dalin_model", default="hist/dalin.pickle", description="Path to Dalin model"),
    Config("hist.swedberg_model", default="hist/swedberg.pickle", description="Path to Swedberg model"),
    Config("hist.extralemgrams", default="", description="Additional lemgram annotation")
]
