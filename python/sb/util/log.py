# -*- coding: utf-8 -*-

import time
import sys
import os

totalwarnings = 0
totalerrors = 0
starttime = 0
timeformat = "%H.%M.%S"
process_id_prefix = ""

def init(level=None, format=None, timefmt=None, showpid=False):
    """Initialise logging to <stderr>.
    Resets the warning and error counters.
    """
    global totalwarnings, totalerrors, starttime, timeformat, process_id_prefix
    if timefmt: timeformat = timefmt
    totalwarnings = 0
    totalerrors = 0
    starttime = time.time()
    process_id_prefix = "%06d " % os.getpid() if showpid else ""

def strtime():
    """Formats the current elapsed time according to the time format."""
    if not starttime: init()
    return time.strftime(timeformat)

def newline():
    print >>sys.stderr

def line(ch):
    print >>sys.stderr, process_id_prefix + ch * 80

def output(msg="", *args):
    """Prints a message (plus newline) on stderr."""
    print >>sys.stderr, process_id_prefix + "|", msg % args

def header():
    newline()
    line("_")

def info(msg, *args):
    """Prints/logs an informational message."""
    if not starttime: init()
    output(strtime() + ": " + msg, *args)

def warning(msg, *args):
    """Prints/logs a warning message."""
    if not starttime: init()
    global totalwarnings
    totalwarnings += 1
    output("warning : " + msg, *args)

def error(msg, *args):
    """Prints/logs an error message."""
    if not starttime: init()
    global totalerrors
    totalerrors += 1
    output("-ERROR- : " + msg, *args)

def statistics():
    info("Total time: %.2f s", time.time() - starttime)
    if totalerrors or totalwarnings:
        output("%d warnings were reported", totalwarnings)
        output("%d ERRORS were reported", totalerrors)
    line("^")
    newline()


