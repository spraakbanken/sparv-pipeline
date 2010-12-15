
from glob import glob
import os
import subprocess
import util

CWB_DATADIR = os.environ.get('CWB_DATADIR')
CORPUS_REGISTRY = os.environ.get('CORPUS_REGISTRY')

def install_corpus(host, master, datadir=CWB_DATADIR, registry=CORPUS_REGISTRY):
    util.system.rsync(os.path.join(datadir, master), host)
    util.system.rsync(os.path.join(registry, master), host)

def install_directory(host, directory):
    for local in glob(os.path.join(directory, '*')):
        remote = os.path.basename(local).replace("#", "/")
        util.system.rsync(local, host, remote)

def install_mysql(host, db_name, tables):
    if isinstance(tables, basestring):
        tables = tables.split()
    util.log.info("Copying MySQL database: %s, tables: %s", db_name, ", ".join(tables))
    subprocess.check_call('mysqldump %s %s | ssh %s "mysql %s"' %
                          (db_name, " ".join(tables), host, db_name), shell=True)

if __name__ == '__main__':
    util.run.main(corpus=install_corpus,
                  dir=install_directory,
                  mysql=install_mysql)

