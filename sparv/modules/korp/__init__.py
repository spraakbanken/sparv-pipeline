"""Korp-related annotators, exporters and installers."""

from sparv.api import Config
from . import lemgram_index, relations, timespan

__config__ = [
    Config("korp.remote_host", description="Remote host to install to. Leave blank to install locally."),
    Config("korp.mysql_dbname", description="Name of database where Korp data will be stored"),
    Config("korp.modes", default=["default"], description="The Korp modes in which the corpus will be published"),
    Config("korp.protected", False, description="Whether this corpus should have limited access or not")
]
