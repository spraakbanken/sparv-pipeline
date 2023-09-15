"""Korp-related annotators, exporters and installers."""
from typing import List

from sparv.api import Config
from . import config, lemgram_index, wordpicture, timespan

__config__ = [
    Config("korp.remote_host", description="Remote host to install to. Leave blank to install locally.", datatype=str),
    Config("korp.mysql_dbname", description="Name of database where Korp data will be stored", datatype=str),
    Config(
        "korp.modes",
        default=[{"name": "default"}],
        description="The Korp modes in which the corpus will be published",
        datatype=List[dict],
    ),
    Config(
        "korp.protected",
        default=False,
        description="Whether this corpus should have limited access or not",
        datatype=bool,
    ),
    Config(
        "korp.config_dir",
        description="Path on remote host where Korp corpus configuration files are stored",
        datatype=str,
    ),
    Config(
        "korp.wordpicture_table",
        default="relations",
        description="Prefix used for Word Picture database table names",
        datatype=str,
    ),
]
