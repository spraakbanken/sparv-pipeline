"""Formats dates and times."""

import datetime
import re

from dateutil.relativedelta import relativedelta

from sparv.api import Annotation, Config, Output, OutputCommonData, SparvErrorMessage, annotator, get_logger

logger = get_logger(__name__)


@annotator(
    "Convert existing dates to specified output format",
    config=[
        Config(
            "dateformat.datetime_from",
            description="Annotation attribute containing from-dates (and times)",
            datatype=str,
        ),
        Config(
            "dateformat.datetime_to", description="Annotation attribute containing to-dates (and times)", datatype=str
        ),
        Config(
            "dateformat.datetime_informat",
            description="Format of the source date/time values, using format codes from "
            "https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes. Several "
            "formats can be specified separated by '|'. They will be tried in order.",
            datatype=str,
        ),
        Config(
            "dateformat.splitter",
            description="One or more characters separating two dates in 'datetime_from', "
            "treating them as from-date and to-date.",
            datatype=str,
        ),
        Config(
            "dateformat.pre_regex",
            description="Regular expression with a catching group whose content will be used in the parsing instead of "
            "the whole string. Applied before splitting.",
            datatype=str,
        ),
        Config(
            "dateformat.regex",
            description="Regular expression with a catching group whose content will be used in the parsing instead of "
            "the whole string. Applied on each value after splitting.",
            datatype=str,
        ),
        Config(
            "dateformat.date_outformat",
            default="%Y%m%d",
            description="Desired format of the formatted dates, specified using the same format codes as for the "
            "in-format. Several formats can be specified separated by '|'. They will be tied to their respective "
            "in-format.",
            datatype=str,
        ),
        Config(
            "dateformat.out_annotation",
            default="<text>",
            description="Annotation on which the resulting formatted date attributes will be written.",
            datatype=str,
        ),
    ],
)
def dateformat(
    in_from: Annotation = Annotation("[dateformat.datetime_from]"),
    in_to: Annotation | None = Annotation("[dateformat.datetime_to]"),
    out_from: Output = Output("[dateformat.out_annotation]:dateformat.datefrom", description="From-dates"),
    out_to: Output | None = Output("[dateformat.out_annotation]:dateformat.dateto", description="To-dates"),
    informat: str = Config("dateformat.datetime_informat"),
    outformat: str = Config("dateformat.date_outformat"),
    splitter: str | None = Config("dateformat.splitter"),
    pre_regex: str | None = Config("dateformat.pre_regex"),
    regex: str | None = Config("dateformat.regex"),
) -> None:
    """Convert existing dates/times to specified date output format.

    https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior

    Args:
        in_from: Annotation containing from-dates (and times).
        in_to: Annotation containing to-dates.
        out_from: Annotation with from-times to be written.
        out_to: Annotation with to-times to be written.
        informat: Format of the in_from and in_to dates/times.
            Several formats can be specified separated by |. They will be tried in order.
        outformat: Desired format of the out_from and out_to dates.
            Several formats can be specified separated by |. They will be tied to their respective in-format.
        splitter: One or more characters separating two dates in 'in_from',
            treating them as from-date and to-date.
        pre_regex: Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Applied before splitting.
        regex: Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Applied on each value after splitting.
    """
    _formatter(in_from, in_to, out_from, out_to, informat, outformat, splitter, pre_regex, regex)


@annotator("Convert existing dates to format YYYY-MM-DD")
def dateformat_pretty(
    in_date: Annotation = Annotation("[dateformat.datetime_from]"),
    out: Output = Output(
        "[dateformat.out_annotation]:dateformat.date_pretty", description="Date without timestamp 'YYYY-MM-DD'"
    ),
    informat: str = Config("dateformat.datetime_informat"),
    splitter: str | None = Config("dateformat.splitter"),
    pre_regex: str | None = Config("dateformat.pre_regex"),
    regex: str | None = Config("dateformat.regex"),
) -> None:
    """Convert existing dates to format YYYY-MM-DD.

    Args:
        in_date: Annotation containing dates (and times).
        out: Annotation with formatted dates to be written.
        informat: Format of the in_date dates/times.
            Several formats can be specified separated by |. They will be tried in order.
        splitter: One or more characters separating two dates in 'in_date'.
            Treating them as from-date and to-date.
        pre_regex: Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Applied before splitting.
        regex: Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Applied on each value after splitting.
    """
    _formatter(in_date, None, out, None, informat, "%Y-%m-%d", splitter, pre_regex, regex)


