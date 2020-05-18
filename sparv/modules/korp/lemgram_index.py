"""Create files needed for the lemgram search in Korp."""

import logging
import subprocess

import sparv.util as util
from sparv import Annotation, Config, Corpus, Export, ExportInput, Output, exporter, installer
from sparv.core import paths
from sparv.util.mysql_wrapper import MySQL

log = logging.getLogger(__name__)

# Path to the cwb-scan-corpus binary
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"


# @installer("Install lemgram SQL on remote host")
def install_lemgrams(sqlfile: str = ExportInput("korp_lemgramindex/lemgram_index.sql"),
                     out: str = Output("korp.time_install_lemgram", data=True, common=True),
                     db_name: str = Config("korp.mysql_dbname", ""),
                     host: str = Config("korp.remote_host", "")):
    """Install lemgram SQL on remote host.

    Args:
        sqlfile (str, optional): SQL file to be installed.
            Defaults to ExportInput("korp_lemgramindex/lemgram_index.sql").
        out (str, optional): Timestamp file to be written.
            Defaults to Output("korp.time_install_lemgram", data=True, common=True).
        db_name (str, optional): Name of the data base. Defaults to Config("korp.mysql_dbname", "").
        host (str, optional): Remote host to install to. Defaults to Config("korp.remote_host", "").
    """
    util.install_mysql(host, db_name, sqlfile)
    util.write_common_data(out, "")


# TODO: Korp search for complemgram needs to be fixed before this can be re-written
# @exporter("Lemgram index SQL file for use in Korp")
def lemgram_sql(corpus: str = Corpus,
                out: str = Export("korp_lemgramindex/lemgram_index.sql"),
                lemgram: str = Annotation("<token>:saldo.lemgram", all_docs=True),
                complemgram: str = Annotation("<token>:saldo.complemgram", all_docs=True),
                db_name: str = Config("korp.lemgram_db_name", "korp_lemgram"),
                attributes: list = Config("lemgram_index_attributes", ["lemgram", "prefix", "suffix"]),  # ??
                corpus_registry: str = Config("corpus_registry", paths.corpus_registry)):
    """Create lemgram index SQL file."""
    attribute_fields = {"lemgram": "freq", "prefix": "freq_prefix", "suffix": "freq_suffix"}

    corpus = corpus.upper()
    index = _count_lemgrams(corpus, attributes, corpus_registry)

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

    log.info("Creating SQL")
    mysql.add_row(MYSQL_TABLE, rows)


def _count_lemgrams(corpus, attributes, corpus_registry):
    """Count lemgrams using cwb-scan."""
    log.info("Reading corpus")
    result = {}
    process = subprocess.Popen([CWB_SCAN_EXECUTABLE, "-q", "-r", corpus_registry, corpus] + attributes,
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
