"""Korp-related annotators, exporters and installers."""

from sparv.api import Config
from . import install_corpus, lemgram_index, relations, timespan

__config__ = [
    Config("korp.remote_host", description="Remote host to install to"),
    Config("korp.mysql_dbname", description="Name of database where Korp data will be stored"),
    Config("korp.modes", default=["default"], description="The Korp modes in which the corpus will be published")
]
