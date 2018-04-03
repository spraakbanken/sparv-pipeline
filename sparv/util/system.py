# -*- coding: utf-8 -*-

"""
System utilities for Språkbanken
"""
import subprocess
import sys
import os
import errno
import shutil
from . import log


def dirname(file):
    return os.path.dirname(file)


def make_directory(*path):
    dir = os.path.join(*path)
    if dir:
        try:
            os.makedirs(dir)
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                pass
            else:
                raise


def kill_process(process):
    """Kills a process, and ignores the error if it is already dead"""
    try:
        process.kill()
    except OSError as exc:
        if exc.errno == errno.ESRCH:  # No such process
            pass
        else:
            raise


def clear_directory(dir):
    shutil.rmtree(dir, ignore_errors=True)
    make_directory(dir)


def call_java(jar, arguments, options=[], stdin="", search_paths=(),
              encoding=None, verbose=False, return_command=False):
    """Call java with a jar file, command line arguments and stdin.
    Returns a pair (stdout, stderr).
    If the verbose flag is True, pipes all stderr output to stderr,
    and an empty string is returned as the stderr component.

    *** for maltparser: ***
    If return_command is set, then the process is returned.
    """
    assert isinstance(arguments, (list, tuple))
    assert isinstance(options, (list, tuple))
    jarfile = find_binary(jar, search_paths, executable=False)
    # For WSD: use = instead of space in arguments
    # TODO: Remove when fixed!
    if isinstance(arguments[0], tuple):
        arguments = [x + "=" + y for x, y in arguments]
    java_args = list(options) + ["-jar", jarfile] + list(arguments)
    return call_binary("java", arguments=java_args, stdin=stdin,
                       search_paths=search_paths, encoding=encoding,
                       verbose=verbose, return_command=return_command)


def call_binary(name, arguments=(), stdin="", raw_command=None, search_paths=(),
                binary_names=(), encoding=None, verbose=False,
                use_shell=False, return_command=False):
    """
    Call a binary with arguments and stdin, return a pair (stdout, stderr).
    If the verbose flag is True, pipes all stderr output to stderr,
    and an empty string is returned as the stderr component.

    *** for maltparser: ***
    If return_command is set, then the process is returned.
    """
    from . import unicode_convert
    from subprocess import Popen, PIPE
    assert isinstance(arguments, (list, tuple))
    assert isinstance(stdin, (str, list, tuple))

    binary = find_binary(name, search_paths, binary_names)
    if raw_command:
        use_shell = True
        command = raw_command % binary
        if arguments:
            command = " ".join([command] + arguments)
    else:
        command = [binary] + list(arguments)
    if isinstance(stdin, (list, tuple)):
        stdin = "\n".join(stdin)
    if encoding is not None and isinstance(stdin, str):
        stdin = unicode_convert.encode(stdin, encoding)
    log.info("CALL: %s", " ".join(command) if not raw_command else command)
    command = Popen(command, shell=use_shell,
                    stdin=PIPE, stdout=PIPE,
                    stderr=(None if verbose else PIPE),
                    close_fds=False)
    if return_command:
        return command
    else:
        stdout, stderr = command.communicate(stdin)
        if command.returncode:
            if stdout:
                print(stdout)
            if stderr:
                print(stderr, file=sys.stderr)
            raise OSError("%s returned error code %d" % (binary, command.returncode))
        if encoding:
            stdout = stdout.decode(encoding)
            if stderr:
                stderr = stderr.decode(encoding)
        return stdout, stderr


def find_binary(name, search_paths=(), binary_names=(), executable=True):
    """
    Search for the binary for a program. Stolen and modified from NLTK.
    """
    assert isinstance(name, str)
    assert isinstance(search_paths, (list, tuple))
    assert isinstance(binary_names, (list, tuple))

    search_paths = list(search_paths) + ['.'] + os.getenv("PATH").split(":")
    search_paths = list(map(os.path.expanduser, search_paths))

    if not binary_names:
        binary_names = [name]

    for directory in search_paths:
        for binary in binary_names:
            path_to_bin = os.path.join(directory, binary)
            if os.path.isfile(path_to_bin):
                if executable:
                    assert os.access(path_to_bin, os.X_OK), "Binary is not executable: %s" % path_to_bin
                return path_to_bin

    raise LookupError("Couldn't find binary: %s\nSearched in: %s\nFor binary names: %s" %
                      (name, ", ".join(search_paths), ", ".join(binary_names)))


def rsync(local, host, remote=None):
    """ Transfer files and/or directories using rsync.
    When syncing directories, extraneous files in destination dirs are deleted.
    """
    if remote is None:
        remote = local
    if os.path.isdir(local):
        remote_dir = os.path.dirname(remote)
        log.info("Copying directory: %s => %s", local, remote)
        args = ["--recursive", "--delete", "%s/" % local]
    else:
        remote_dir = os.path.dirname(remote)
        log.info("Copying file: %s => %s", local, remote)
        args = [local]
    subprocess.check_call(["ssh", host, "mkdir -p '%s'" % remote_dir])
    subprocess.check_call(["rsync"] + args + ["%s:%s" % (host, remote)])
