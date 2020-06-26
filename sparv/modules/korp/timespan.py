"""Create timespan SQL data for use in Korp."""

import logging
from collections import defaultdict

import sparv.util as util
from sparv import (AllDocuments, AnnotationAllDocs, Config, Corpus, Export, ExportInput, OutputCommonData, exporter,
                   installer)
from sparv.util.mysql_wrapper import MySQL

log = logging.getLogger(__name__)


@installer("Install timespan SQL on remote host")
def install_timespan(sqlfile: ExportInput = ExportInput("korp_timespan/timespan.sql"),
                     out: OutputCommonData = OutputCommonData("korp.time_install_timespan"),
                     db_name: str = Config("korp.mysql_dbname", ""),
                     host: str = Config("korp.remote_host", "")):
    """Install timespan SQL on remote host.

    Args:
        sqlfile (str, optional): SQL file to be installed. Defaults to ExportInput("korp_timespan/timespan.sql").
        out (str, optional): Timestamp file to be written.
            Defaults to OutputCommonData("korp.time_install_relations").
        db_name (str, optional): Name of the data base. Defaults to Config("korp.mysql_dbname", "").
        host (str, optional): Remote host to install to. Defaults to Config("korp.remote_host", "").
    """
    util.install_mysql(host, db_name, sqlfile)
    out.write("")


@exporter("Timespan SQL data for use in Korp", config=[
    Config("korp.timespan_db_name", default="timespan")
])
def timespan_sql(corpus: Corpus = Corpus(),
                 db_name: str = Config("korp.timespan_db_name"),
                 out: Export = Export("korp_timespan/timespan.sql"),
                 docs: AllDocuments = AllDocuments(),
                 token: AnnotationAllDocs = AnnotationAllDocs("<token>"),
                 datefrom: AnnotationAllDocs = AnnotationAllDocs("<text>:dateformat.datefrom"),
                 dateto: AnnotationAllDocs = AnnotationAllDocs("<text>:dateformat.dateto"),
                 timefrom: AnnotationAllDocs = AnnotationAllDocs("<text>:dateformat.timefrom"),
                 timeto: AnnotationAllDocs = AnnotationAllDocs("<text>:dateformat.timeto")):
    """Create timespan SQL data for use in Korp."""
    corpus = corpus.upper()
    datespans = defaultdict(int)
    datetimespans = defaultdict(int)

    for doc in docs:
        text_tokens, orphans = util.get_children(doc, datefrom, token)
        datespans[("0" * 8, "0" * 8)] += len(orphans)
        datetimespans[("0" * 14, "0" * 14)] += len(orphans)
        dateinfo = util.read_annotation_attributes(doc, (datefrom, dateto, timefrom, timeto))
        for i, text in enumerate(text_tokens):
            d = next(dateinfo)
            datespans[(d[0].zfill(8), d[1].zfill(8))] += len(text)
            datetimespans[(d[0].zfill(8) + d[2].zfill(6), d[1].zfill(8) + d[3].zfill(6))] += len(text)

    rows_date = []
    rows_datetime = []

    for span in datespans:
        rows_date.append({
            "corpus": corpus,
            "datefrom": span[0],
            "dateto": span[1],
            "tokens": datespans[span]
        })

    for span in datetimespans:
        rows_datetime.append({
            "corpus": corpus,
            "datefrom": span[0],
            "dateto": span[1],
            "tokens": datetimespans[span]
        })

    log.info("Creating SQL")
    mysql = MySQL(db_name, encoding=util.UTF8, output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_TIMESPAN)
    mysql.create_table(MYSQL_TABLE_DATE, drop=False, **MYSQL_TIMESPAN_DATE)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus})
    mysql.delete_rows(MYSQL_TABLE_DATE, {"corpus": corpus})
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
