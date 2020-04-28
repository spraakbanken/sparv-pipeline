"""Module for installing Korp-related corpus files on remote host."""

import logging
import os
import re

import sparv.util as util
from sparv import Config, Corpus, ExportInput, Output, installer
from sparv.core import paths

log = logging.getLogger(__name__)


@installer("Install CWB datafiles on remote host")
def install_corpus(corpus: str = Corpus,
                   info_file: str = ExportInput("[cwb.cwb_datadir]/[id]/.info", absolute_path=True),
                   cwb_file: str = ExportInput("[cwb.corpus_registry]/[id]", absolute_path=True),
                   out: str = Output("korp.time_install_corpus", data=True, common=True),
                   host: str = Config("remote_host", ""),
                   datadir: str = Config("cwb.cwb_datadir"),
                   registry: str = Config("cwb.corpus_registry"),
                   target_datadir: str = Config("remote_cwb_datadir", ""),
                   target_registry: str = Config("remote_corpus_registry", "")):
    """Install CWB datafiles on server, by rsyncing datadir and registry.

    If local and remote paths differ, target_datadir and target_registry must be specified.
    """
    if not corpus:
        raise(Exception("Missing corpus name. Corpus not installed."))

    if not host:
        raise(Exception("No host provided! Corpus not installed."))

    target = os.path.join(target_datadir, corpus) if target_datadir else None
    util.system.rsync(os.path.join(datadir, corpus), host, target)

    target_registry_file = os.path.join(target_registry, corpus) if target_registry else os.path.join(registry, corpus)
    source_registry_file = os.path.join(registry, corpus + ".tmp") if target_registry else os.path.join(registry, corpus)

    if target_registry:
        # Fix absolute paths in registry file
        with open(os.path.join(registry, corpus), "r") as registry_in:
            with open(os.path.join(registry, corpus + ".tmp"), "w") as registry_out:
                for line in registry_in:
                    if line.startswith("HOME"):
                        line = re.sub(r"HOME .*(\/.+)", r"HOME " + target_datadir + r"\1", line)
                    elif line.startswith("INFO"):
                        line = re.sub(r"INFO .*(\/.+)\/\.info", r"INFO " + target_datadir + r"\1/.info", line)

                    registry_out.write(line)

    util.system.rsync(source_registry_file, host, target_registry_file)
    if target_registry:
        os.remove(os.path.join(registry, corpus + ".tmp"))

    # Write timestamp file
    util.write_common_data(out, "")
