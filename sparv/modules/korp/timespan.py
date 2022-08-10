"""Create timespan SQL data for use in Korp."""

from collections import defaultdict

from sparv.api import (AllSourceFilenames, Annotation, AnnotationAllSourceFiles, Config, Corpus, Export, ExportInput,
                       OutputCommonData, annotator, exporter, get_logger, installer, util)
from sparv.api.util.mysql_wrapper import MySQL

logger = get_logger(__name__)


@installer("Install timespan SQL on remote host")
def install_timespan(sqlfile: ExportInput = ExportInput("korp.timespan/timespan.sql"),
                     out: OutputCommonData = OutputCommonData("korp.install_timespan_marker"),
                     db_name: str = Config("korp.mysql_dbname"),
                     host: str = Config("korp.remote_host")):
    """Install timespan SQL on remote host.

    Args:
        sqlfile (str, optional): SQL file to be installed. Defaults to ExportInput("korp.timespan/timespan.sql").
        out (str, optional): Marker file to be written.
        db_name (str, optional): Name of the data base. Defaults to Config("korp.mysql_dbname").
        host (str, optional): Remote host to install to. Defaults to Config("korp.remote_host").
    """
    util.install.install_mysql(host, db_name, sqlfile)
    out.write("")


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
        text_tokens, orphans = Annotation(datefrom.name, source_file=file).get_children(token)
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
