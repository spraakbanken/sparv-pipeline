"""`sparv.api.util.install` provides functions for installing and uninstalling corpora, either locally or remotely."""

from __future__ import annotations

import shlex
import subprocess
from collections.abc import Iterable
from pathlib import Path

from sparv.api import SparvErrorMessage, get_logger
from sparv.api.util import system

logger = get_logger(__name__)

EMPTY_FILE_LIMIT = 10  # Minimum file size (in bytes) to be considered non-empty


def install_path(source_path: str | Path, host: str | None, target_path: str | Path) -> None:
    """Transfer a file or the contents of a directory to a target destination, optionally on a different host.

    Args:
        source_path: Path to the local file or directory to sync. If a directory is specified, its contents are synced,
            not the directory itself, and any extraneous files in destination directories are deleted.
        host: Remote host to install to. Set to `None` to install locally.
        target_path: Path to the target file or directory.
    """
    system.rsync(source_path, host, target_path)


def uninstall_path(path: str | Path, host: str | None = None) -> None:
    """Remove a file or directory, optionally on a different host.

    Args:
        path: Path to the file or directory to remove.
        host: Remote host where the file or directory is located. Set to `None` to remove locally.
    """
    system.remove_path(path, host)


def install_mysql(host: str | None, db_name: str, sqlfile: Path | str | list[Path | str]) -> None:
    """Insert tables and data from one or more SQL files into a local or remote MySQL database.

    Args:
        host: The remote host to install to. Set to `None` to install locally.
        db_name: The name of the database.
        sqlfile: The path to a SQL file, or a list of paths to multiple SQL files.
    """
    if isinstance(sqlfile, (str, Path)):
        sqlfile = [sqlfile]
    sqlfile = [Path(f) for f in sqlfile]
    file_total = len(sqlfile)

    for file_count, f in enumerate(sqlfile):
        if not f.exists():
            logger.error("Missing SQL file: %s", f)
        elif f.stat().st_size < EMPTY_FILE_LIMIT:
            logger.info("Skipping empty file: %s (%d/%d)", f, file_count + 1, file_total)
        else:
            logger.info("Installing MySQL database: %s, source: %s (%d/%d)", db_name, f, file_count + 1, file_total)
            if not host:
                subprocess.check_call(f"cat {shlex.quote(str(f))} | mysql {shlex.quote(db_name)}", shell=True)
            else:
                subprocess.check_call(
                    f"cat {shlex.quote(str(f))} | ssh {shlex.quote(host)} {shlex.quote(f'mysql {db_name}')}", shell=True
                )


def install_mysql_dump(host: str, db_name: str, tables: str | Iterable[str]) -> None:
    """Copy selected tables, including their data, from a local MySQL database to a remote one.

    Args:
        host: The remote host to install to.
        db_name: The name of the remote database.
        tables: A table name or a list of table names. If a list is provided, the tables are separated by spaces.
    """
    if isinstance(tables, str):
        tables = tables.split()
    logger.info("Copying MySQL database: %s, tables: %s", db_name, ", ".join(tables))
    subprocess.check_call(f'mysqldump {db_name} {" ".join(tables)} | ssh {host} "mysql {db_name}"', shell=True)


def install_svn(source_file: str | Path, svn_url: str, remove_existing: bool = False) -> None:
    """Check in a file to an SVN repository.

    If the file is already in the repository, it will be deleted and added again.

    Args:
        source_file: The file to check in.
        svn_url: The URL to the SVN repository, including the path to the file.
        remove_existing: If False, this function can only be used to add new files to the repository. If True, existing
            files will be deleted before the import.

    Raises:
        SparvErrorMessage: If the source_file does not exist, if svn_url is not set, if it is not possible to list or
            delete the file in the SVN repository, if remove_existing is set to False and source_file already exists in
            the repository, or if it is not possible to import the file to the SVN repository.
    """
    # Check if source file exists
    source_file = Path(source_file)
    if not source_file.exists():
        raise SparvErrorMessage(
            f"Source file does not exist: {source_file}", module="api.util.install", function="install_svn"
        )

    # Check if svn_url is set
    if not svn_url:
        raise SparvErrorMessage("No SVN URL specified", module="api.util.install", function="install_svn")

    svn_url = svn_url.removeprefix("svn+")

    # Check if file exists in SVN repository and delete it (existing files cannot be updated in SVN)
    try:
        returncode = system.call_svn("ls", svn_url)
        if returncode == 0:
            if remove_existing is False:
                raise SparvErrorMessage(
                    f"File already exists in SVN repository: {svn_url}",
                    module="api.util.install",
                    function="install_svn",
                )
            logger.info("File exists in SVN repository, updating: %s", svn_url)
            system.call_svn("delete", svn_url)
    except FileNotFoundError:
        logger.info("File does not exist in SVN repository, adding: %s", svn_url)

    # Import file to SVN
    system.call_svn("import", str(source_file), svn_url)


