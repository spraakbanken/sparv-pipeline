
"""
The Sparv Pipeline testsuite. It does these two things:

1. Looks for test.yaml files under tests/ and runs the commands in there.

   The yaml file is either one single command or a list of them.
   If a list item is a dictionary with the key clean, it runs cleanly
   and is allowed to fail. Example:

       - clean: make distclean
       - make export

   (Commands are run in the order they are written.)

   Then all files prefixed with goal_ are compared with the corresponding
   unprefixed file. We have a success only when they match exactly.
   Directories can be prefixed with goal_ and then all immediate files are
   compared to the same in the unprefixed directory. Example:

       $ find
       ./export/corpus1.xml
       ./export/corpus2.xml
       ./goal_export/corpus1.xml
       ./goal_export/corpus2.xml
       ./goal_stdout
       ./stderr
       ./stdout

   Here these pairs must have a non-empty diff:

       export/corpus1.xml and goal_export/corpus1.xml,
       export/corpus2.xml and goal_export/corpus2.xml,
       stdout and goal_stdout

   We do no checks for stderr since there is no goal_stderr file.

2. Runs all doctests in the python/ directory.

Not implemented yet:
    * Code coverage statistics
    * Tests with expected failure
    * --clean does not remove .diff files

Flags:
    -h          Show help
    -v, -v11    Verbose and even more verbose
    --clean     Only run the clean parts, and remove stdout/stderr files
    --models    Remake correct revision in the models directory
    PATH..      Paths to look for test.yaml instead of tests/
                Use this if you only want to run some test.
"""

# from __future__ import print_function
from subprocess import STDOUT, call
from contextlib import contextmanager
from os import path
import os
import sys
import yaml
import doctest
import importlib


@contextmanager
def cd(dir):
    """
    Change directory to dir and restore it to the initial one when done.
    """
    old = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(old)


def partition(xs):
    """
    Values tagged True are right, those tagged False are left.

    >>> partition([(True, 1), (False, 2), (True, 3)])
    ([2], [1, 3])
    """
    left, right = [], []
    for b, x in xs:
        if b:
            right.append(x)
        else:
            left.append(x)
    return left, right


def indent(lines_or_str, indent_str='  ', join=True):
    """
    Increase the indentation of a string or a list of lines.

    >>> print(indent(['ab','cd']))
      ab
      cd
    >>> print(indent('ab'+chr(10)+'cd'))
      ab
      cd
    >>> indent(['ab','cd'], join=False)
    ['  ab', '  cd']
    """
    if isinstance(lines_or_str, str):
        lines = lines_or_str.split('\n')
    else:
        lines = lines_or_str
    indented = (indent_str + line.rstrip() for line in lines)
    if join:
        return '\n'.join(indented)
    else:
        return list(indented)


def run_test(test_dir, verbose, cleanup=False):
    """
    Runs the test expressed in test.yaml in this directory.

    Returns an info tuple (bad, good) where bad is empty if test succeeded.
    """
    try:
        with open(path.join(test_dir, 'test.yaml'), 'r') as y:
            lines = yaml.load(y)
    except Exception as e:
        return ['Error when loading test.yaml:', str(e)], []

    if not isinstance(lines, list):
        lines = [lines]

    ###
    # Run all commands:

    run = []

    seen = set()
    def rm_if_unseen(filename):
        if filename not in seen:
            if os.path.exists(filename):
                os.remove(filename)
        seen.add(filename)
        return filename

    for line in lines:
        if isinstance(line, dict) and 'clean' in line:
            clean = True
            cmd = line['clean']
        else:
            clean = False
            cmd = line

        if not isinstance(cmd, str):
            return ['Invalid cmd in test.yaml:', str(cmd)], []

        prefix = 'clean_' if clean else ''
        stdout = path.join(test_dir, prefix + 'stdout')
        stderr = path.join(test_dir, prefix + 'stderr')
        if cleanup and not clean:
            exc = 0
        else:
            with open(rm_if_unseen(stdout), 'a') as out:
                with open(rm_if_unseen(stderr), 'a') as err:
                    for fd in [out, err]:
                        fd.write('>>> ' + cmd + '\n')
                        fd.flush()
                    with cd(test_dir):
                        run.append(cmd)
                        exc = call(cmd, stdout=out, stderr=err, shell=True)

        if exc != 0 and not clean:
            info = [cmd + ' failed (exit code: ' + str(exc) + ')']
            for f in [stdout, stderr]:
                with open(f, 'r') as fd:
                    info.append(f + '[-8:]:')
                    info.extend(indent(fd.readlines()[-8:], join=False))
            return info, []

        if cleanup:
            for f in [stdout, stderr]:
                if os.path.exists(f):
                    os.remove(f)
            continue


    if cleanup:
        return [], run

    ###
    # All commands run, check the diffs with goal_ files and directories:

    return partition(check_goal_diffs(test_dir, verbose=verbose))


def capture(cmd, filename):
    """
    Capture stdout and stderr of a system call.

    Returns the exit code, the file name of the captured output and
    a callback that returns the captured output.

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile() as tmp:
    ...     exc, name, contents = capture(['echo', '-n', 'mu'], tmp.name)
    ...     (exc, name == tmp.name, contents())
    (0, True, 'mu')
    """
    with open(filename, 'w') as fd:
        exc = call(cmd, stdout=fd, stderr=STDOUT)
    def lazy_contents():
        with open(filename, 'r') as fd:
            return fd.read()
    return exc, filename, lazy_contents


