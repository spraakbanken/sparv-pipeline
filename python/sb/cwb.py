# -*- coding: utf-8 -*-

"""
Tools for exporting, encoding and aligning corpora for Corpus Workbench.
"""

import os
import re
from glob import glob

import util

ALIGNDIR = "tmp/align"
UNDEF = "__UNDEF__"

CWB_ENCODING = os.environ.get("CWB_ENCODING", "utf8")
CWB_DATADIR = os.environ.get("CWB_DATADIR")
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


######################################################################
# Saving as Corpus Workbench data file

def export_to_vrt(out, order, annotations, encoding=CWB_ENCODING):
    if isinstance(annotations, basestring):
        annotations = annotations.split()
    from collections import defaultdict
    vrt = defaultdict(dict)
    for n, annot in enumerate(annotations):
        for key, value in util.read_annotation_iteritems(annot):
            vrt[key][n] = value or UNDEF
    sortkey = util.read_annotation(order).get
    rows = sorted(vrt, key=sortkey)
    cols = range(len(annotations))
    with open(out, "w") as OUT:
        for key in rows:
            line = [vrt[key].get(n, UNDEF) for n in cols]
            print >>OUT, "\t".join(line).encode(encoding)
    util.log.info("Exported %d rows, %d columns: %s", len(rows), len(cols), out)


def insert_structural_tags(vrt, out, structs, encoding=CWB_ENCODING):
    structs = parse_structural_attributes(structs)
    with open(vrt) as VRT:
        with open(out, "w") as OUT:
            old_attr_values = dict((elem, None) for (elem, _attrs) in structs)
            for line in VRT:
                line = line.rstrip("\n\r")
                cols = line.split("\t")
                new_attr_values = {}
                for elem, attrs in structs:
                    new_attr_values[elem] = ''.join(' %s="%s"' % (attr, cols[n])
                                                    for (attr, n) in attrs
                                                    if cols[n] and cols[n] != UNDEF)
                    if old_attr_values[elem] and new_attr_values[elem] != old_attr_values[elem]:
                        print >>OUT, "</%s>" % elem
                        old_attr_values[elem] = None
                for elem, _attrs in reversed(structs):
                    if new_attr_values[elem] and new_attr_values[elem] != old_attr_values[elem]:
                        print >>OUT, "<%s%s>" % (elem, new_attr_values[elem])
                        old_attr_values[elem] = new_attr_values[elem]
                print >>OUT, line
            for elem, _attrs in structs:
                if old_attr_values[elem]:
                    print >>OUT, "</%s>" % elem
    util.log.info("Exported %d structural attrs: %s", len(structs), out)


def finalize(master, columns, structs, vrtdir=None, vrtfiles=None,
             encoding=CWB_ENCODING, datadir=CWB_DATADIR, registry=CORPUS_REGISTRY):
    """
    Encode a number of VRT files, by calling cwb-encode.
    params, structs describe the attributes that are exported in the VRT files.
    """
    assert bool(vrtdir) != bool(vrtfiles), "Either VRTDIR or VRTFILES must be specified"
    if isinstance(vrtfiles, basestring): vrtfiles = vrtfiles.split()
    if isinstance(columns, basestring): columns = columns.split()
    structs = parse_structural_attributes(structs)

    corpus_registry = os.path.join(registry, master)
    corpus_datadir = os.path.join(datadir, master)
    util.system.clear_directory(corpus_datadir)
    
    encode_args = ["-s", "-p", "-",
                   "-d", corpus_datadir,
                   "-R", corpus_registry,
                   "-c", encoding,
                   ]
    if vrtdir:
        encode_args += ["-F", vrtdir]
    if vrtfiles:
        for vrt in vrtfiles:
            encode_args += ["-f", vrt]
    for col in columns:
        encode_args += ["-P", col]
    for struct, attrs in structs:
        encode_args += ["-S", "%s:0+%s" % (struct, "+".join(attr for attr, _n in attrs))]
    util.system.call_binary("cwb-encode", encode_args, verbose=True)

    index_args = ["-V", "-r", registry, master.upper()]
    util.system.call_binary("cwb-makeall", index_args, verbose=True)
    util.log.info("Encoded and indexed %d columns, %d structs", len(columns), len(structs))


def align(master, other, link, aligndir=ALIGNDIR):
    """
    Align 'master' corpus with 'other' corpus, using the 'link' annotation for alignment.
    """

    util.system.make_directory(aligndir)
    alignfile = os.path.join(aligndir, master + ".align")
    util.log.info("Aligning %s <-> %s", master, other)

    try:
        [(link_name, [(link_attr, _path)])] = parse_structural(link)
    except ValueError:
        raise ValueError("You have to specify exactly one alignment link.")
    link_attr = link_name + "_" + link_attr

    # align linked chunks
    args = ["-v", "-o", alignfile, "-V", link_attr, master, other, link_name]
    result, _ = util.system.call_binary("cwb-align", args, verbose=True)
    with open(alignfile + ".result", "w") as F:
        print >>F, result
    _, lastline = result.rsplit("Alignment complete.", 1)
    util.log.info("%s", lastline.strip())
    util.log.info("Alignment file/result: %s/.result", alignfile)

    # add alignment parameter to registry
    # cwb-regedit is not installed by default, so we skip it and modify the regfile directly instead:
    regfile = os.path.join(os.environ["CORPUS_REGISTRY"], master)
    with open(regfile, "a") as F:
        print >>F
        print >>F, "# Added by cwb.py"
        print >>F, "ALIGNED", other
    util.log.info("Added alignment to registry: %s", regfile)
    # args = [master, ":add", ":a", other]
    # result, _ = util.system.call_binary("cwb-regedit", args, verbose=True)
    # util.log.info("%s", result.strip())

    # encode the alignments into CWB
    args = ["-v", "-D", alignfile]
    result, _ = util.system.call_binary("cwb-align-encode", args, verbose=True)
    util.log.info("%s", result.strip())


def parse_structural_attributes(structural_atts):
    if isinstance(structural_atts, basestring):
        structural_atts = structural_atts.split()
    structs = {}
    order = []
    for n, struct in enumerate(structural_atts):
        if ":" in struct:
            elem, attr = struct.split(":")
            if elem not in structs:
                structs[elem] = []
                order.append(elem)
            structs[elem].append((attr, n))
        else:
            assert not struct or struct=="-", "Struct should contain ':' or be equal to '-': %s" % struct
    return [(elem, structs[elem]) for elem in order]


if __name__ == '__main__':
    util.run.main(export=export_to_vrt,
                  insert_structs=insert_structural_tags,
                  finalize=finalize,
                  align=align)

