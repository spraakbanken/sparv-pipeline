# -*- coding: utf-8 -*-

import time
import sys
import os
import constants

totalwarnings = 0
totalerrors = 0
starttime = 0
timeformat = "%H.%M.%S"
process_id_prefix = ""
lastmessage = []
logfile = "/warnings.log"

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
    msge = (msg % args).encode(constants.UTF8)
    print >>sys.stderr, process_id_prefix + "|", msge
    m = process_id_prefix + "| " + msge
    global lastmessage
    lastmessage.append(m)

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
    output(constants.COLORS["yellow"] + "warning : " + msg + constants.COLORS["default"], *args)

def error(msg, *args):
    """Prints/logs an error message."""
    if not starttime: init()
    global totalerrors
    totalerrors += 1
    output(constants.COLORS["red"] + "-ERROR- : " + msg + constants.COLORS["default"], *args)

def statistics():
    """Prints statistics and summary."""
    info("Total time: %.2f s", time.time() - starttime)
    if totalwarnings:
        output(constants.COLORS["yellow"] + constants.COLORS["bold"] + "%d warnings were reported" + constants.COLORS["default"], totalwarnings)
    if totalerrors:
        output(constants.COLORS["red"] + constants.COLORS["bold"] + "%d ERRORS were reported" + constants.COLORS["default"], totalerrors)
    if totalwarnings or totalerrors:
        save_to_logfile()
        raise_error = "" #raw_input("Press enter to continue. Enter anything else to break: ")
        if raise_error.strip() != "":
            raise StandardError
    line("^")
    newline()
    global lastmessage
    lastmessage = []

def save_to_logfile():
    """Append last warning or error to logfile."""
    global lastmessage
    with open(os.getcwd() + logfile, "a") as o:
        o.write(process_id_prefix + "_" * 80)
        o.write("\n")
        for l in lastmessage:
            for v in constants.COLORS.values():
                l = l.replace(v, "")
            o.write(l + "\n")
        o.write(process_id_prefix + "^" * 80)
        o.write("\n\n\n")

