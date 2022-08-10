"""Module for installing cwb binary files on remote host."""

import os
from typing import Optional

from sparv.api import Config, Corpus, ExportInput, OutputCommonData, SparvErrorMessage, installer, util


@installer("Install CWB datafiles on remote host")
def install_corpus(
        corpus: Corpus = Corpus(),
        out: OutputCommonData = OutputCommonData("cwb.install_corpus_marker"),
        host: Optional[str] = Config("cwb.remote_host"),
        registry_file: ExportInput = ExportInput("cwb.encoded/registry/[metadata.id]"),
        info_file: ExportInput = ExportInput("cwb.encoded/data/.info"),
        target_data_dir: str = Config("cwb.remote_data_dir"),
        target_registry_dir: str = Config("cwb.remote_registry_dir"),
        # The remaining arguments are needed by Snakemake
        _marker: ExportInput = ExportInput("cwb.encoded/data/.marker")):
    """Install CWB datafiles on server, by rsyncing datadir and registry."""
    sync_cwb(corpus=corpus, out=out, host=host, info_file=info_file, registry_file=registry_file,
             target_data_dir=target_data_dir, target_registry_dir=target_registry_dir)


@installer("Install CWB datafiles for a scrambled corpus on remote host")
def install_corpus_scrambled(
        corpus: Corpus = Corpus(),
        out: OutputCommonData = OutputCommonData("cwb.install_corpus_scrambled_marker"),
        host: Optional[str] = Config("cwb.remote_host"),
        registry_file: ExportInput = ExportInput("cwb.encoded_scrambled/registry/[metadata.id]"),
        info_file: ExportInput = ExportInput("cwb.encoded_scrambled/data/.info"),
        target_data_dir: str = Config("cwb.remote_data_dir"),
        target_registry_dir: str = Config("cwb.remote_registry_dir"),
        # The remaining arguments are needed by Snakemake
        _scrambled_marker: ExportInput = ExportInput("cwb.encoded_scrambled/data/.scrambled_marker")):
    """Install scrambled CWB datafiles on server, by rsyncing datadir and registry."""
    sync_cwb(corpus=corpus, out=out, host=host, info_file=info_file, registry_file=registry_file,
             target_data_dir=target_data_dir, target_registry_dir=target_registry_dir)


def sync_cwb(corpus, out, host, info_file, registry_file, target_data_dir, target_registry_dir):
    """Install CWB datafiles on server, by rsyncing CWB datadir and registry."""
    if not corpus:
        raise SparvErrorMessage("Missing corpus name. Corpus not installed.")

    if not target_data_dir:
        raise SparvErrorMessage("Configuration variable cwb.remote_data_dir not set! Corpus not installed.")

    if not target_registry_dir:
        raise SparvErrorMessage("Configuration variable cwb.remote_registry_dir not set! Corpus not installed.")

    source_data_dir = os.path.dirname(info_file)
    source_registry_dir = os.path.dirname(registry_file)

    target = os.path.join(target_data_dir, corpus)
    util.system.rsync(source_data_dir, host, target)

    target_registry_file = os.path.join(target_registry_dir, corpus)
    source_registry_file = os.path.join(source_registry_dir, corpus + ".tmp")

    # Fix absolute paths in registry file
    with open(registry_file, encoding="utf-8") as registry_in:
        with open(source_registry_file, "w", encoding="utf-8") as registry_out:
            for line in registry_in:
                if line.startswith("HOME"):
                    line = f"HOME {target_data_dir}/{corpus}\n"
                elif line.startswith("INFO"):
                    line = f"INFO {target_data_dir}/{corpus}/.info\n"

                registry_out.write(line)

    util.system.rsync(source_registry_file, host, target_registry_file)
    os.remove(source_registry_file)

    # Write marker file
    out.write("")
