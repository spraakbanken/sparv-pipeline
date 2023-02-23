"""Create timespan SQL data for use in Korp."""

from collections import defaultdict
from typing import Optional

from sparv.api import (
    AllSourceFilenames,
    AnnotationAllSourceFiles,
    Config,
    Corpus,
    Export,
    ExportInput,
    MarkerOptional,
    OutputMarker,
    annotator,
    exporter,
    get_logger,
    installer,
    uninstaller,
    util
)
from sparv.api.util.mysql_wrapper import MySQL

logger = get_logger(__name__)


@installer("Install timespan SQL on remote host", uninstaller="korp:uninstall_timespan")
def install_timespan(
    sqlfile: ExportInput = ExportInput("korp.timespan/timespan.sql"),
    marker: OutputMarker = OutputMarker("korp.install_timespan_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("korp.uninstall_timespan_marker"),
    db_name: str = Config("korp.mysql_dbname"),
    host: Optional[str] = Config("korp.remote_host"),
):
    """Install timespan SQL on remote host.

    Args:
        sqlfile: SQL file to be installed.
        marker: Marker file to be written.
        uninstall_marker: Uninstall marker to remove.
        db_name: Name of the database.
        host: Remote host to install to.
    """
    util.install.install_mysql(host, db_name, sqlfile)
    uninstall_marker.remove()
    marker.write()


@uninstaller("Uninstall timespan data from database", language=["swe"])
def uninstall_timespan(
    corpus: Corpus = Corpus(),
    marker: OutputMarker = OutputMarker("korp.uninstall_timespan_marker"),
    install_marker: MarkerOptional = MarkerOptional("korp.install_timespan_marker"),
    db_name: str = Config("korp.mysql_dbname"),
    host: Optional[str] = Config("korp.remote_host")
):
    """Remove timespan data from database.

    Args:
        corpus: Corpus ID.
        marker: Uninstall marker to write.
        install_marker: Install marker to remove.
        db_name: Name of the database.
        host: Remote host.
    """
    sql = MySQL(database=db_name, host=host)
    sql.delete_rows(MYSQL_TABLE, {"corpus": corpus.upper()})
    sql.delete_rows(MYSQL_TABLE_DATE, {"corpus": corpus.upper()})
    install_marker.remove()
    marker.write()


@exporter("Timespan SQL data for use in Korp", abstract=True)
def timespan_sql(_sql: ExportInput = ExportInput("korp.timespan/timespan.sql")):
    """Create timespan SQL data for use in Korp."""
    pass


@annotator("Timespan SQL data for use in Korp", order=1)
def timespan_sql_with_dateinfo(corpus: Corpus = Corpus(),
                               out: Export = Export("korp.timespan/timespan.sql"),
                               source_files: AllSourceFilenames = AllSourceFilenames(),
                               token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
                               datefrom: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<text>:dateformat.datefrom"),
                               dateto: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<text>:dateformat.dateto"),
                               timefrom: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<text>:dateformat.timefrom"),
                               timeto: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<text>:dateformat.timeto")):
    """Create timespan SQL data for use in Korp."""
    corpus_name = corpus.upper()
    datespans = defaultdict(int)
    datetimespans = defaultdict(int)

    for file in source_files:
        text_tokens, orphans = datefrom.get_children(file, token)
        if orphans:
            datespans[("0" * 8, "0" * 8)] += len(orphans)
            datetimespans[("0" * 14, "0" * 14)] += len(orphans)
        dateinfo = datefrom.read_attributes(file, (datefrom, dateto, timefrom, timeto))
        for text in text_tokens:
            d = next(dateinfo)
            datespans[(d[0].zfill(8), d[1].zfill(8))] += len(text)
            datetimespans[(d[0].zfill(8) + d[2].zfill(6), d[1].zfill(8) + d[3].zfill(6))] += len(text)

    rows_date = []
    rows_datetime = []

    for span in datespans:
        rows_date.append({
            "corpus": corpus_name,
            "datefrom": span[0],
            "dateto": span[1],
            "tokens": datespans[span]
        })

    for span in datetimespans:
        rows_datetime.append({
            "corpus": corpus_name,
            "datefrom": span[0],
            "dateto": span[1],
            "tokens": datetimespans[span]
        })

    create_sql(corpus_name, out, rows_date, rows_datetime)


@annotator("Timespan SQL data for use in Korp, for when the corpus has no date metadata.", order=2)
def timespan_sql_no_dateinfo(corpus: Corpus = Corpus(),
                             out: Export = Export("korp.timespan/timespan.sql"),
                             source_files: AllSourceFilenames = AllSourceFilenames(),
                             token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>")):
    """Create timespan SQL data for use in Korp."""
    corpus_name = corpus.upper()
    token_count = 0

    for file in source_files:
        token_count += token.get_size(file)

    rows_date = [{
        "corpus": corpus_name,
        "datefrom": "0" * 8,
        "dateto": "0" * 8,
        "tokens": token_count
    }]
    rows_datetime = [{
        "corpus": corpus_name,
        "datefrom": "0" * 14,
        "dateto": "0" * 14,
        "tokens": token_count
    }]

    create_sql(corpus_name, out, rows_date, rows_datetime)


def create_sql(corpus_name: str, out: Export, rows_date, rows_datetime):
    """Create timespans SQL file."""
    logger.info("Creating SQL")
    mysql = MySQL(output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_TIMESPAN)
    mysql.create_table(MYSQL_TABLE_DATE, drop=False, **MYSQL_TIMESPAN_DATE)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus_name})
    mysql.delete_rows(MYSQL_TABLE_DATE, {"corpus": corpus_name})
    mysql.set_names()
    mysql.add_row(MYSQL_TABLE, rows_datetime)
    mysql.add_row(MYSQL_TABLE_DATE, rows_date)


MYSQL_TABLE = "timedata"
MYSQL_TABLE_DATE = "timedata_date"

MYSQL_TIMESPAN = {"columns": [("corpus", "varchar(64)", "", "NOT NULL"),
                              ("datefrom", "datetime", "0000-00-00 00:00:00", "NOT NULL"),
                              ("dateto", "datetime", "0000-00-00 00:00:00", "NOT NULL"),
                              ("tokens", int, 0, "NOT NULL")],
                  "primary": "corpus datefrom dateto",
                  "indexes": [],
                  "default charset": "utf8"
                  }

MYSQL_TIMESPAN_DATE = {"columns": [("corpus", "varchar(64)", "", "NOT NULL"),
                                   ("datefrom", "date", "0000-00-00", "NOT NULL"),
                                   ("dateto", "date", "0000-00-00", "NOT NULL"),
                                   ("tokens", int, 0, "NOT NULL")],
                       "primary": "corpus datefrom dateto",
                       "indexes": [],
                       "default charset": "utf8"
                       }
