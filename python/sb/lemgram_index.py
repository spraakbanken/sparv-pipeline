# -*- coding: utf-8 -*-

import os, subprocess
import util
from util.mysql_wrapper import MySQL

# Path to the cwb-scan-corpus binary
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")

def make_index(corpus, out, db_name, attributes=["lex", "prefix", "suffix"]):
    
    corpus = corpus.upper()
    index = count_lemgrams(corpus, attributes)
    
    mysql = MySQL(db_name, encoding=util.UTF8, output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_INDEX)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus})
    mysql.set_names()
    
    rows = []
    for lemgram, freq in index.items():
        row = {"lemgram": lemgram,
               "freq": freq[0],
               "freq_prefix": freq[1],
               "freq_suffix": freq[2],
               "corpus": corpus
               }
        rows.append(row)

    util.log.info("Creating SQL")
    mysql.add_row(MYSQL_TABLE, rows)


def count_lemgrams(corpus, attributes):
    
    util.log.info("Reading corpus")
    result = {}
    process = subprocess.Popen([CWB_SCAN_EXECUTABLE, "-r", CORPUS_REGISTRY, corpus] + attributes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    reply, error = process.communicate()
    if error and "Error:" in error: # We always get something back on stderror from cwb-scan-corpus, so we must check if it really is an error
        print error
        raise Exception
    for line in reply.splitlines():
        line = line.decode("UTF-8")
        if not line:
            continue
        temp = line.split("\t")
        freq = int(temp[0])
        for i in range(len(temp) - 1):
            for value in temp[i+1].split("|"):
                if value and not ":" in value:
                    result.setdefault(value, [0, 0, 0])
                    result[value][i] += freq
    
    return result

################################################################################

MYSQL_TABLE = "lemgram_index"

MYSQL_INDEX = {'columns': [("lemgram", "varchar(64)", "", "NOT NULL"),
                           ("freq", int, None, ""),
                           ("freq_prefix", int, None, ""),
                           ("freq_suffix", int, None, ""),
                           ("corpus", "varchar(64)", "", "NOT NULL")],
               'indexes': ["lemgram",
                           "corpus"
                           ],
               'default charset': 'utf8',
               }

################################################################################

if __name__ == '__main__':
    util.run.main(make_index)
