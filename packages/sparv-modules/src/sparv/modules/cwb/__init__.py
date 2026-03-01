"""Exports, encodes and aligns corpora for Corpus Workbench."""

from sparv.api import Config

from . import cwb, info, install_corpus

__config__ = [
    Config("cwb.remote_host", description="Remote host to install CWB files to", datatype=str),
    Config("cwb.remote_registry_dir", description="CWB registry path on remote host", datatype=str),
    Config("cwb.remote_data_dir", description="CWB datadir path on remote host", datatype=str),
]
