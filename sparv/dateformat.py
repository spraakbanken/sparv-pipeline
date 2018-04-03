# -*- coding: utf-8 -*-

"""
Formats dates and times.
"""
import datetime
import re
from dateutil.relativedelta import relativedelta
import sparv.util as util


def dateformat(infrom, outfrom=None, into=None, outto=None, informat="", outformat="%Y%m%d%H%M%S", splitter=None, regex=None):
    """Takes dates and input formats. Converts to specified format.

    - infrom, annotation containing from-dates
    - outfrom, annotation with from-dates to be written
    - into, annotation containing to-dates (optional)
    - outto, annotation with to-dates to be written (optional)
    - informat, the format of the infrom and into dates. Several formats can be specified separated by |. They will be tried in order.
    - outformat, the desired format of the outfrom and outto dates. Several formats can be specified separated by |. They will be tied to their respective in-format.
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

    if not into:
        into = infrom

    informat = informat.split("|")
    outformat = outformat.split("|")
    if splitter:
        splitter = splitter

    assert len(outformat) == 1 or (len(outformat) == len(informat)), "The number of out-formats must be equal to one or the number of in-formats."

    ifrom = util.read_annotation_iteritems(infrom)
    ofrom = {}

    for key, val in ifrom:
        val = val.strip()
        if not val:
            ofrom[key] = None
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
                    ofrom[key] = None
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
                if len(fromdates) == 1 or outto:
                    ofrom[key] = strftime(fromdates[0], outformat[0] if len(outformat) == 1 else outformat[tries - 1])
                else:
                    outstrings = [strftime(fromdate, outformat[0] if len(outformat) == 1 else outformat[tries - 1]) for fromdate in fromdates]
                    ofrom[key] = outstrings[0] + splitter + outstrings[1]
                break
            except ValueError:
                if tries == len(informat):
                    util.log.error("Could not parse: %s", str(vals))
                    raise
                continue

    util.write_annotation(outfrom, ofrom)
    del ofrom

    if outto:
        ito = util.read_annotation_iteritems(into)
        oto = {}

        for key, val in ito:
            if not val:
                oto[key] = None
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
                        oto[key] = None
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
                    oto[key] = strftime(todates[-1], outformat[0] if len(outformat) == 1 else outformat[tries - 1])
                    break
                except ValueError:
                    if tries == len(informat):
                        util.log.error("Could not parse: %s", str(vals))
                        raise
                    continue

        util.write_annotation(outto, oto)


def strftime(dt, fmt):
    """Python datetime.strftime < 1900 workaround, taken from https://gist.github.com/2000837"""

    TEMPYEAR = 9996  # We need to use a leap year to support feb 29th

    if dt.year < 1900:
        # create a copy of this datetime, just in case, then set the year to
        # something acceptable, then replace that year in the resulting string
        tmp_dt = datetime.datetime(TEMPYEAR, dt.month, dt.day,
                                   dt.hour, dt.minute,
                                   dt.second, dt.microsecond,
                                   dt.tzinfo)

        if re.search('(?<!%)((?:%%)*)(%y)', fmt):
            util.log.warning("Using %y time format with year prior to 1900 could produce unusual results!")

        tmp_fmt = fmt
        tmp_fmt = re.sub('(?<!%)((?:%%)*)(%y)', '\\1\x11\x11', tmp_fmt, re.U)
        tmp_fmt = re.sub('(?<!%)((?:%%)*)(%Y)', '\\1\x12\x12\x12\x12', tmp_fmt, re.U)
        tmp_fmt = tmp_fmt.replace(str(TEMPYEAR), '\x13\x13\x13\x13')
        tmp_fmt = tmp_fmt.replace(str(TEMPYEAR)[-2:], '\x14\x14')

        result = tmp_dt.strftime(tmp_fmt)

        if '%c' in fmt:
            # local datetime format - uses full year but hard for us to guess where.
            result = result.replace(str(TEMPYEAR), str(dt.year))

        result = result.replace('\x11\x11', str(dt.year)[-2:])
        result = result.replace('\x12\x12\x12\x12', str(dt.year))
        result = result.replace('\x13\x13\x13\x13', str(TEMPYEAR))
        result = result.replace('\x14\x14', str(TEMPYEAR)[-2:])

        return result

    else:
        return dt.strftime(fmt)


if __name__ == '__main__':
    util.run.main(dateformat)
