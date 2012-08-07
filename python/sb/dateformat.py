# -*- coding: utf-8 -*-

"""
Formats dates and times.
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
import util

def dateformat(infrom, outfrom=None, into=None, outto=None, informat="", outformat="%Y%m%d%H%M%S", encoding="UTF-8"):
    """Takes dates and input formats. Converts to specified format.
    
    - infrom, annotation containing from-dates
    - outfrom, annotation with from-dates to be written
    - into, annotation containing to-dates (optional)
    - outto, annotation with to-dates to be written (optional)
    - informat, the format of the infrom and into dates. Several formats can be specified separated by |. They will be tried in order.
    - outformat, the desired format of the outfrom and outto dates
    
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
    
    ifrom = util.read_annotation_iteritems(infrom)
    ofrom = {}
    
    for key, val in ifrom:
        tries = 0
        for inf in informat:
            tries += 1
            try:
                fromdate = datetime.strptime(val.encode(encoding), inf)
                ofrom[key] = datetime.strftime(fromdate, outformat)
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
                    todate = datetime.strptime(val.encode(encoding), inf)
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
                    oto[key] = datetime.strftime(todate, outformat)
                    break
                except ValueError:
                    if tries == len(informat):
                        raise
                    continue
        
        util.write_annotation(outto, oto)


if __name__ == '__main__':
    util.run.main(dateformat
                  )