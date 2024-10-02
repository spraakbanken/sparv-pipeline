"""Module for installing cwb binary files on remote host."""

import os
from pathlib import Path
from typing import Optional

from sparv.api import (
    Config,
    Corpus,
    ExportInput,
    MarkerOptional,
    OutputMarker,
    SparvErrorMessage,
    get_logger,
    installer,
    uninstaller,
    util,
)

logger = get_logger(__name__)


@installer("Install CWB datafiles", uninstaller="cwb:uninstall_corpus")
def install_corpus(
        corpus: Corpus = Corpus(),
        marker: OutputMarker = OutputMarker("cwb.install_corpus_marker"),
        uninstall_marker: MarkerOptional = MarkerOptional("cwb.uninstall_corpus_marker"),
        host: Optional[str] = Config("cwb.remote_host"),
        registry_file: ExportInput = ExportInput("cwb.encoded/registry/[metadata.id]"),
        info_file: ExportInput = ExportInput("cwb.encoded/data/.info"),
        target_data_dir: str = Config("cwb.remote_data_dir"),
        target_registry_dir: str = Config("cwb.remote_registry_dir"),
        # The remaining arguments are needed by Snakemake
        _marker: ExportInput = ExportInput("cwb.encoded/data/.marker")):
    """Install CWB datafiles, by rsyncing datadir and registry."""
    sync_cwb(corpus=corpus, marker=marker, host=host, info_file=info_file, registry_file=registry_file,
             target_data_dir=target_data_dir, target_registry_dir=target_registry_dir)
    uninstall_marker.remove()


@installer("Install CWB datafiles for a scrambled corpus", uninstaller="cwb:uninstall_corpus")
def install_corpus_scrambled(
        corpus: Corpus = Corpus(),
        marker: OutputMarker = OutputMarker("cwb.install_corpus_scrambled_marker"),
        uninstall_marker: MarkerOptional = MarkerOptional("cwb.uninstall_corpus_marker"),
        host: Optional[str] = Config("cwb.remote_host"),
        registry_file: ExportInput = ExportInput("cwb.encoded_scrambled/registry/[metadata.id]"),
        info_file: ExportInput = ExportInput("cwb.encoded_scrambled/data/.info"),
        target_data_dir: str = Config("cwb.remote_data_dir"),
        target_registry_dir: str = Config("cwb.remote_registry_dir"),
        # The remaining arguments are needed by Snakemake
        _scrambled_marker: ExportInput = ExportInput("cwb.encoded_scrambled/data/.scrambled_marker")):
    """Install scrambled CWB datafiles, by rsyncing datadir and registry."""
    sync_cwb(corpus=corpus, marker=marker, host=host, info_file=info_file, registry_file=registry_file,
             target_data_dir=target_data_dir, target_registry_dir=target_registry_dir)
    uninstall_marker.remove()


@uninstaller("Uninstall CWB datafiles")
def uninstall_corpus(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("cwb.uninstall_corpus_marker"),
    install_marker: MarkerOptional = MarkerOptional("cwb.install_corpus_marker"),
    install_scrambled_marker: MarkerOptional = MarkerOptional("cwb.install_corpus_scrambled_marker"),
    host: Optional[str] = Config("cwb.remote_host"),
    data_dir: str = Config("cwb.remote_data_dir"),
    registry_dir: str = Config("cwb.remote_registry_dir")
):
    """Uninstall CWB data."""
    assert corpus and data_dir and registry_dir  # Already checked by Sparv, but just to be sure

    registry_file = Path(registry_dir) / corpus
    logger.info("Removing CWB registry file from %s%s", host + ":" if host else "", registry_file)
    util.install.uninstall_path(registry_file, host=host)

    corpus_dir = Path(data_dir) / corpus
    logger.info("Removing CWB data from %s%s", host + ":" if host else "", corpus_dir)
    util.install.uninstall_path(corpus_dir, host=host)

    install_marker.remove()
    install_scrambled_marker.remove()
    marker.write()


def sync_cwb(corpus, marker, host, info_file, registry_file, target_data_dir, target_registry_dir):
    """Install CWB datafiles on server, by rsyncing CWB datadir and registry."""
    if not corpus:
        raise SparvErrorMessage("Missing corpus name. Corpus not installed.")

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
    marker.write()
