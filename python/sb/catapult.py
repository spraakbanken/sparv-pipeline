"""
catapult: runs python scripts in already running processes to
eliminate the python interpreter startup time.

Run scripts in the catapult with the c program catalaunch.
"""

from multiprocessing import Process, Queue, cpu_count

import socket
import sys
import runpy
import os
import traceback
import sys

import util

# Important to preload all modules otherwise processes will need to do
# it upon request, introducing new delays.
from sb.util import *
from sb import *

import re

# Splits at every space that is not preceded by a backslash
splitter = re.compile('(?<!\\\\) ')

def handle(client_sock, verbose):
    """
    Handle a client: parse the arguments, change to the relevant
    directory, then run the script. Stdout and stderr are directed
    to /dev/null or to the client socket.
    """

    def chunk_send(msg):
        """
        Sends a message chunk until it is totally received in the other end
        """
        while len(msg) > 0:
            sent = client_sock.send(msg)
            if sent == 0:
                raise RuntimeError("socket connection broken")
            msg = msg[sent:]

    def set_stdout_stderr():
        """
        Put stdout and stderr to the client_sock, or /dev/null if not
        verbose. Returns the clean-up handler.
        """

        class Writer(object):
            def write(self, msg):
                chunk_send(msg)

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
            """
            Restores stdout and stderr
            """
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

    # If the first argument is -m, the following argument is a module
    # name instead of a script name
    module_flag = len(args) > 2 and args[1] == '-m'

    if module_flag:
        args.pop(1)

    if len(args) > 1:

        # First argument is the pwd of the caller
        pwd = args.pop(0)

        if verbose:
            util.log.info('Running %s %s, in directory %s',
                          args[0], ' '.join(args[1:]), pwd)

        # Set stdout and stderr, which returns the cleaup function
        cleanup = set_stdout_stderr()

        # Run the command
        try:
            sys.argv = ['python']
            sys.argv.extend(args[1:])
            os.chdir(pwd)
            if module_flag:
                runpy.run_module(args[0], run_name='__main__')
            else:
                runpy.run_path(args[0], run_name='__main__')
        except (ImportError, IOError):
            # If file does not exist, send the error message
            chunk_send("%s\n" % sys.exc_info()[1])
            cleanup()
            util.log.error("%s\n" % sys.exc_info()[1])
        except:
            # Send other errors, and if verbose, send tracebacks
            chunk_send("%s\n" % sys.exc_info()[1])
            for i in xrange(2):
                traceback.print_exception(*sys.exc_info())
                i or cleanup()
            util.log.error("Error: %s\n" % sys.exc_info()[1])
        else:
            cleanup()

        if verbose:
            util.log.info('Completed %s %s', args[0], ' '.join(args[1:]))

    else:
        chunk_send('Cannot handle %s\n' % data)
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
            util.log.error('%s: Error in handling code:',
                           i, sys.exc_info()[1])
            traceback.print_exception(*sys.exc_info())

def start(socket_path, processes=1, verbose='false'):
    """
    Starts a catapult on a socket file, using a number of processes.

    If verbose is false, all stdout and stderr programs produce is
    piped to /dev/null, otherwise it is sent to the client. The
    computation is done by the catapult processes, however.
    Regardless of what verbose is, client errors should be reported
    both in the catapult and to the client.

    Start processes using catalaunch.
    """

    if os.path.exists(socket_path):
        util.log.info('socket %s already exists', socket_path)
        exit(1)

    verbose = verbose.lower() == 'true'

    util.log.info('Verbose: %s', verbose)

    # If processes does not contain an int, set it to the number of processors
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
