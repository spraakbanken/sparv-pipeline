# -*- coding: utf-8 -*-

"""
Formats dates and times.
"""
import datetime, re
from dateutil.relativedelta import relativedelta
import util

def dateformat(infrom, outfrom=None, into=None, outto=None, informat="", outformat="%Y%m%d%H%M%S", encoding="UTF-8"):
    """Takes dates and input formats. Converts to specified format.
    
    - infrom, annotation containing from-dates
    - outfrom, annotation with from-dates to be written
    - into, annotation containing to-dates (optional)
    - outto, annotation with to-dates to be written (optional)
    - informat, the format of the infrom and into dates. Several formats can be specified separated by |. They will be tried in order.
    - outformat, the desired format of the outfrom and outto dates. Several formats can be specified separated by |. They will be tied to their respective in-format.
    
    http://docs.python.org/library/datetime.html#strftime-and-strptime-behavior
    """
    
    def get_smallest_unit(informat):
        smallest_unit = 0 # No date
    
        if not "%y" in informat and not "%Y" in informat:
            pass
        elif not "%b" in informat and not "%B" in informat and not "%m" in informat:
            smallest_unit = 1 # year
        elif not "%d" in informat:
            smallest_unit = 2 # month
        elif not "%H" in informat and not "%I" in informat:
            smallest_unit = 3 # day
        elif not "%M" in informat:
            smallest_unit = 4 # hour
        elif not "%S" in informat:
            smallest_unit = 5 # minute
        else:
            smallest_unit = 6 # second
        
        return smallest_unit
    
    if not into:
        into = infrom
       
    informat = informat.split("|")
    outformat = outformat.split("|")
    
    assert len(outformat) == 1 or (len(outformat) == len(informat)), "The number of out-formats must be equal to one or the number of in-formats."
    
    ifrom = util.read_annotation_iteritems(infrom)
    ofrom = {}
    
    for key, val in ifrom:
        tries = 0
        for inf in informat:
            tries += 1
            try:
                fromdate = datetime.datetime.strptime(val.encode(encoding), inf)
                ofrom[key] = strftime(fromdate, outformat[0] if len(outformat) == 1 else outformat[tries - 1])
                break
            except ValueError:
                if tries == len(informat):
                    raise
                continue

    util.write_annotation(outfrom, ofrom)
    del ofrom

    if outto:
        ito = util.read_annotation_iteritems(into)
        oto = {}
    
        for key, val in ito:
            tries = 0
            for inf in informat:
                tries += 1
                try:
                    smallest_unit = get_smallest_unit(inf)
                    todate = datetime.datetime.strptime(val.encode(encoding), inf)
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
                    
                    todate = todate + add - relativedelta(seconds=1)
                    oto[key] = strftime(todate, outformat[0] if len(outformat) == 1 else outformat[tries - 1])
                    break
                except ValueError:
                    if tries == len(informat):
                        raise
                    continue
        
        util.write_annotation(outto, oto)

def strftime(dt, fmt):
    """Python datetime.strftime < 1900 workaround, taken from https://gist.github.com/2000837"""

    if dt.year < 1900:
        # create a copy of this datetime, just in case, then set the year to
        # something acceptable, then replace that year in the resulting string
        tmp_dt = datetime.datetime(datetime.MAXYEAR, dt.month, dt.day,
                                  dt.hour, dt.minute,
                                  dt.second, dt.microsecond,
                                  dt.tzinfo)
        
        if re.search('(?<!%)((?:%%)*)(%y)', fmt):
            util.log.warning("Using %y time format with year prior to 1900 could produce unusual results!")
        
        tmp_fmt = fmt
        tmp_fmt = re.sub('(?<!%)((?:%%)*)(%y)', '\\1\x11\x11', tmp_fmt, re.U)
        tmp_fmt = re.sub('(?<!%)((?:%%)*)(%Y)', '\\1\x12\x12\x12\x12', tmp_fmt, re.U)
        tmp_fmt = tmp_fmt.replace(str(datetime.MAXYEAR), '\x13\x13\x13\x13')
        tmp_fmt = tmp_fmt.replace(str(datetime.MAXYEAR)[-2:], '\x14\x14')
        
        result = tmp_dt.strftime(tmp_fmt)
        
        if '%c' in fmt:
            # local datetime format - uses full year but hard for us to guess where.
            result = result.replace(str(datetime.MAXYEAR), str(dt.year))
        
        result = result.replace('\x11\x11', str(dt.year)[-2:])
        result = result.replace('\x12\x12\x12\x12', str(dt.year))
        result = result.replace('\x13\x13\x13\x13', str(datetime.MAXYEAR))
        result = result.replace('\x14\x14', str(datetime.MAXYEAR)[-2:])
            
        return result
        
    else:
        return dt.strftime(fmt)


if __name__ == '__main__':
    util.run.main(dateformat
                  )