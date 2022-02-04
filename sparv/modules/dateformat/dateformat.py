"""Formats dates and times."""

import datetime
import re
from typing import Optional

from dateutil.relativedelta import relativedelta

from sparv.api import Annotation, Config, Output, OutputCommonData, SparvErrorMessage, annotator, get_logger

logger = get_logger(__name__)


@annotator("Convert existing dates to specified output format", config=[
    Config("dateformat.datetime_from", description="Annotation attribute containing from-dates (and times)"),
    Config("dateformat.datetime_to", description="Annotation attribute containing to-dates (and times)"),
    Config("dateformat.datetime_informat",
           description="Format of the source date/time values. Several formats can be specified separated "
                       "by |. They will be tried in order."),
    Config("dateformat.splitter", description="One or more characters separating two dates in 'datetime_from', "
                                              "treating them as from-date and to-date."),
    Config("dateformat.regex", description="Regular expression with a catching group whose content will be used in the "
                                           "parsing instead of the whole string."),
    Config("dateformat.date_outformat", default="%Y%m%d",
           description="Desired format of the formatted dates. Several formats can be specified separated "
                       "by |. They will be tied to their respective in-format."),
    Config("dateformat.out_annotation", default="<text>",
           description="Annotation on which the resulting formatted date attributes will be written.")
])
def dateformat(in_from: Annotation = Annotation("[dateformat.datetime_from]"),
               in_to: Optional[Annotation] = Annotation("[dateformat.datetime_to]"),
               out_from: Output = Output("[dateformat.out_annotation]:dateformat.datefrom",
                                         description="From-dates"),
               out_to: Optional[Output] = Output("[dateformat.out_annotation]:dateformat.dateto",
                                                 description="To-dates"),
               informat: str = Config("dateformat.datetime_informat"),
               outformat: str = Config("dateformat.date_outformat"),
               splitter: Optional[str] = Config("dateformat.splitter", None),
               regex: Optional[str] = Config("dateformat.regex", None)):
    """Convert existing dates/times to specified date output format.

    http://docs.python.org/library/datetime.html#strftime-and-strptime-behavior

    Args:
        in_from (str, optional): Annotation containing from-dates (and times).
            Defaults to Annotation("[dateformat.datetime_from]").
        in_to (Optional[str], optional): Annotation containing to-dates.
            Defaults to Annotation("[dateformat.datetime_to]").
        out_from (str, optional): Annotation with from-times to be written.
            Defaults to Output("[dateformat.out_annotation]:dateformat.datefrom",description="From-dates").
        out_to (Optional[str], optional): Annotation with to-times to be written.
            Defaults to Output("[dateformat.out_annotation]:dateformat.dateto",description="To-dates").
        informat (str, optional): Format of the in_from and in_to dates/times.
            Several formats can be specified separated by |. They will be tried in order.
            Defaults to Config("dateformat.datetime_informat").
        outformat (str, optional): Desired format of the out_from and out_to dates.
            Several formats can be specified separated by |. They will be tied to their respective in-format.
            Defaults to Config("dateformat.date_outformat", "%Y%m%d").
        splitter (str, optional): One or more characters separating two dates in 'in_from',
            treating them as from-date and to-date. Defaults to Config("dateformat.splitter", None).
        regex (str, optional): Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Defaults to Config("dateformat.regex", None).
    """
    _formatter(in_from, in_to, out_from, out_to, informat, outformat, splitter, regex)


