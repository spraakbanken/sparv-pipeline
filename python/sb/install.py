
from glob import glob
import os
import subprocess
import util

CWB_DATADIR = os.environ.get('CWB_DATADIR')
CORPUS_REGISTRY = os.environ.get('CORPUS_REGISTRY')

def install_corpus(host, master, datadir=CWB_DATADIR, registry=CORPUS_REGISTRY, target_datadir=None, target_registry=None):
    """
    Install CWB datafiles on server, by rsyncing datadir and registry.
    """
    target = os.path.join(target_datadir, master) if target_datadir else None
    util.system.rsync(os.path.join(datadir, master), host, target)
    util.system.rsync(os.path.join(registry, master), host, target_registry)

def install_directory(host, directory):
    """
    Rsyncs every file from local directory to target host. Target path is extracted from
    filenames by replacing "#" with "/".
    """
    for local in glob(os.path.join(directory, '*')):
        remote = os.path.basename(local).replace("#", "/")
        util.system.rsync(local, host, remote)

def install_mysql(host, db_name, tables):
    """
    Copies selected tables (including data) from local to remote MySQL database.
    """
    if isinstance(tables, basestring):
        tables = tables.split()
    util.log.info("Copying MySQL database: %s, tables: %s", db_name, ", ".join(tables))
    subprocess.check_call('mysqldump %s %s | ssh %s "mysql %s"' %
                          (db_name, " ".join(tables), host, db_name), shell=True)

if __name__ == '__main__':
    util.run.main(corpus=install_corpus,
                  dir=install_directory,
                  mysql=install_mysql)