def uninstall_svn(svn_url: str) -> None:
    """Delete a file from an SVN repository.

    Args:
        svn_url: The URL to the SVN repository including the name of the file to remove.

    Raises:
        SparvErrorMessage: If svn_url is not set, or if deletion fails.
    """
    # Check if svn_url is set
    if not svn_url:
        raise SparvErrorMessage("No SVN URL specified", module="api.util.install", function="uninstall_svn")

    svn_url = svn_url.removeprefix("svn+")

    # Delete file from SVN
    system.call_svn("delete", svn_url)


def install_git(source_file: str | Path, repo_path: str | Path, commit_message: str | None = None) -> None:
    """Copy a file to a local Git repository and make a commit.

    Args:
        source_file: The file to copy.
        repo_path: The path to the local Git repository.
        commit_message: The commit message. If not set, a default message will be used.

    Raises:
        SparvErrorMessage: If the source file does not exist, if repo_path is not set, or if it is not possible to add
            the file to the Git repository.
    """
    source_file = Path(source_file)
    repo_path = Path(repo_path)

    # Check if source file and repo path exist
    if not source_file.exists():
        raise SparvErrorMessage(
            f"Source file does not exist: {source_file}", module="api.util.install", function="install_git"
        )
    if not repo_path.exists():
        raise SparvErrorMessage(
            "Local Git repository path does not exist", module="api.util.install", function="install_git"
        )

    # Copy the file to the local Git repository
    target_file = repo_path / source_file.name
    target_file.write_bytes(source_file.read_bytes())

    # Add file to Git and commit
    try:
        logger.info("Adding file to local Git repository: %s", repo_path)
        add = subprocess.run(["git", "-C", str(repo_path), "add", str(target_file)], check=True, capture_output=True)
        if add.stderr:
            logger.warning("Command 'git add' generated the following output on stderr: %s", add.stderr.decode())

        message = commit_message or f"Add {source_file.name!r} with Sparv"
        commit = subprocess.run(["git", "-C", str(repo_path), "commit", "-m", message], check=True, capture_output=True)
        if commit.stderr:
            logger.warning("Command 'git commit' generated the following output on stderr: %s", commit.stderr.decode())
    except subprocess.CalledProcessError as e:
        raise SparvErrorMessage(
            f"Failed to add file to local Git repository: {e}", module="api.util.install", function="install_git"
        ) from e


def uninstall_git(file_path: str | Path, commit_message: str | None = None) -> None:
    """Remove a file from a local Git repository and make a commit.

    Args:
        file_path: The path to file to remove.
        commit_message: The commit message. If not set, a default message will be used.

    Raises:
        SparvErrorMessage: If repo_path is not set, if the file does not exist in the Git repository, or if it is not
            possible to remove the file from the Git repository.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise SparvErrorMessage(
            f"File does not exist in Git repository: {file_path}", module="api.util.install", function="uninstall_git"
        )

    # Remove file from Git and commit
    try:
        logger.info("Removing file from local Git repository: %s", file_path)
        rm = subprocess.check_call(["git", "-C", str(file_path.parent), "rm", str(file_path.name)])
        if rm.stderr:
            logger.warning("Command 'git rm' generated the following output on stderr: %s", rm.stderr.decode())
        message = commit_message or "Remove {source_file.name!r} with Sparv"
        commit = subprocess.check_call(["git", "-C", str(file_path.parent), "commit", "-m", message])
        if commit.stderr:
            logger.warning("Command 'git commit' generated the following output on stderr: %s", commit.stderr.decode())
    except subprocess.CalledProcessError as e:
        raise SparvErrorMessage(
            f"Failed to remove file from local Git repository: {e}", module="api.util.install", function="uninstall_git"
        ) from e
