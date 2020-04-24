"""Module for installing Korp-related corpus files on remote host."""

import logging
import os
import re
import subprocess
from glob import glob

import sparv.util as util
from sparv import Config, Corpus, ExportInput, installer
from sparv.core import paths

log = logging.getLogger(__name__)


@installer("Install CWB datafiles on remote host")
def install_corpus(corpus: str = Corpus,
                   info_file: str = ExportInput("[cwb_datadir]/[id]/.info", absolute_path=True),
                   cwb_file: str = ExportInput("[corpus_registry]/[id]", absolute_path=True),
                   host: str = Config("remote_host", ""),
                   datadir: str = Config("cwb_datadir", paths.cwb_datadir),
                   registry: str = Config("corpus_registry", paths.corpus_registry),
                   target_datadir: str = Config("remote_cwb_datadir", ""),
                   target_registry: str = Config("remote_corpus_registry", "")):
    """Install CWB datafiles on server, by rsyncing datadir and registry.

    If local and remote paths differ, target_datadir and target_registry must be specified.
    """
    if not corpus:
        log.error("Missing corpus name. Corpus not installed.")
    else:
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


def install_file(host, local_file, remote_file):
    """Rsync a file to a target host."""
    util.system.rsync(local_file, host, remote_file)


def install_directory(host, directory):
    """Rsync every file from local directory to target host.

    Target path is extracted from filenames by replacing "#" with "/".
    """
    for local in glob(os.path.join(directory, '*')):
        remote = os.path.basename(local).replace("#", "/")
        util.system.rsync(local, host, remote)


def install_mysql(host, db_name, sqlfile):
    """Insert tables and data from local SQL-file to remote MySQL database.

    sqlfile may be a whitespace separated list of SQL-files.
    """
    sqlfiles = sqlfile.split()
    file_count = 0
    file_total = len(sqlfiles)

    for sqlf in sqlfiles:
        file_count += 1
        if not os.path.exists(sqlf):
            log.error("Missing SQL file: %s", sqlf)
        elif os.path.getsize(sqlf) < 10:
            log.info("Skipping empty file: %s (%d/%d)", sqlf, file_count, file_total)
        else:
            log.info("Installing MySQL database: %s, source: %s (%d/%d)", db_name, sqlf, file_count, file_total)
            subprocess.check_call('cat %s | ssh %s "mysql %s"' % (sqlf, host, db_name), shell=True)


def install_mysql_dump(host, db_name, tables):
    """Copy selected tables (including data) from local to remote MySQL database."""
    if isinstance(tables, str):
        tables = tables.split()
    log.info("Copying MySQL database: %s, tables: %s", db_name, ", ".join(tables))
    subprocess.check_call('mysqldump %s %s | ssh %s "mysql %s"' %
                          (db_name, " ".join(tables), host, db_name), shell=True)


if __name__ == '__main__':
    util.run.main(dir=install_directory,
                  file=install_file,
                  mysql=install_mysql)
