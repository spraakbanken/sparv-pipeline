"""
Testing the membrane library
"""

import sb.util as util
import itertools
import os

from time import sleep

from sb.util.membrane import membrane, serve_membrane, serve_membranes

def expensive_square(i):
    """Today, squaring is super-expensive!"""
    util.log.info("Squaring %s", i)
    sleep(0.1)
    return i ** 2

@membrane(loader=expensive_square, address_arg_name='address')
def square(i, address=None):
    """
    A square version which uses a membrane, which can store loaded
    expensive squares either locally or on a server.

    If a server is used, then the whole computation will take place on
    the server, including IO, but the result is returned.
    (must be pickleable)

    Use the method load on current function to get the stored values.
    """
    i_squared = square.load(i)
    util.log.info("%s squared is %s", i, i_squared)
    return i_squared

def square_test(i, address=None):
    """
    Runs the square function, and prints the result
    """
    i_squared = square(int(i), address)
    util.log.info("%s squared is %s", i, i_squared)

def square_server(value, width=None, hostname='localhost', port=8051, extendable='false'):
    """
    Starts a server which serves the square function. It preloads value, plus
    up to width extra values. If extendable is set, then the server allows
    calculating values.
    """
    extendable = extendable.lower() == 'true'

    value = int(value)
    if width:
        width = int(width)
    else:
        width = 1

    preload_values = range(value, value + width)
    serve_membrane(square, preload_values, hostname, port, extendable)

def my_sum(args):
    """Sums and logs"""
    util.log.info("Summing %s", args)
    return sum(args)

@membrane(loader=my_sum, address_arg_name='address')
def fancy_arguments(address=None, *args, **kwargs):
    """
    Membranes also support variadic functions.
    """

    args_summed = fancy_arguments.load(args)

    util.log.info("%s summed is %s", args, args_summed)

    extra_args = len(kwargs)

    util.log.info("You supplied %s extra arguments", extra_args)

    return args_summed, extra_args

def multiserve(hostname='localhost', port=8051):
    """
    Starts a server serving the square function and fancy arguments function
    """
    serve_membranes(hostname, port,
                    square=dict(membrane=square, preload=range(0,10), extendable=True),
                    fancy_arguments=dict(membrane=fancy_arguments, preload=[], extendable=True),
                    print_cwd=dict(membrane=print_cwd_mem, preload=[], extendable=False))

def fancy_arguments_test(lower, upper, name, address=None):
    """
    Runs fancy_arguments with argument address, then as *args range(lower,upper) and
    as **kwargs a dictionary with chars from the name as keys.
    """
    numbers = range(int(lower), int(upper))
    name_dict = dict(zip(name,itertools.count(0)))

    summed, length = fancy_arguments(address, *numbers, **name_dict)

    util.log.info("sum: %s and %s contains %s unique characters", summed, name, length)

@membrane(loader=None, address_arg_name='address')
def print_cwd_mem(address=None):
    cwd = os.getcwd()
    util.log.info("membrane cwd: %s", cwd)
    return cwd

def print_cwd(address=None):
    cwd = print_cwd_mem(address)
    util.log.info("server cwd: %s", cwd)
    util.log.info("local cwd: %s", os.getcwd())
    return cwd

if __name__ == '__main__':
    util.run.main(square_server = square_server, square_test = square_test,
                  multiserve = multiserve, fancy_arguments_test = fancy_arguments_test,
                  print_cwd = print_cwd)
