# -*- coding: utf-8 -*-
import sparv.util as util


def fileid(out, files=None, filelist=None, prefix=""):
    """Creates unique IDs for every file in a list, using the filenames as seed.
    The resulting IDs are written to the file specified by 'out'."""

    assert files or filelist, "files or filelist must be specified"

    if filelist:
        with open(filelist, "r") as f:
            files = f.read().strip()

    files = files.split()
    files.sort()

    numfiles = len(files) * 2
    OUT = {}

    for f in files:
        util.resetIdent(f, numfiles)
        OUT[f] = prefix + util.mkIdent("", list(OUT.values()))

    util.write_annotation(out, OUT)


def add(out, fileids, files=None, filelist=None, prefix=""):
    """ Adds IDs for new files to an existing list of file IDs, and removes missing ones. """

    assert files or filelist, "files or filelist must be specified"

    if filelist:
        with open(filelist, "r") as f:
            files = f.read().strip()

    files = files.split()
    files.sort()

    OUT = util.read_annotation(fileids)
    numfiles = (len(files) + len(OUT)) * 2

    # Add new files
    for f in files:
        if f not in OUT:
            util.resetIdent(f, numfiles)
            OUT[f] = prefix + util.mkIdent("", list(OUT.values()))
            util.log.info("File %s added.", f)

    # Remove deleted files
    todelete = []
    for f in OUT:
        if f not in files:
            todelete.append(f)
            util.log.info("File %s removed.", f)

    for f in todelete:
        del OUT[f]

    util.write_annotation(out, OUT)


if __name__ == '__main__':
    util.run.main(fileid,
                  add=add)
