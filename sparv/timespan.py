# -*- coding: utf-8 -*-
import subprocess
import os
import sparv.util as util
from sparv.util.mysql_wrapper import MySQL

# Path to the cwb-scan-corpus binary
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"
CQP_EXECUTABLE = "cqp"
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


def timespan(corpus, db_name, out):

    def calculate(usetime=True):
        rows = []

        dateattribs = ["text_datefrom", "text_timefrom", "text_dateto", "text_timeto"] if usetime else ["text_datefrom", "text_dateto"]

        process = subprocess.Popen([CWB_SCAN_EXECUTABLE, "-r", CORPUS_REGISTRY, corpus] + dateattribs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        reply, error = process.communicate()
        reply = reply.decode()
        if error:
            error = error.decode()
            if "Error:" in error:  # We always get something back on stderror from cwb-scan-corpus, so we must check if it really is an error
                if "Error: can't open attribute" in error and (".text_datefrom" in error or ".text_dateto" in error):
                    util.log.info("No date information present in corpus.")
                    # No date information in corpus. Calculate total token count instead.
                    process = subprocess.Popen([CQP_EXECUTABLE, "-c", "-r", CORPUS_REGISTRY], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    reply, error = process.communicate(bytes("set PrettyPrint off;%s;info;" % corpus, "UTF-8"))

                    if error:
                        print(error)
                        raise Exception

                    for line in reply.decode().splitlines():
                        if line.startswith("Size: "):
                            reply = "%s\t\t\t\t" % line[6:].strip()
                else:
                    print(error)
                    raise Exception

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

    util.log.info("Creating SQL")
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

MYSQL_TIMESPAN = {'columns': [
                               ("corpus",   "varchar(64)", "", "NOT NULL"),
                               ("datefrom",  "datetime", "0000-00-00 00:00:00", "NOT NULL"),
                               ("dateto",  "datetime", "0000-00-00 00:00:00", "NOT NULL"),
                               ("tokens",   int, 0, "NOT NULL")],
                  'primary': "corpus datefrom dateto",
                  'indexes': [],
                  'default charset': 'utf8'
                  }

MYSQL_TIMESPAN_DATE = {'columns': [
                               ("corpus",   "varchar(64)", "", "NOT NULL"),
                               ("datefrom",  "date", "0000-00-00", "NOT NULL"),
                               ("dateto",  "date", "0000-00-00", "NOT NULL"),
                               ("tokens",   int, 0, "NOT NULL")],
                       'primary': "corpus datefrom dateto",
                       'indexes': [],
                       'default charset': 'utf8'
                       }

if __name__ == '__main__':
    util.run.main(timespan)
