# -*- coding: utf-8 -*-

import subprocess, os
import util
from util.mysql_wrapper import MySQL

# Path to the cwb-scan-corpus binary
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")

def timespan(corpus, db_name, out):
    
    corpus = corpus.upper()
    rows = []
    process = subprocess.Popen([CWB_SCAN_EXECUTABLE, "-r", CORPUS_REGISTRY, corpus, "text_datefrom", "text_dateto"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    reply, error = process.communicate()
    if error and "Error:" in error: # We always get something back on stderror from cwb-scan-corpus, so we must check if it really is an error
        print error
        raise Exception
    for line in reply.splitlines():
        line = line.decode("UTF-8")
        if not line:
            continue
        line = line.split("\t")
        line[0] = int(line[0])
        
        row = {
               "corpus": corpus,
               "datefrom": line[1],
               "dateto": line[2],
               "tokens": int(line[0])
               }
        
        rows.append(row)
    
    mysql = MySQL(db_name, encoding=util.UTF8, output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_TIMESPAN)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus})
    mysql.set_names()
    
    util.log.info("Creating SQL")
    mysql.add_row(MYSQL_TABLE, rows)

################################################################################

MYSQL_TABLE = "timespans"

MYSQL_TIMESPAN = {'columns': [
                               ("corpus",   "varchar(64)", "", "NOT NULL"),
                               ("datefrom",  "char(14)", "", "NOT NULL"),
                               ("dateto",    "char(14)", "", "NOT NULL"),
                               ("tokens",   int, None, "")],
               'indexes': ["corpus"],
               'default charset': 'utf8'
               }


if __name__ == '__main__':
    util.run.main(timespan)