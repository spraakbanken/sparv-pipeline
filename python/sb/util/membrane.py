# -*- coding: utf-8 -*-

"""
Membrane: wraps a function with an expensive pre-calculation to a
server part which runs the calculation once, and serves calls
to this function. The original function is still available.
"""

from wsgiref.simple_server import make_server
from cgi import parse_qs, escape

import cPickle as pickle

from functools import partial

import sb.util as util

import os
import inspect
import urllib2
import urllib
import urlparse

import decorator

def update_tuple(t, i, new):
    """
    Updates the tuple t at index i with the value new.

    Returns the old value and the new tuple in a tuple.
    """
    tuple_list = list(t)
    old = tuple_list[i]
    tuple_list[i] = new
    return old, tuple(tuple_list)

def membrane(loader, address_arg_name):
    """
    Make a function membrane. Example:

    def expensive_square(i):
        sleep(1)
        return int(i) * int(i)

    @membrane(loader=expensive_square, address_arg_name='address')
    def calculate(k, address = None):
        k_squared = calculate.load(k)
        return "%s" % k_squared
    """

    class MembraneDecorator(object):
        """
        This class stores the loaded arguments and decorates the function
        """

        def __init__(self, orig_fun):
            self.orig_fun = orig_fun
            self.loaded = {}
            arg_names, _, _, _ = inspect.getargspec(self.orig_fun)
            self.address_ix = arg_names.index(address_arg_name)
            self.extendable = True

        def load_argument(self,*arg):
            util.log.info("Running %s(%s)", loader, arg)
            self.loaded[arg] = loader(*arg)

        def get_loaded_argument(self,*arg):
            if not arg in self.loaded:
                if self.extendable:
                    self.load_argument(*arg)
                else:
                    return None
            return self.loaded[arg]

        def set_extendable(self,flag):
            """
            Extendable means that the dictionary can grow from the
            preloaded values.
            """
            self.extendable = flag

        def __call__(self, *args_in, **kwargs):
            """
            Calls the function, on the server if address is set,
            otherwise locally.
            """

            address, args = update_tuple(args_in, self.address_ix, None)

            if address:
                util.log.info("Asking server %s", address)
                params = dict(args=args, kwargs=kwargs, client_pwd=os.getcwd())
                result = pickle.loads(urllib2.urlopen(address, pickle.dumps(params)).read())
                util.log.info("Server result: %s", result)
                return result
            else:
                util.log.info("Calling original function")
                return self.orig_fun(*args, **kwargs)

    def add_extra_methods(orig_fun):
        """
        Stores __load_argument, __set_extendable, and load in the
        function object. Uses decorator.FunctionMaker.
        """
        obj = MembraneDecorator(orig_fun)
        res = decorator.FunctionMaker.create(
            orig_fun, 'return decorated(%(signature)s)',
            dict(decorated=obj), __wrapped__=orig_fun,
            __load_argument = obj.load_argument,
            __set_extendable = obj.set_extendable,
            load = obj.get_loaded_argument)
        return res

    return add_extra_methods

def serve_membranes(hostname='localhost', port=8051, **configs):
    """
    Starts a server that serves many membranes. Their corresponding
    configurations each have a dictionary entry in configs. Example:
    serve_membranes(saldo = dict(membrane = sb.saldo.annotate,
                                 preload=['saldo.pickle'],
                                 extendable=False),
                    compound = dict(membrane = sb.compound.annotate,
                                    preload=['saldo.compound.pickle'],
                                    extendable=False))
    """

    # Preload all arguments, and set extendable settings
    for i in configs:
        mem = configs[i]
        util.log.info("%s: setting extendable to %s", i, mem['extendable'])
        mem['membrane'].__set_extendable(mem['extendable'])

        for arg in mem['preload']:
            util.log.info("%s: loading argument on %s", i, arg)
            mem['membrane'].__load_argument(arg)

    util.log.info("Preloading completed, starting server...")

    # The serve callback
    def serve(environ, start_response):
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            request_body_size = 0

        # Get the url path, remove initial and trailing /
        path_info = environ['PATH_INFO'].strip('/')

        # Corresponding function to this path, or the "first" element in config
        mem = configs.get(path_info,configs.itervalues().next())

        # Get arguments
        request_body = environ['wsgi.input'].read(request_body_size)
        params = pickle.loads(request_body)
        args = params['args']
        kwargs = params['kwargs']

        # Client's pwd is stored in the arguments too. Change to it
        client_pwd = params['client_pwd']
        os.chdir(client_pwd)

        # Run function
        response_body = pickle.dumps(mem['membrane'](*args,**kwargs))

        # Respond
        status = '200 OK'
        response_headers = [('Content-Type', 'text/plain'),
                            ('Content-Length', str(len(response_body)))]

        start_response(status, response_headers)
        return [response_body]

    # Start the server and serve forever
    make_server(hostname, int(port), serve).serve_forever()

def serve_membrane(membrane, preload,
                   hostname='localhost', port=8051, extendable=False):
    """
    Starts a server that serves only one membrane
    """

    serve_membranes(hostname, port, default=dict(membrane=membrane,
                                                 preload=preload,
                                                 extendable=extendable))
