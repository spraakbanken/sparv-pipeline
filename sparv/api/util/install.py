"""Util functions for installations on remote servers."""

import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Union, List

from sparv.api import get_logger
from sparv.api.util import system

logger = get_logger(__name__)


def install_path(
    source_path: Union[str, Path],
    host: Optional[str],
    target_path: Union[str, Path]
) -> None:
    """Transfer a file or the contents of a directory to a target destination, optionally on a different host."""
    system.rsync(source_path, host, target_path)


def uninstall_path(path: Union[str, Path], host: Optional[str] = None) -> None:
    """Remove a file or directory, optionally on a remote host."""
    system.remove_path(path, host)


def install_mysql(host: Optional[str], db_name: str, sqlfile: Union[str, List[str]]):
    """Insert tables and data from SQL-file(s) to local or remote MySQL database.

    Args:
        host: The remote host to install to. Set to None to install locally.
        db_name: Name of the database.
        sqlfile: Path to a SQL file, or list of paths.
    """

    if isinstance(sqlfile, str):
        sqlfile = [sqlfile]
    file_count = 0
    file_total = len(sqlfile)

    for f in sqlfile:
        file_count += 1
        if not os.path.exists(f):
            logger.error("Missing SQL file: %s", f)
        elif os.path.getsize(f) < 10:
            logger.info("Skipping empty file: %s (%d/%d)", f, file_count, file_total)
        else:
            logger.info(f"Installing MySQL database: {db_name}, source: {f} ({file_count}/{file_total})")
            if not host:
                subprocess.check_call(
                    f"cat {shlex.quote(f)} | mysql {shlex.quote(db_name)}", shell=True
                )
            else:
                subprocess.check_call(
                    f"cat {shlex.quote(f)} | ssh {shlex.quote(host)} {shlex.quote(f'mysql {db_name}')}", shell=True
                )


def install_mysql_dump(host, db_name, tables):
    """Copy selected tables (including data) from local to remote MySQL database."""
    if isinstance(tables, str):
        tables = tables.split()
    logger.info("Copying MySQL database: %s, tables: %s", db_name, ", ".join(tables))
    subprocess.check_call('mysqldump %s %s | ssh %s "mysql %s"' %
                          (db_name, " ".join(tables), host, db_name), shell=True)
