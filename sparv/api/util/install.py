"""Util functions for installations on remote servers."""

import os
import subprocess
from glob import glob

from sparv.api import get_logger
from sparv.api.util import system

logger = get_logger(__name__)


def install_file(local_file, host=None, remote_file=None):
    """Rsync a file to a target host."""
    system.rsync(local_file, host, remote_file)


def install_directory(host, directory):
    """Rsync every file from local directory to target host.

    Target path is extracted from filenames by replacing "#" with "/".
    """
    for local in glob(os.path.join(directory, '*')):
        remote = os.path.basename(local).replace("#", "/")
        system.rsync(local, host, remote)


def install_mysql(host, db_name, sqlfile):
    """Insert tables and data from local SQL-file to remote MySQL database.

    sqlfile may be a whitespace separated list of SQL files.
    """
    if not host:
        raise Exception("No host provided! Installations aborted.")

    sqlfiles = sqlfile.split()
    file_count = 0
    file_total = len(sqlfiles)

    for sqlf in sqlfiles:
        file_count += 1
        if not os.path.exists(sqlf):
            logger.error("Missing SQL file: %s", sqlf)
        elif os.path.getsize(sqlf) < 10:
            logger.info("Skipping empty file: %s (%d/%d)", sqlf, file_count, file_total)
        else:
            logger.info("Installing MySQL database: %s, source: %s (%d/%d)", db_name, sqlf, file_count, file_total)
            subprocess.check_call('cat %s | ssh %s "mysql %s"' % (sqlf, host, db_name), shell=True)


def install_mysql_dump(host, db_name, tables):
    """Copy selected tables (including data) from local to remote MySQL database."""
    if isinstance(tables, str):
        tables = tables.split()
    logger.info("Copying MySQL database: %s, tables: %s", db_name, ", ".join(tables))
    subprocess.check_call('mysqldump %s %s | ssh %s "mysql %s"' %
                          (db_name, " ".join(tables), host, db_name), shell=True)
