
from multiprocessing import Process, Queue, cpu_count
from threading import Thread

import socket
import sys
import runpy
import os
import traceback
import sys

import util
from sb.util import *
from sb import *

import re

# Splits at every space that is not preceded by a backslash
splitter = re.compile('(?<!\\\\) ')

def chunk_send(client_sock, msg):
    while len(msg) > 0:
        sent = client_sock.send(msg)
        if sent == 0:
            raise RuntimeError("socket connection broken")
        msg = msg[sent:]

def handle(client_sock, verbose):

    def set_stdout_stderr():
        """
        Put stdout and stderr to the client_sock, or /dev/null if not
        verbose. Returns the clean-up handler.
        """

        class Writer(object):
            def write(self, msg):
                chunk_send(client_sock, msg)

            def flush(self):
                pass

        # file descriptors are for output in non-python code,
        # stds are for python's own output
        orig_fds = os.dup(1), os.dup(2)
        orig_stds = sys.stdout, sys.stderr
        if verbose:
            os.dup2(client_sock.fileno(), 1)
            os.dup2(client_sock.fileno(), 2)
            w = Writer()
            sys.stdout = w
            sys.stderr = w
            null_fds = []
        else:
            null_fds = [ os.open(os.devnull, os.O_RDWR) for i in xrange(2) ]
            os.dup2(null_fds[0], 1)
            os.dup2(null_fds[1], 2)

        def cleanup():
            sys.stdout = orig_stds[0]
            sys.stderr = orig_stds[1]
            os.dup2(orig_fds[0], 1)
            os.dup2(orig_fds[1], 2)
            map(os.close,null_fds)
            client_sock.close()

        return cleanup

    # Receive data
    data = client_sock.recv(8192)
    if verbose:
        util.log.info('Received %s', data)

    # Split arguments on spaces, and replace '\ ' to ' ' and \\ to \
    args = [ arg.replace('\\ ',' ').replace('\\\\','\\')
             for arg in re.split(splitter,data) ]

    if len(args) > 2 and args[1] == '-m':

        # First argument is the pwd of the caller
        pwd = args.pop(0)

        if verbose:
            util.log.info('Running %s %s, using %s', args[1], ' '.join(args[2:]), pwd)

        cleanup = set_stdout_stderr()

        # Run the command
        try:
            sys.argv = ['python']
            sys.argv.extend(args[2:])
            os.chdir(pwd)
            runpy.run_module(args[1], run_name='__main__')
        except SystemExit:
            for i in xrange(2):
                util.log.error("%s\n" % sys.exc_info()[1])
                i or cleanup()
        except:
            for i in xrange(2):
                traceback.print_exception(*sys.exc_info())
                util.log.error("Error: %s\n" % sys.exc_info()[1])
                i or cleanup()
        else:
            cleanup()

        if verbose:
            util.log.info('Completed %s %s', args[1], ' '.join(args[2:]))

    else:
        chunk_send(client_sock, 'Cannot handle %s\n' % data)
        client_sock.close()

def worker(i, server_socket, verbose):
    """
    Workers listen to the socket server, and handles incoming requests
    """

    while 1:
        client_sock, addr = server_socket.accept()
        if verbose:
            util.log.info('%s: Handling a connection to %s', i, client_sock)
        try:
            handle(client_sock, verbose)
            client_sock.close()
        except:
            traceback.print_exception(*sys.exc_info())

def start(socket_path, processes=1, verbose=False):

    if os.path.exists(socket_path):
        util.log.info('socket %s already exists', socket_path)
        exit(1)

    # Parse arguments
    try:
        if not verbose or verbose.lower() == 'false':
            verbose = False
        else:
            verbose = True
    except:
        verbose = True

    util.log.info('Verbose: %s', verbose)

    try:
        processes = int(processes)
    except:
        processes = cpu_count()

    # Start the socket
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.bind(socket_path)
    server_socket.listen(processes)

    # Start processes-1 workers
    workers = [ Process(target=worker, args=[i+1, server_socket, verbose])
                for i in xrange(processes-1) ]

    for p in workers:
        p.start()

    # Additionally, let this thread be worker 0
    worker(0,server_socket,verbose)

if __name__ == '__main__':
    util.run.main(start)
