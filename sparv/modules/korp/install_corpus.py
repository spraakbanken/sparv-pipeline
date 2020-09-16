"""Module for installing Korp-related corpus files on remote host."""

import logging
import os
import re

import sparv.util as util
from sparv import Config, Corpus, ExportInput, OutputCommonData, installer

log = logging.getLogger(__name__)


@installer("Install CWB datafiles on remote host", config=[
    Config("korp.remote_host", "", description="Remote host to install CWB datafiles to"),
    Config("korp.remote_corpus_registry", "", description="CWB registry path on remote host"),
    Config("korp.remote_cwb_datadir", "", description="CWB datadir path on remote host"),
    Config("korp.protected", False, description="Whether this corpus should have limited access or not")
])
def install_corpus(corpus: Corpus = Corpus(),
                   info_file: ExportInput = ExportInput("[cwb.cwb_datadir]/[metadata.id]/.info", absolute_path=True),
                   cwb_file: ExportInput = ExportInput("[cwb.corpus_registry]/[metadata.id]", absolute_path=True),
                   out: OutputCommonData = OutputCommonData("korp.time_install_corpus"),
                   host: str = Config("korp.remote_host"),
                   datadir: str = Config("cwb.cwb_datadir"),
                   registry: str = Config("cwb.corpus_registry"),
                   target_datadir: str = Config("korp.remote_cwb_datadir"),
                   target_registry: str = Config("korp.remote_corpus_registry")):
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
    source_registry_file = os.path.join(registry, corpus + ".tmp") if target_registry else os.path.join(registry,
                                                                                                        corpus)

    if target_registry:
        # Fix absolute paths in registry file
        with open(os.path.join(registry, corpus)) as registry_in:
            with open(os.path.join(registry, corpus + ".tmp"), "w") as registry_out:
                for line in registry_in:
                    if line.startswith("HOME"):
                        line = re.sub(r"HOME .*(/.+)", r"HOME " + target_datadir + r"\1", line)
                    elif line.startswith("INFO"):
                        line = re.sub(r"INFO .*(/.+)/\.info", r"INFO " + target_datadir + r"\1/.info", line)

                    registry_out.write(line)

    util.system.rsync(source_registry_file, host, target_registry_file)
    if target_registry:
        os.remove(os.path.join(registry, corpus + ".tmp"))

    # Write timestamp file
    out.write("")