@annotator(
    "Convert existing times to specified output format",
    config=[
        Config(
            "dateformat.time_outformat",
            "%H%M%S",
            description="Desired format of the formatted times. Several formats can be specified separated "
            "by |. They will be tied to their respective in-format.",
            datatype=str,
        )
    ],
)
def timeformat(
    in_from: Annotation = Annotation("[dateformat.datetime_from]"),
    in_to: Annotation | None = Annotation("[dateformat.datetime_to]"),
    out_from: Output = Output("[dateformat.out_annotation]:dateformat.timefrom", description="From-times"),
    out_to: Output | None = Output("[dateformat.out_annotation]:dateformat.timeto", description="To-times"),
    informat: str = Config("dateformat.datetime_informat"),
    outformat: str = Config("dateformat.time_outformat"),
    splitter: str | None = Config("dateformat.splitter"),
    pre_regex: str | None = Config("dateformat.pre_regex"),
    regex: str | None = Config("dateformat.regex"),
) -> None:
    """Convert existing dates/times to specified time output format.

    https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior

    Args:
        in_from: Annotation containing from-dates (and times).
        in_to: Annotation containing to-dates.
        out_from: Annotation with from-times to be written.
        out_to: Annotation with to-times to be written.
        informat: Format of the in_from and in_to dates/times.
            Several formats can be specified separated by |. They will be tried in order.
        outformat: Desired format of the out_from and out_to times.
            Several formats can be specified separated by |. They will be tied to their respective in-format.
        splitter: One or more characters separating two dates in 'in_from',
            treating them as from-date and to-date.
        pre_regex: Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Applied before splitting.
        regex: Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Applied on each value after splitting.
    """
    _formatter(in_from, in_to, out_from, out_to, informat, outformat, splitter, pre_regex, regex)


@annotator("Get datetime resolutions from informat")
def resolution(
    out_resolution: OutputCommonData = OutputCommonData("dateformat.resolution", description="Datetime resolution"),
    informat: str | None = Config("dateformat.datetime_informat"),
) -> None:
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


