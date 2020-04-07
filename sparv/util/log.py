# -*- coding: utf-8 -*-

import time
import sys
import os
from . import constants

totalwarnings = 0
totalerrors = 0
starttime = 0
timeformat = "%H.%M.%S"
process_id_prefix = ""
lastmessage = []
logfile = "/warnings.log"
sparv_debug = False


def init(level=None, format=None, timefmt=None, showpid=False):
    """Initialise logging to <stderr>.
    Resets the warning and error counters.
    """
    global totalwarnings, totalerrors, starttime, timeformat, process_id_prefix, sparv_debug
    if timefmt:
        timeformat = timefmt
    totalwarnings = 0
    totalerrors = 0
    starttime = time.time()
    process_id_prefix = "%06d " % os.getpid() if showpid else ""
    sparv_debug = os.environ.get('sparv_debug', "false").lower() == "true"


def strtime():
    """Formats the current elapsed time according to the time format."""
    if not starttime:
        init()
    return time.strftime(timeformat)


def newline():
    print(file=sys.stderr)


def line(ch):
    print(process_id_prefix + ch * 80, file=sys.stderr)


def output(msg="", *args):
    """Prints a message (plus newline) on stderr."""
    args = tuple(arg if isinstance(arg, str) else arg for arg in args)
    msge = msg % args
    print(process_id_prefix + "|", msge, file=sys.stderr)
    m = process_id_prefix + "| " + msge
    global lastmessage
    lastmessage.append(m)


def header():
    newline()
    line("_")


def info(msg, *args):
    """Prints/logs an informational message."""
    if not starttime:
        init()
    output(strtime() + ": " + msg, *args)


def warning(msg, *args):
    """Prints/logs a warning message."""
    if not starttime:
        init()
    global totalwarnings
    totalwarnings += 1
    output(constants.Color.YELLOW + "warning : " + msg + constants.Color.RESET, *args)


def error(msg, *args):
    """Prints/logs an error message."""
    if not starttime:
        init()
    global totalerrors
    totalerrors += 1
    output(constants.Color.RED + "-ERROR- : " + msg + constants.Color.RESET, *args)


def debug(msg, *args):
    """Prints/logs a debug message.
    Requires environment variable sparv_debug=true when running make."""
    if not starttime:
        init()
    global sparv_debug
    if sparv_debug:
        output(constants.Color.CYAN + "-DEBUG- : " + msg + constants.Color.RESET, *args)


def statistics():
    """Prints statistics and summary."""
    info("Total time: %.2f s", time.time() - starttime)
    if totalwarnings:
        output(constants.Color.YELLOW + constants.Color.BOLD + "%d warnings were reported" + constants.Color.RESET, totalwarnings)
    if totalerrors:
        output(constants.Color.RED + constants.Color.BOLD + "%d ERRORS were reported" + constants.Color.RESET, totalerrors)
    if totalwarnings or totalerrors:
        save_to_logfile()
        raise_error = ""  # raw_input("Press enter to continue. Enter anything else to break: ")
        if raise_error.strip() != "":
            raise Exception
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
        styles = [v[1] for v in constants.Color.__dict__.items() if not v[0].startswith("__")]
        for l in lastmessage:
            # Remove styling
            for v in styles:
                l = l.replace(v, "")
            o.write(l + "\n")
        o.write(process_id_prefix + "^" * 80)
        o.write("\n\n\n")
