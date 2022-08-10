"""Create files needed for the lemgram search in Korp."""

from collections import defaultdict

from sparv.api import (AllSourceFilenames, AnnotationAllSourceFiles, Config, Corpus, Export, ExportInput, OutputCommonData, exporter,
                       get_logger, installer, util)
from sparv.api.util.mysql_wrapper import MySQL

logger = get_logger(__name__)


# Path to the cwb-scan-corpus binary
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"


@installer("Install lemgram SQL on remote host", language=["swe"])
def install_lemgrams(sqlfile: ExportInput = ExportInput("korp.lemgram_index/lemgram_index.sql"),
                     marker: OutputCommonData = OutputCommonData("korp.install_lemgram_marker"),
                     db_name: str = Config("korp.mysql_dbname"),
                     host: str = Config("korp.remote_host")):
    """Install lemgram SQL on remote host.

    Args:
        sqlfile (str, optional): SQL file to be installed.
            Defaults to ExportInput("korp.lemgram_index/lemgram_index.sql").
        marker (str, optional): Marker file to be written.
            Defaults to OutputCommonData("korp.install_lemgram_marker").
        db_name (str, optional): Name of the data base. Defaults to Config("korp.mysql_dbname").
        host (str, optional): Remote host to install to. Defaults to Config("korp.remote_host").
    """
    util.install.install_mysql(host, db_name, sqlfile)
    marker.write("")


@exporter("Lemgram index SQL file for use in Korp", language=["swe"])
def lemgram_sql(corpus: Corpus = Corpus(),
                source_files: AllSourceFilenames = AllSourceFilenames(),
                out: Export = Export("korp.lemgram_index/lemgram_index.sql"),
                lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:saldo.lemgram")):
    """Create lemgram index SQL file."""
    corpus = corpus.upper()
    result = defaultdict(int)

    for file in source_files:
        for lg in lemgram.read(file):
            for value in lg.split("|"):
                if value and ":" not in value:
                    result[value] += 1

    mysql = MySQL(output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_INDEX)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus})
    mysql.set_names()

    rows = []
    for lemgram, freq in list(result.items()):
        rows.append({
            "lemgram": lemgram,
            "corpus": corpus,
            "freq": freq
        })

    logger.info("Creating SQL")
    mysql.add_row(MYSQL_TABLE, rows)


MYSQL_TABLE = "lemgram_index"
MYSQL_INDEX = {"columns": [("lemgram", "varchar(64)", "", "NOT NULL"),
                           ("freq", int, 0, "NOT NULL"),
                           ("corpus", "varchar(64)", "", "NOT NULL")],
               "indexes": ["lemgram corpus freq"],  # Can't make this primary due to collation
               "default charset": "utf8mb4",
               }
