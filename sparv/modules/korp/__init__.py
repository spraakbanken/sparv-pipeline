"""Korp-related annotators, exporters and installers."""

from sparv import Config
from . import install_corpus, lemgram_index, relations, timespan

__config__ = [
    Config("korp.remote_host", description="Remote host to install to"),
    Config("korp.mysql_dbname", description="Name of database where Korp data will be stored"),
    Config("korp.mode", default="modern", description="The Korp mode in which the corpus will be published")
]