def _formatter(
    in_from: Annotation,
    in_to: Annotation | None,
    out_from: Output,
    out_to: Output | None,
    in_format: str,
    out_format: str,
    splitter: str,
    pre_regex: str,
    regex: str,
) -> None:
    """Take existing dates/times and input formats and convert to specified output format.

    Args:
        in_from: Annotation containing from-dates (and times).
        in_to: Annotation containing to-dates.
        out_from: Annotation with from-times to be written.
        out_to: Annotation with to-times to be written.
        in_format: Format of the in_from and in_to dates/times.
            Several formats can be specified separated by |. They will be tried in order.
        out_format: Desired format of the out_from and out_to dates.
            Several formats can be specified separated by |. They will be tied to their respective in-format.
        splitter: One or more characters separating two dates in 'in_from',
            treating them as from-date and to-date.
        pre_regex: Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Applied before splitting.
        regex: Regular expression with a catching group whose content will be used in the parsing
            instead of the whole string. Applied on each value after splitting.

    Raises:
        SparvErrorMessage: If the input annotation does not match the output annotation.
        ValueError: If the input format is invalid.
    """

    def get_smallest_unit(informat: str) -> str | None:
        smallest_unit = None  # No date

        if "%y" not in informat and "%Y" not in informat:
            pass
        elif "%b" not in informat and "%B" not in informat and "%m" not in informat:
            smallest_unit = "years"
        elif "%d" not in informat:
            smallest_unit = "months"
        elif "%H" not in informat and "%I" not in informat:
            smallest_unit = "days"
        elif "%M" not in informat:
            smallest_unit = "hours"
        elif "%S" not in informat:
            smallest_unit = "minutes"
        else:
            smallest_unit = "seconds"

        return smallest_unit

    def get_date_length(informat: str) -> int | None:
        parts = informat.split("%")
        length = len(parts[0])  # First value is either blank or not part of date

        lengths = {
            "Y": 4,
            "3Y": 3,
            "y": 2,
            "m": 2,
            "b": None,
            "B": None,
            "d": 2,
            "H": None,
            "I": None,
            "M": 2,
            "S": 2,
        }

        for part in parts[1:]:
            add = lengths.get(part[0], None)
            if add:
                length += add + len(part[1:])
            else:
                return None

        return length

    # Check that the input annotation matches the output
    if (in_from and in_from.annotation_name != out_from.annotation_name) or (
        in_to and in_to.annotation_name != out_to.annotation_name
    ):
        raise SparvErrorMessage(
            "The 'dateformat' attributes must be attached to the same annotation as the input"
            f" (in this case the '{in_from.annotation_name}' annotation)"
        )

    if not in_to:
        in_to = in_from

    in_format = in_format.split("|")
    out_format = out_format.split("|")

    assert len(out_format) == 1 or (len(out_format) == len(in_format)), (
        "The number of out-formats must be equal to one or the number of in-formats."
    )

    ifrom = list(in_from.read())
    ofrom = in_from.create_empty_attribute()

    for index, val in enumerate(ifrom):
        val = val.strip()  # noqa: PLW2901
        if not val:
            ofrom[index] = None
            continue

        if pre_regex:
            matches = re.match(pre_regex, val)
            if not matches:
                raise SparvErrorMessage(f"dateformat.pre_regex did not match the value {val!r}")
            val = next(v for v in matches.groups() if v)  # noqa: PLW2901
            if not val:
                # If the regex doesn't match, treat as no date
                ofrom[index] = None
                continue

        tries = 0
        for inf in in_format:
            if splitter and splitter in inf:
                values = re.findall(r"%[YybBmdHMS]", inf)
                if len(set(values)) < len(values):
                    vals = val.split(splitter)
                    inf = inf.split(splitter)  # noqa: PLW2901
            else:
                vals = [val]
                inf = [inf]  # noqa: PLW2901

            if regex:
                temp = []
                for v in vals:
                    matches = re.search(regex, v)
                    if matches:
                        temp.append(next(x for x in matches.groups() if x))
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
                        v = "0" + v  # noqa: PLW2901
                    if "%0m" in inf[i] or "%0d" in inf[i]:
                        inf[i] = inf[i].replace("%0m", "%m").replace("%0d", "%d")
                        datelen = get_date_length(inf[i])
                        if datelen and not datelen == len(v):
                            raise ValueError
                    fromdates.append(datetime.datetime.strptime(v, inf[i]))
                if len(fromdates) == 1 or out_to:
                    ofrom[index] = fromdates[0].strftime(
                        out_format[0] if len(out_format) == 1 else out_format[tries - 1]
                    )
                else:
                    outstrings = [
                        fromdate.strftime(out_format[0] if len(out_format) == 1 else out_format[tries - 1])
                        for fromdate in fromdates
                    ]
                    ofrom[index] = outstrings[0] + splitter + outstrings[1]
                break
            except ValueError:
                if tries == len(in_format):
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

            if pre_regex:
                matches = re.match(pre_regex, val)
                val = next(v for v in matches.groups() if v)  # noqa: PLW2901
                if not val:
                    # If the regex doesn't match, treat as no date
                    oto[index] = None
                    continue

            tries = 0
            for inf in in_format:
                if splitter and splitter in inf:
                    values = re.findall(r"%[YybBmdHMS]", inf)
                    if len(set(values)) < len(values):
                        vals = val.split(splitter)
                        inf = inf.split(splitter)  # noqa: PLW2901
                else:
                    vals = [val]
                    inf = [inf]  # noqa: PLW2901

                if regex:
                    temp = []
                    for v in vals:
                        matches = re.search(regex, v)
                        if matches:
                            temp.append(next(x for x in matches.groups() if x))
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
                            v = "0" + v  # noqa: PLW2901
                        if "%0m" in inf[i] or "%0d" in inf[i]:
                            inf[i] = inf[i].replace("%0m", "%m").replace("%0d", "%d")
                            datelen = get_date_length(inf[i])
                            if datelen and not datelen == len(v):
                                raise ValueError
                        todates.append(datetime.datetime.strptime(v, inf[i]))
                    smallest_unit = get_smallest_unit(inf[0])
                    if smallest_unit:
                        add = relativedelta(**{smallest_unit: 1})

                    todates = [todate + add - relativedelta(seconds=1) for todate in todates]
                    oto[index] = todates[-1].strftime(out_format[0] if len(out_format) == 1 else out_format[tries - 1])
                    break
                except ValueError:
                    if tries == len(in_format):
                        logger.error("Could not parse: %s", str(vals))
                        raise
                    continue

        out_to.write(oto)