def match(goal, built, verbose):
    """
    Check that contents of the files are identical.
    """
    if not path.exists(built):
        return False, built + ' was not built (required by ' + goal + ')'
    exc, diff_file, diff = capture(['diff', built, goal], built + '.diff')
    if exc != 0:
        _, word_diff_file, word_diff = capture(
            ['git', 'diff', '--word-diff=color', '--no-index', built, goal],
            built + '.word.diff')
        msg = built + ' != ' + goal + '\n' + diff_file + '\n' + word_diff_file
        if verbose:
            for contents in [diff, word_diff]:
                msg += '\n' + indent(contents())
        return False, msg
    else:
        return True, built + ' == ' + goal


def goal_(s):
    """
    Removes the goal_ prefix the last part of a path.

    >>> goal_('test/example/goal_stdout')
    'test/example/stdout'
    """
    a, b = path.split(s)
    return path.join(a, b[len('goal_'):])


def check_goal_diffs(test_dir, verbose):
    """
    Checks that files starting with goal_ match those without the prefix,
    and same for files immediately under directories with the goal_ prefix.
    """
    for dir, _, files in os.walk(test_dir):
        if path.split(dir)[1].startswith('goal_'):
            for filename in files:
                yield match(path.join(dir, filename),
                            path.join(goal_(dir), filename),
                            verbose=verbose)
        for filename in files:
            if filename.startswith('goal_'):
                yield match(path.join(dir, filename),
                            path.join(dir, goal_(filename)),
                            verbose=verbose)


def dirs_with_test_yaml(dirs):
    """
    Returns the subdirectories that has a test.yaml file.
    """
    for root in dirs or ['tests/']:
        for dir, subdirs, files in os.walk(root):
            if 'test.yaml' in files:
                yield dir


def run_tests(dirs, verbose=False, cleanup=False):
    """
    Runs all tests in the directories in dirs.

    Returns a stream of booleans answering "Success?".
    """
    for dir in dirs:
        if verbose:
            print(dir)
        errors, checked = run_test(dir, verbose=verbose, cleanup=cleanup)
        if errors:
            print('fail: ' + dir)
            print(indent(list(map(indent, errors))))
            yield False
        else:
            n = str(len(checked))
            if cleanup:
                print('pass: ' + dir + ' (cleanups executed: ' + n + ')')
            else:
                print('pass: ' + dir + ' (files without diff: ' + n + ')')
            if verbose:
                print(indent(checked))
            yield True


def pyfiles():
    """
    Returns the stream of .py files reachable from the current directory.
    """
    for dir, _, files in os.walk('.'):
        for f in files:
            if f.endswith('.py'):
                name = path.join(dir, f)
                if name.startswith('./'):
                    yield name[2:]
                else:
                    yield name


def doctests(sb_python_path, verbose):
    with cd(sb_python_path):
        sys.path.append(os.getcwd())
        no_doctests = []
        imp_error = []
        for f in pyfiles():
            try:
                name = path.splitext(f)[0].replace('/', '.')
                module = importlib.import_module(name)
                failed, attempted = doctest.testmod(module)
                if failed:
                    print('fail: ' + name)
                    yield False
                elif attempted:
                    print('pass: ' + name + ' (' + str(attempted) + ' tests)')
                    yield True
                else:
                    no_doctests.append(name)
            except ImportError as e:
                imp_error.append(name)
        if verbose:
            print('No doctests:\n' + indent(no_doctests))
            print('Import error:\n' + indent(imp_error))


def flag(x):
    """
    Iff x is an element in the argument list, remove it and return True.
    """
    if x in sys.argv:
        sys.argv.remove(x)
        return True
    else:
        return False


def main():
    if flag('-h') or flag('--help'):
        print(sys.argv[0], '[-v] [-v11] [PATH..]')
        print(sys.modules[__name__].__doc__)
        sys.exit(0)

    super_verbose = flag('-v11')
    verbose = super_verbose or flag('-v')

    cwd = os.getcwd()
    sb_python_path = path.join(cwd, 'python')
    os.environ['PYTHONPATH'] = sb_python_path
    os.environ['SPARV_MODELS'] = path.join(cwd, 'models')
    os.environ['PATH'] += ':' + path.join(cwd, 'bin')
    os.environ['python'] = os.environ.get('python', 'python3')
    # os.environ['python'] = "../venv/bin/python3"

    if flag('--models'):
        revision = '{2017-03-01}'
        print('Calling make in models/ with svn --revision ' + revision)
        cmd = 'make -C models all -B -j4 revision=' + revision
        sys.exit(call(cmd.split(), stdout=sys.stdout, stderr=sys.stderr))

    if flag('--clean'):
        ok = all(run_tests(dirs_with_test_yaml(sys.argv[1:]),
                           verbose=verbose, cleanup=True))
        sys.exit(0 if ok else -1)

    # Doctest this very file
    ok = [0 == doctest.testmod(verbose=super_verbose).failed]
    # Doctest all sb python scripts
    ok += list(doctests(sb_python_path, verbose=super_verbose))
    # Unit-test tests/ or from paths given by args
    ok += list(run_tests(dirs_with_test_yaml(sys.argv[1:]), verbose=verbose))
    if not all(ok):
        print('*** test suite failed.')
        sys.exit(-1)


if __name__ == '__main__':
    main()
