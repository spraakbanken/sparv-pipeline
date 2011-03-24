# -*- coding: utf-8 -*-

import util

def fileid(out, files=None, filelist=None):
    assert files or filelist, "files or filelist must be specified"
    
    if filelist:
        files = open(filelist, "r").read().strip()
    files = files.split()
    files.sort()
    
    numfiles = len(files) * 2
    OUT = {}

    for f in files:
        util.resetIdent(f, numfiles)
        OUT[f] = util.mkIdent("", OUT.values())
    
    util.write_annotation(out, OUT)


if __name__ == '__main__':
    util.run.main(fileid)
