"""Module for installing cwb binary files on remote host."""

from pathlib import Path

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
    host: str | None = Config("cwb.remote_host"),
    registry_file: ExportInput = ExportInput("cwb.encoded/registry/[metadata.id]"),
    info_file: ExportInput = ExportInput("cwb.encoded/data/.info"),
    target_data_dir: str = Config("cwb.remote_data_dir"),
    target_registry_dir: str = Config("cwb.remote_registry_dir"),
    # This argument is needed by Snakemake to trigger encoding of the corpus if needed
    _marker: ExportInput = ExportInput("cwb.encoded/data/.marker"),
) -> None:
    """Install CWB datafiles, by rsyncing datadir and registry.

    Args:
        corpus: The name of the corpus to install.
        marker: The install marker file to write after installation.
        uninstall_marker: The uninstall marker file to remove after installation.
        host: The remote host to install the corpus on.
        registry_file: The path to the CWB registry file.
        info_file: The path to the CWB info file.
        target_data_dir: The target directory for the CWB data files.
        target_registry_dir: The target directory for the CWB registry files.
        _marker: The marker file to create after installation.
    """
    sync_cwb(
        corpus=corpus,
        marker=marker,
        host=host,
        info_file=info_file,
        registry_file=registry_file,
        target_data_dir=target_data_dir,
        target_registry_dir=target_registry_dir,
    )
    uninstall_marker.remove()


@installer("Install CWB datafiles for a scrambled corpus", uninstaller="cwb:uninstall_corpus")
def install_corpus_scrambled(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("cwb.install_corpus_scrambled_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("cwb.uninstall_corpus_marker"),
    host: str | None = Config("cwb.remote_host"),
    registry_file: ExportInput = ExportInput("cwb.encoded_scrambled/registry/[metadata.id]"),
    info_file: ExportInput = ExportInput("cwb.encoded_scrambled/data/.info"),
    target_data_dir: str = Config("cwb.remote_data_dir"),
    target_registry_dir: str = Config("cwb.remote_registry_dir"),
    # This argument is needed by Snakemake to trigger encoding of the corpus if needed
    _scrambled_marker: ExportInput = ExportInput("cwb.encoded_scrambled/data/.scrambled_marker"),
) -> None:
    """Install scrambled CWB datafiles, by rsyncing datadir and registry.

    Args:
        corpus: The name of the corpus to install.
        marker: The install marker file to write after installation.
        uninstall_marker: The uninstall marker file to remove after installation.
        host: The remote host to install the corpus on.
        registry_file: The path to the CWB registry file.
        info_file: The path to the CWB info file.
        target_data_dir: The target directory for the CWB data files.
        target_registry_dir: The target directory for the CWB registry files.
        _scrambled_marker: The marker file to create after installation.
    """
    sync_cwb(
        corpus=corpus,
        marker=marker,
        host=host,
        info_file=info_file,
        registry_file=registry_file,
        target_data_dir=target_data_dir,
        target_registry_dir=target_registry_dir,
    )
    uninstall_marker.remove()


@uninstaller("Uninstall CWB datafiles")
def uninstall_corpus(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("cwb.uninstall_corpus_marker"),
    install_marker: MarkerOptional = MarkerOptional("cwb.install_corpus_marker"),
    install_scrambled_marker: MarkerOptional = MarkerOptional("cwb.install_corpus_scrambled_marker"),
    host: str | None = Config("cwb.remote_host"),
    data_dir: str = Config("cwb.remote_data_dir"),
    registry_dir: str = Config("cwb.remote_registry_dir"),
) -> None:
    """Uninstall CWB data.

    Args:
        corpus: The name of the corpus to uninstall.
        marker: The uninstall marker file to write after uninstallation.
        install_marker: The install marker file to remove after uninstallation.
        install_scrambled_marker: The install scrambled marker file to remove after uninstallation.
        host: The remote host to uninstall the corpus from.
        data_dir: The remote directory where the CWB data files are located.
        registry_dir: The remote directory where the CWB registry files are located.
    """
    assert corpus and data_dir and registry_dir  # Already checked by Sparv, but just to be sure; # noqa: PT018

    registry_file = Path(registry_dir) / corpus
    logger.info("Removing CWB registry file from %s%s", host + ":" if host else "", registry_file)
    util.install.uninstall_path(registry_file, host=host)

    corpus_dir = Path(data_dir) / corpus
    logger.info("Removing CWB data from %s%s", host + ":" if host else "", corpus_dir)
    util.install.uninstall_path(corpus_dir, host=host)

    install_marker.remove()
    install_scrambled_marker.remove()
    marker.write()


def sync_cwb(
    corpus: Corpus,
    marker: OutputMarker,
    host: str | None,
    info_file: ExportInput,
    registry_file: ExportInput,
    target_data_dir: str,
    target_registry_dir: str,
) -> None:
    """Install CWB datafiles on server, by rsyncing CWB datadir and registry.

    Args:
        corpus: The name of the corpus to install.
        marker: The install marker file to write after installation.
        host: The remote host to install the corpus on.
        info_file: The path to the CWB info file.
        registry_file: The path to the CWB registry file.
        target_data_dir: The target directory for the CWB data files.
        target_registry_dir: The target directory for the CWB registry files.

    Raises:
        SparvErrorMessage: If the corpus name is missing or if it is not installed.
    """
    if not corpus:
        raise SparvErrorMessage("Missing corpus name. Corpus not installed.")

    source_data_dir = Path(info_file).parent
    source_registry_dir = Path(registry_file).parent

    target = Path(target_data_dir, corpus)
    util.system.rsync(source_data_dir, host, target)

    target_registry_file = Path(target_registry_dir) / corpus
    source_registry_file = Path(source_registry_dir) / (corpus + ".tmp")

    # Fix absolute paths in registry file
    with (
        Path(registry_file).open(encoding="utf-8") as registry_in,
        source_registry_file.open("w", encoding="utf-8") as registry_out,
    ):
        for line in registry_in:
            if line.startswith("HOME"):
                line = f"HOME {target_data_dir}/{corpus}\n"  # noqa: PLW2901
            elif line.startswith("INFO"):
                line = f"INFO {target_data_dir}/{corpus}/.info\n"  # noqa: PLW2901

            registry_out.write(line)

    util.system.rsync(source_registry_file, host, target_registry_file)
    source_registry_file.unlink()

    # Write marker file
    marker.write()
