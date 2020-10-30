from sparv import Config
from . import install_corpus, lemgram_index, relations, timespan

__config__ = [
    Config("korp.remote_host", "", description="Remote host to install to")
]
