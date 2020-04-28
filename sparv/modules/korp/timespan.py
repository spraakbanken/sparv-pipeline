"""Create timespan SQL data for use in Korp."""

import logging

import sparv.util as util
from sparv import Config, Corpus, Export, ExportInput, Output, exporter, installer
from sparv.core import paths
from sparv.util.mysql_wrapper import MySQL

log = logging.getLogger(__name__)

# Path to the cwb-scan-corpus binary
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"
CQP_EXECUTABLE = "cqp"


@installer("Install timespan SQL on remote host")
def install_timespan(sqlfile: str = ExportInput("korp_timespan/timespan.sql"),
                     out: str = Output("korp.time_install_timespan", data=True, common=True),
                     db_name: str = Config("korp.mysql_dbname", ""),
                     host: str = Config("remote_host", "")):
    """Install timespan SQL on remote host.

    Args:
        sqlfile (str, optional): SQL file to be installed. Defaults to ExportInput("korp_timespan/timespan.sql").
        out (str, optional): Timestamp file to be written.
            Defaults to Output("korp.time_install_relations", data=True, common=True).
        db_name (str, optional): Name of the data base. Defaults to Config("korp.mysql_dbname", "").
        host (str, optional): Remote host to install to. Defaults to Config("remote_host", "").
    """
    util.install_mysql(host, db_name, sqlfile)
    util.write_common_data(out, "")


@exporter("Create timespan SQL data for use in Korp")
def timespan_sql(corpus: str = Corpus,
                 db_name: str = Config("korp_timespan", "timespan"),
                 corpus_registry: str = Config("corpus_registry", paths.corpus_registry),
                 out: str = Export("korp_timespan/timespan.sql")):
    """Create timespan SQL data for use in Korp."""
    def calculate(usetime=True):
        rows = []

        dateattribs = ["text_datefrom", "text_timefrom", "text_dateto", "text_timeto"] if usetime else ["text_datefrom",
                                                                                                        "text_dateto"]

        reply, error = util.system.call_binary(CWB_SCAN_EXECUTABLE, ["-q", "-r", corpus_registry, corpus] + dateattribs,
                                               encoding="UTF-8", allow_error=True)
        if error:
            if "Error: can't open attribute" in error and (".text_datefrom" in error or ".text_dateto" in error):
                log.info("No date information present in corpus.")
                # No date information in corpus. Calculate total token count instead.
                reply, error = util.system.call_binary(CQP_EXECUTABLE, ["-c", "-r", corpus_registry],
                                                       "set PrettyPrint off;%s;info;" % corpus, encoding="UTF-8")

                if error:
                    log.error(error)
                    raise Exception

                for line in reply.splitlines():
                    if line.startswith("Size: "):
                        reply = "%s\t\t\t\t" % line[6:].strip()
            else:
                log.error(error)
                raise Exception(error)

        spans = {}

        for line in reply.splitlines():
            if not line:
                continue
            line = line.split("\t")
            tokens = int(line[0])

            if usetime:
                dfrom = line[1] + line[2]
                dto = line[3] + line[4]
                dfrom = dfrom.zfill(14)  # Pad years < 1000 with zeroes
                dto = dto.zfill(14)
            else:
                dfrom = line[1]
                dto = line[2]
                dfrom = dfrom.zfill(8)
                dto = dto.zfill(8)

            span = (dfrom, dto)
            spans[span] = spans.get(span, 0) + tokens  # Sometimes we get more than one row for tokens without date information

        for span in spans:

            row = {
                "corpus": corpus,
                "datefrom": span[0],
                "dateto": span[1],
                "tokens": spans[span]
            }

            rows.append(row)

        return rows

    corpus = corpus.upper()

    rows_datetime = calculate(True)
    rows_date = calculate(False)

    log.info("Creating SQL")
    mysql = MySQL(db_name, encoding=util.UTF8, output=out)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_TIMESPAN)
    mysql.create_table(MYSQL_TABLE_DATE, drop=False, **MYSQL_TIMESPAN_DATE)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus})
    mysql.delete_rows(MYSQL_TABLE_DATE, {"corpus": corpus})
    mysql.set_names()

    mysql.add_row(MYSQL_TABLE, rows_datetime)
    mysql.add_row(MYSQL_TABLE_DATE, rows_date)


################################################################################

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