@annotator("Convert existing times to specified output format", config=[
    Config("dateformat.time_outformat", "%H%M%S",
           description="Desired format of the formatted times. Several formats can be specified separated "
                       "by |. They will be tied to their respective in-format.")
])
def timeformat(in_from: Annotation = Annotation("[dateformat.datetime_from]"),
               in_to: Optional[Annotation] = Annotation("[dateformat.datetime_to]"),
               out_from: Output = Output("[dateformat.out_annotation]:dateformat.timefrom",
                                         description="From-times"),
               out_to: Optional[Output] = Output("[dateformat.out_annotation]:dateformat.timeto",
                                                 description="To-times"),
               informat: str = Config("dateformat.datetime_informat"),
               outformat: str = Config("dateformat.time_outformat"),
               splitter: Optional[str] = Config("dateformat.splitter", None),
               regex: Optional[str] = Config("dateformat.regex", None)):
    """Convert existing dates/times to specified time output format.

    http://docs.python.org/library/datetime.html#strftime-and-strptime-behavior

    Args:
        in_from (str, optional): Annotation containing from-dates (and times).
            Defaults to Annotation("[dateformat.datetime_from]").
        in_to (Optional[str], optional): Annotation containing to-dates.
            Defaults to Annotation("[dateformat.datetime_to]").
        out_from (str, optional): Annotation with from-times to be written.
            Defaults to Output("[dateformat.out_annotation]:dateformat.timefrom",description="From-times").
        out_to (Optional[str], optional): Annotation with to-times to be written.
            Defaults to Output("[dateformat.out_annotation]:dateformat.timeto",description="To-times").
        informat (str, optional): Format of the in_from and in_to dates/times.
            Several formats can be specified separated by |. They will be tried in order.
            Defaults to Config("dateformat.datetime_informat").
        outformat (str, optional): Desired format of the out_from and out_to times.
            Several formats can be specified separated by |. They will be tied to their respective in-format.
            Defaults to Config("dateformat.time_outformat", "%Y%m%d").
        splitter (str, optional): One or more characters separating two dates in 'in_from',
            treating them as from-date and to-date. Defaults to Config("dateformat.splitter", None).
        regex (str, optional): Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Defaults to Config("dateformat.regex", None).
    """
    _formatter(in_from, in_to, out_from, out_to, informat, outformat, splitter, regex)


@annotator("Get datetime resolutions from informat")
def resolution(out_resolution: OutputCommonData = OutputCommonData("dateformat.resolution"),
               informat: Optional[str] = Config("dateformat.datetime_informat")):
    """Get the datetime resolution from the informat defined in the corpus config.

    Args:
        out_resolution: Date format output.
        informat: Date in-format, used to calculate date resolution.
    """
    resolutions = []

    if informat:
        informats = informat.strip("|").split("|")
        for i in informats:
            res = []
            if any(s in i for s in ["%Y", "%y"]):
                res.append("Y")
            if any(s in i for s in ["%b", "%B", "%m"]):
                res.append("M")
            if any(s in i for s in ["%a", "%A", "%w", "%d"]):
                res.append("D")
            if any(s in i for s in ["%H", "%I"]):
                res.append("h")
            if "%M" in i:
                res.append("m")
            if "%S" in i:
                res.append("s")
            resolutions.append("".join(res))

        # Sort with more fine-grained resolutions first
        resolutions.sort(key=len, reverse=True)

    resolutions = "|".join(resolutions)

    # Write time resolution file
    out_resolution.write(resolutions)


def _formatter(in_from: Annotation, in_to: Optional[Annotation], out_from: Output, out_to: Output,
               informat: str, outformat: str, splitter: str, regex: str):
    """Take existing dates/times and input formats and convert to specified output format."""
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

    # Check that the input annotation matches the output
    if (in_from.annotation_name != out_from.annotation_name) or (
        in_to.annotation_name != out_to.annotation_name):
        raise SparvErrorMessage("The 'dateformat' attributes must be attached to the same annotation as the input"
                                f" (in this case the '{in_from.annotation_name}' annotation)")

    if not in_to:
        in_to = in_from

    informat = informat.split("|")
    outformat = outformat.split("|")
    if splitter:
        splitter = splitter

    assert len(outformat) == 1 or (len(outformat) == len(informat)), "The number of out-formats must be equal to one " \
                                                                     "or the number of in-formats."

    ifrom = list(in_from.read())
    ofrom = in_from.create_empty_attribute()

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
                    logger.error("Could not parse: %s", str(vals))
                    raise
                continue

    out_from.write(ofrom)
    del ofrom

    if out_to:
        ito = list(in_to.read())
        oto = in_to.create_empty_attribute()

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
                        logger.error("Could not parse: %s", str(vals))
                        raise
                    continue

        out_to.write(oto)
