"""Formats dates and times."""

import datetime
import logging
import re
from typing import Optional

from dateutil.relativedelta import relativedelta

import sparv.util as util
from sparv import Annotation, Config, Document, Output, annotator

log = logging.getLogger(__name__)


@annotator("Convert existing dates to specified output format")
def dateformat(doc: str = Document,
               in_from: str = Annotation("{from_chunk}"),
               in_to: Optional[str] = Annotation("{to_chunk}"),
               out_from: str = Output("{from_chunk}:dateformat.from", description="From-dates"),
               out_to: Optional[str] = Output("{to_chunk}:dateformat.to", description="To-dates"),
               informat: str = Config("dateformat.informat", ""),
               outformat: str = Config("dateformat.outformat", "%Y%m%d%H%M%S"),
               splitter: str = Config("dateformat.splitter", None),
               regex: str = Config("dateformat.regex", None)):
    """Take existing dates and input formats and convert to specified output format.

    - doc, corpus document name
    - in_from, annotation containing from-dates
    - out_from, annotation with from-dates to be written
    - in_to, annotation containing to-dates (optional)
    - out_to, annotation with to-dates to be written (optional)
    - informat, the format of the infrom and into dates. Several formats can be specified separated by |. They will be tried in order.
    - outformat, the desired format of the outfrom and out_to dates. Several formats can be specified separated by |. They will be tied to their respective in-format.
    - splitter, a character or more separating two dates in 'infrom', treating them as from-date and to-date
    - regex, a regular expression with a catching group whose content will be used in the parsing instead of the whole string

    http://docs.python.org/library/datetime.html#strftime-and-strptime-behavior
    """
    def get_smallest_unit(informat):
        smallest_unit = 0  # No date

        if "%y" not in informat and "%Y" not in informat:
            pass
        elif "%b" not in informat and "%B" not in informat and "%m" not in informat:
            smallest_unit = 1  # year
        elif "%d" not in informat:
            smallest_unit = 2  # month
        elif "%H" not in informat and "%I" not in informat:
            smallest_unit = 3  # day
        elif "%M" not in informat:
            smallest_unit = 4  # hour
        elif "%S" not in informat:
            smallest_unit = 5  # minute
        else:
            smallest_unit = 6  # second

        return smallest_unit

    def get_date_length(informat):
        parts = informat.split("%")
        length = len(parts[0])  # First value is either blank or not part of date

        lengths = {"Y": 4,
                   "3Y": 3,
                   "y": 2,
                   "m": 2,
                   "b": None,
                   "B": None,
                   "d": 2,
                   "H": None,
                   "I": None,
                   "M": 2,
                   "S": 2}

        for part in parts[1:]:
            add = lengths.get(part[0], None)
            if add:
                length += add + len(part[1:])
            else:
                return None

        return length

    if not in_to:
        into = in_from

    informat = informat.split("|")
    outformat = outformat.split("|")
    if splitter:
        splitter = splitter

    assert len(outformat) == 1 or (len(outformat) == len(informat)), "The number of out-formats must be equal to one " \
                                                                     "or the number of in-formats."

    ifrom = list(util.read_annotation(doc, in_from))
    ofrom = util.create_empty_attribute(doc, ifrom)

    for index, val in enumerate(ifrom):
        val = val.strip()
        if not val:
            ofrom[index] = None
            continue

        tries = 0
        for inf in informat:
            if splitter and splitter in inf:
                values = re.findall("%[YybBmdHMS]", inf)
                if len(set(values)) < len(values):
                    vals = val.split(splitter)
                    inf = inf.split(splitter)
            else:
                vals = [val]
                inf = [inf]

            if regex:
                temp = []
                for v in vals:
                    matches = re.search(regex, v)
                    if matches:
                        temp.append([x for x in matches.groups() if x][0])
                if not temp:
                    # If the regex doesn't match, treat as no date
                    ofrom[index] = None
                    continue
                vals = temp

            tries += 1
            try:
                fromdates = []
                for i, v in enumerate(vals):
                    if "%3Y" in inf[i]:
                        datelen = get_date_length(inf[i])
                        if datelen and not datelen == len(v):
                            raise ValueError
                        inf[i] = inf[i].replace("%3Y", "%Y")
                        v = "0" + v
                    if "%0m" in inf[i] or "%0d" in inf[i]:
                        inf[i] = inf[i].replace("%0m", "%m").replace("%0d", "%d")
                        datelen = get_date_length(inf[i])
                        if datelen and not datelen == len(v):
                            raise ValueError
                    fromdates.append(datetime.datetime.strptime(v, inf[i]))
                if len(fromdates) == 1 or out_to:
                    ofrom[index] = fromdates[0].strftime(outformat[0] if len(outformat) == 1 else outformat[tries - 1])
                else:
                    outstrings = [fromdate.strftime(outformat[0] if len(outformat) == 1 else outformat[tries - 1])
                                  for fromdate in fromdates]
                    ofrom[index] = outstrings[0] + splitter + outstrings[1]
                break
            except ValueError:
                if tries == len(informat):
                    log.error("Could not parse: %s", str(vals))
                    raise
                continue

    util.write_annotation(doc, out_from, ofrom)
    del ofrom

    if out_to:
        ito = list(util.read_annotation(doc, into))
        oto = util.create_empty_attribute(doc, into)

        for index, val in enumerate(ito):
            if not val:
                oto[index] = None
                continue

            tries = 0
            for inf in informat:
                if splitter and splitter in inf:
                    values = re.findall("%[YybBmdHMS]", inf)
                    if len(set(values)) < len(values):
                        vals = val.split(splitter)
                        inf = inf.split(splitter)
                else:
                    vals = [val]
                    inf = [inf]

                if regex:
                    temp = []
                    for v in vals:
                        matches = re.search(regex, v)
                        if matches:
                            temp.append([x for x in matches.groups() if x][0])
                    if not temp:
                        # If the regex doesn't match, treat as no date
                        oto[index] = None
                        continue
                    vals = temp

                tries += 1
                try:
                    todates = []
                    for i, v in enumerate(vals):
                        if "%3Y" in inf[i]:
                            datelen = get_date_length(inf[i])
                            if datelen and not datelen == len(v):
                                raise ValueError
                            inf[i] = inf[i].replace("%3Y", "%Y")
                            v = "0" + v
                        if "%0m" in inf[i] or "%0d" in inf[i]:
                            inf[i] = inf[i].replace("%0m", "%m").replace("%0d", "%d")
                            datelen = get_date_length(inf[i])
                            if datelen and not datelen == len(v):
                                raise ValueError
                        todates.append(datetime.datetime.strptime(v, inf[i]))
                    smallest_unit = get_smallest_unit(inf[0])
                    if smallest_unit == 1:
                        add = relativedelta(years=1)
                    elif smallest_unit == 2:
                        add = relativedelta(months=1)
                    elif smallest_unit == 3:
                        add = relativedelta(days=1)
                    elif smallest_unit == 4:
                        add = relativedelta(hours=1)
                    elif smallest_unit == 5:
                        add = relativedelta(minutes=1)
                    elif smallest_unit == 6:
                        add = relativedelta(seconds=1)

                    todates = [todate + add - relativedelta(seconds=1) for todate in todates]
                    oto[index] = todates[-1].strftime(outformat[0] if len(outformat) == 1 else outformat[tries - 1])
                    break
                except ValueError:
                    if tries == len(informat):
                        log.error("Could not parse: %s", str(vals))
                        raise
                    continue

        util.write_annotation(doc, out_to, oto)
