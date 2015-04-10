# -*- coding: utf-8 -*-

import subprocess
import os
import util
from util.mysql_wrapper import MySQL

# Path to the cwb-scan-corpus binary
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"
CQP_EXECUTABLE = "cqp"
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


def timespan(corpus, db_name, out):
    
    corpus = corpus.upper()
    rows = []
    process = subprocess.Popen([CWB_SCAN_EXECUTABLE, "-r", CORPUS_REGISTRY, corpus, "text_datefrom", "text_timefrom", "text_dateto", "text_timeto"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    reply, error = process.communicate()
    if error and "Error:" in error:  # We always get something back on stderror from cwb-scan-corpus, so we must check if it really is an error
        if "Error: can't open attribute" in error and (".text_datefrom" in error or ".text_dateto" in error):
            util.log.info("No date information present in corpus.")
            # No date information in corpus. Calculate total token count instead.
            process = subprocess.Popen([CQP_EXECUTABLE, "-c", "-r", CORPUS_REGISTRY], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            reply, error = process.communicate("set PrettyPrint off;%s;info;" % corpus)
            
            if error:
                print error
                raise Exception

            for line in reply.splitlines():
                if line.startswith("Size: "):
                    reply = "%s\t\t\t\t" % line[6:].strip()
        else:
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
            "datefrom": (line[1] + line[2]).zfill(14) if (line[1] + line[2]) else "",  # Pad years < 1000 with zero
            "dateto": (line[3] + line[4]).zfill(14) if (line[3] + line[4]) else "",
            "tokens": int(line[0])
        }
        
        rows.append(row)
    
    util.log.info("Creating SQL")
    mysql = MySQL(db_name, encoding=util.UTF8, output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_TIMESPAN)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus})
    mysql.set_names()

    mysql.add_row(MYSQL_TABLE, rows)

################################################################################

MYSQL_TABLE = "timespans"

MYSQL_TIMESPAN = {'columns': [
                               ("corpus",   "varchar(64)", "", "NOT NULL"),
                               ("datefrom",  "char(14)", "", "NOT NULL"),
                               ("dateto",    "char(14)", "", "NOT NULL"),
                               ("tokens",   int, 0, "NOT NULL")],
                  'primary': "corpus datefrom dateto tokens",
                  'indexes': [],
                  'default charset': 'utf8'
                  }


if __name__ == '__main__':
    util.run.main(timespan)
