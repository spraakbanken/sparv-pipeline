"""Create files needed for the lemgram search in Korp."""

from collections import defaultdict

from sparv.api import (
    AllSourceFilenames,
    AnnotationAllSourceFiles,
    Config,
    Corpus,
    Export,
    ExportInput,
    MarkerOptional,
    OutputMarker,
    exporter,
    get_logger,
    installer,
    uninstaller,
    util,
)
from sparv.api.util.mysql_wrapper import MySQL

logger = get_logger(__name__)


@installer("Install lemgram SQL on remote host", language=["swe"], uninstaller="korp:uninstall_lemgrams")
def install_lemgrams(
    sqlfile: ExportInput = ExportInput("korp.lemgram_index/lemgram_index.sql"),
    marker: OutputMarker = OutputMarker("korp.install_lemgram_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("korp.uninstall_lemgram_marker"),
    db_name: str = Config("korp.mysql_dbname"),
    host: str | None = Config("korp.remote_host"),
) -> None:
    """Install lemgram SQL on remote host.

    Args:
        sqlfile: SQL file to be installed.
        marker: Marker file to be written.
        uninstall_marker: Uninstall marker to remove.
        db_name: Name of the database.
        host: Remote host to install to.
    """
    uninstall_marker.remove()
    util.install.install_mysql(host, db_name, sqlfile)
    marker.write()


@uninstaller("Uninstall lemgrams from database", language=["swe"])
def uninstall_lemgrams(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("korp.uninstall_lemgram_marker"),
    install_marker: MarkerOptional = MarkerOptional("korp.install_lemgram_marker"),
    db_name: str = Config("korp.mysql_dbname"),
    host: str | None = Config("korp.remote_host"),
) -> None:
    """Remove lemgram index data from database.

    Args:
        corpus: Corpus ID.
        marker: Uninstall marker to write.
        install_marker: Install marker to remove.
        db_name: Name of the database.
        host: Remote host.
    """
    sql = MySQL(database=db_name, host=host)
    sql.delete_rows(MYSQL_TABLE, {"corpus": corpus.upper()})
    install_marker.remove()
    marker.write()


@exporter("Lemgram index SQL file for use in Korp", language=["swe"])
def lemgram_sql(
    corpus: Corpus = Corpus(),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    out: Export = Export("korp.lemgram_index/lemgram_index.sql"),
    lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:lemgram>"),
) -> None:
    """Create lemgram index SQL file."""
    corpus_upper = corpus.upper()
    result = defaultdict(int)

    logger.progress(total=len(source_files) + 1)

    for file in source_files:
        for lg in lemgram(file).read():
            for value in lg.split("|"):
                if value and ":" not in value:
                    result[value] += 1
        logger.progress()

    mysql = MySQL(output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_INDEX)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus_upper})
    mysql.set_names()

    rows = []
    for lg, freq in result.items():
        rows.append(
            {
                "lemgram": lg,
                "corpus": corpus_upper,
                "freq": freq,
            }
        )

    logger.info("Creating SQL")
    mysql.add_row(MYSQL_TABLE, rows)
    logger.progress()


MYSQL_TABLE = "lemgram_index"
MYSQL_INDEX = {
    "columns": [
        ("lemgram", "varchar(64)", "", "NOT NULL"),
        ("freq", int, 0, "NOT NULL"),
        ("corpus", "varchar(64)", "", "NOT NULL"),
    ],
    "primary": "lemgram corpus freq",
    "indexes": ["corpus"],  # Used by uninstaller
    "default charset": "utf8mb4",
    "collate": "utf8mb4_bin",
}
