import os
import subprocess
import sparv.util as util
from sparv.util.mysql_wrapper import MySQL

# Path to the cwb-scan-corpus binary
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


def make_index(corpus, out, db_name, attributes=["lex", "prefix", "suffix"]):
    """Create lemgram index SQL file."""
    attributes = util.split(attributes)
    attribute_fields = {"lex": "freq", "prefix": "freq_prefix", "suffix": "freq_suffix"}

    corpus = corpus.upper()
    index = count_lemgrams(corpus, attributes)

    mysql = MySQL(db_name, encoding=util.UTF8, output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_INDEX)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus})
    mysql.set_names()

    rows = []
    for lemgram, freq in list(index.items()):
        row = {"lemgram": lemgram,
               "corpus": corpus
               }

        for i, attr in enumerate(attributes):
            row[attribute_fields[attr]] = freq[i]

        for attr in attribute_fields:
            if attr not in attributes:
                row[attribute_fields[attr]] = 0

        rows.append(row)

    util.log.info("Creating SQL")
    mysql.add_row(MYSQL_TABLE, rows)


def count_lemgrams(corpus, attributes):
    """Count lemgrams using cwb-scan."""
    util.log.info("Reading corpus")
    result = {}
    process = subprocess.Popen([CWB_SCAN_EXECUTABLE, "-q", "-r", CORPUS_REGISTRY, corpus] + attributes,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    reply, error = process.communicate()
    if error:
        print(error.decode())
        raise Exception
    for line in reply.decode("UTF-8").splitlines():
        if not line:
            continue
        temp = line.split("\t")
        freq = int(temp[0])
        for i in range(len(temp) - 1):
            for value in temp[i + 1].split("|"):
                if value and ":" not in value:
                    result.setdefault(value, [0] * len(attributes))
                    result[value][i] += freq

    return result


################################################################################

MYSQL_TABLE = "lemgram_index"

MYSQL_INDEX = {"columns": [("lemgram", "varchar(64)", "", "NOT NULL"),
                           ("freq", int, 0, "NOT NULL"),
                           ("freq_prefix", int, 0, "NOT NULL"),
                           ("freq_suffix", int, 0, "NOT NULL"),
                           ("corpus", "varchar(64)", "", "NOT NULL")],
               "indexes": ["lemgram corpus freq freq_prefix freq_suffix"],  # Can't make this primary due to collation
               "default charset": "utf8",
               }

################################################################################

if __name__ == "__main__":
    util.run.main(make_index)
