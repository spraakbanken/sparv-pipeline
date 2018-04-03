# -*- coding: utf-8 -*-

import inspect
import sys
import os
from . import log
from getopt import getopt, GetoptError


def main(*default_functions, **functions):
    """A wrapper to be able to call Python functions from the commandline.
    The arguments to the function is specified as options, as well as the
    chosen function. There can be at most one default function.
    """
    def exit_usage():
        print_usage_and_exit(*default_functions, **functions)

    if default_functions:
        if len(default_functions) > 1:
            exit("\nsparv.util.run.main: Only one default function, please.\n")

    # Each function is a possible commandline option:
    available_options = set(fun for fun in functions if fun is not None)

    # Each function argument is a possible commandline option:
    for fun in list(default_functions) + list(functions.values()):
        spec = inspect.getargspec(fun)
        if spec.varargs or spec.keywords:
            exit("\nsparv.util.run.main: I cannot handle functions with ** or * arguments.\n")
        for arg in spec.args:
            if arg in functions:
                exit("\nsparv.util.run.main: Function name and argument name must not be the same: %s\n" % arg)
            available_options.add(arg + "=")

    # Now read the commandline options:
    try:
        options, args_should_be_empty = getopt(sys.argv[1:], "", available_options)
    except GetoptError:
        exit_usage()
    # We don't allow extra non-option arguments:
    if args_should_be_empty:
        exit_usage()

    # Extract the option specifying the corpus:
    options = dict((opt.lstrip("-"), val) for (opt, val) in options)
    fnames = set(options) & set(functions)
    if fnames:
        fname = fnames.pop()
        del options[fname]
        if fnames or fname not in functions:
            exit_usage()
        fun = functions[fname]
    elif default_functions:
        fun = default_functions[0]
    else:
        exit_usage()

    # Check that all options are arguments to the function:
    spec = inspect.getargspec(fun)
    defaults = spec.defaults or ()
    minargs = len(spec.args) - len(defaults)
    for arg in spec.args[:minargs]:
        if arg not in options:
            exit_usage()

    # Now we can call the function:
    log.init(showpid=True)
    log.header()
    log.info("RUN: %s(%s)", fun.__name__, ", ".join("%s='%s'" % i for i in list(options.items())))
    fun(**options)
    log.statistics()
    if log.totalerrors:
        exit("\nFailure: %d error(s) occurred\n" % log.totalerrors)


def print_usage_and_exit(*default_functions, **functions):
    """Exit Python with a usage message derived from the given functions.
    """
    for fun in default_functions:
        functions[""] = fun
    module = "sparv." + os.path.splitext(os.path.basename(sys.argv[0]))[0]
    usage = "Usage:\n\n"
    for choice, fun in sorted(functions.items()):
        usage += "python -m %s" % module
        if choice:
            usage += " --%s" % choice
        spec = inspect.getargspec(fun)
        defaults = spec.defaults or ()
        minargs = len(spec.args) - len(defaults)
        for arg in spec.args[:minargs]:
            usage += " --%s %s" % (arg, arg.upper())
        for arg, default in zip(spec.args[minargs:], defaults):
            usage += " [--%s %s (default: %s)]" % (arg, arg.upper(), default)
        if spec.varargs:
            usage += " %s..." % spec.varargs
        usage += "\n\n"
        if isinstance(fun.__doc__, str) and fun.__doc__.strip():
            usage += "--> " + fun.__doc__.strip() + "\n\n"
    exit(usage)
