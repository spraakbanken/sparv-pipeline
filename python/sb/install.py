
from glob import glob
import os
import subprocess
import util
import re

CWB_DATADIR = os.environ.get('CWB_DATADIR')
CORPUS_REGISTRY = os.environ.get('CORPUS_REGISTRY')

def install_corpus(host, master, datadir=CWB_DATADIR, registry=CORPUS_REGISTRY, target_datadir=None, target_registry=None):
    """
    Install CWB datafiles on server, by rsyncing datadir and registry.
    If local and remote paths differ, target_datadir and target_registry must be specified.
    """
    if not master:
        util.log.error("Missing master. Corpus not installed.")
    else:
        target = os.path.join(target_datadir, master) if target_datadir else None
        util.system.rsync(os.path.join(datadir, master), host, target)
        
        target_registry_file = os.path.join(target_registry, master) if target_registry else os.path.join(registry, master)
        source_registry_file = os.path.join(registry, master + ".tmp") if target_registry else os.path.join(registry, master)
        
        if target_registry:
            # Fix absolute paths in registry file
            with open(os.path.join(registry, master), "r") as registry_in:
                with open(os.path.join(registry, master + ".tmp"), "w") as registry_out:
                    for line in registry_in:
                        if line.startswith("HOME"):
                            line = re.sub(r"HOME .*(\/.+)", r"HOME " + target_datadir + r"\1", line)
                        elif line.startswith("INFO"):
                            line = re.sub(r"INFO .*(\/.+)\/\.info", r"INFO " + target_datadir + r"\1/.info", line)
                        
                        registry_out.write(line)
        
        util.system.rsync(source_registry_file, host, target_registry_file)
        if target_registry:
            os.remove(os.path.join(registry, master + ".tmp"))

def install_directory(host, directory):
    """
    Rsyncs every file from local directory to target host. Target path is extracted from
    filenames by replacing "#" with "/".
    """
    for local in glob(os.path.join(directory, '*')):
        remote = os.path.basename(local).replace("#", "/")
        util.system.rsync(local, host, remote)

def install_mysql(host, db_name, sqlfile):
    """
    Inserts tables and data from local SQL-file to remote MySQL database.
    sqlfile may be a whitespace separated list of SQL-files.
    """
    
    sqlfiles = sqlfile.split()
    
    for sqlf in sqlfiles:
        if not os.path.exists(sqlf):
            util.log.error("Missing SQL file:", sqlf)
        else:
            util.log.info("Installing MySQL database: %s, source: %s", db_name, sqlf)
            subprocess.check_call('cat %s | ssh %s "mysql %s"' %
                                (sqlf, host, db_name), shell=True)

def install_mysql_dump(host, db_name, tables):
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
