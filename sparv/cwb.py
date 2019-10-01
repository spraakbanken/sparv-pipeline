# -*- coding: utf-8 -*-

"""
Tools for exporting, encoding and aligning corpora for Corpus Workbench.
"""

import os
from glob import glob
from collections import defaultdict
import xml.etree.cElementTree as etree
import itertools as it
import tempfile

import sparv.util as util

ALIGNDIR = "annotations/align"
UNDEF = "__UNDEF__"

CWB_ENCODING = os.environ.get("CWB_ENCODING", "utf8")
CWB_DATADIR = os.environ.get("CWB_DATADIR")
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


######################################################################
# Saving as Corpus Workbench data file

class ListWithGet(list):
    """
    Lists with a get function just like dict's.
    """
    def get(self, n, default=None):
        """
        Lookup and if the index is out of bounds return the default value.

        >>> xs = ListWithGet("abc")
        >>> xs
        ['a', 'b', 'c']
        >>> [xs.get(i, 'default_' + str(i)) for i in range(-1, 5)]
        ['default_-1', 'a', 'b', 'c', 'default_3', 'default_4']
        """
        if 0 <= n < len(self):
            return self[n]
        else:
            return default


def vrt_table(annotations_structs, annotations_columns):
    """
    Return a table suitable for printing as a vrt file from annotations.

    The structs are a pair of annotation and its parent.
    """
    structs_count = len(annotations_structs)
    parents = {}
    for annot, parent_annotation in annotations_structs:
        if parent_annotation not in parents:
            parents[parent_annotation] = util.read_annotation(parent_annotation)

    vrt = defaultdict(ListWithGet)

    for n, (annot, parent_annotation) in enumerate(annotations_structs):
        # Enumerate structural attributes, to handle attributes without values
        enumerated_struct = {
            span: [index, value, span]
            for index, (span, value)
            in enumerate(list(util.read_annotation(annot).items()), 1)
            # Must enumerate from 1, due to the use of any() later
        }
        token_annotations = (
            (word_tok, enumerated_struct.get(tok_span))
            for word_tok, tok_span
            in list(parents[parent_annotation].items())
        )
        for tok, value in token_annotations:
            if not value:
                # This happens for tokens that are outside the structural
                # attribute, such as b in "<text>a</text> b"
                value = ["", "", None]

            value[1] = "|" if value[1] == "|/|" else value[1]
            value[1] = value[1].replace("\n", " ") if value[1] else ""
            vrt[tok].append(value)

    for n, annot in enumerate(annotations_columns):
        n += structs_count
        annotation = util.read_annotation(annot)
        for key in vrt.keys():
            value = annotation.get(key, UNDEF)
            if n > structs_count:  # Any column except the first (the word)
                value = "|" if value == "|/|" else value
            vrt[key].append(value.replace("\n", " "))

    return vrt


def tokens_and_vrt(order, annotations_structs, annotations_columns):
    """
    Returns the tokens in order and the vrt table.
    """
    vrt = vrt_table(annotations_structs, annotations_columns)
    sortkey = util.read_annotation(order).get
    tokens = sorted(vrt, key=sortkey)
    return tokens, vrt


def export(format, out, order, annotations_columns, annotations_structs, text=None, fileid=None, fileids=None, valid_xml=True, columns=(), structs=(), encoding=CWB_ENCODING):
    """
    Export 'annotations' to the VRT or XML file 'out'.
    The order of the annotation keys is decided by the annotation 'order'.
    The columns to be exported are taken from 'columns', default all 'annotations'.
    The structural attributes are specified by 'structs', default no structs.
    If an attribute in 'columns' or 'structs' is "-", that annotation is skipped.
    The structs are specified by "elem:attr", giving <elem attr=N> xml tags.

    annotations_structs corresponds to vrt_struct_annotations from the Makefiles:

    Q: Brukar vi skriva vrt_struct_annotations i någon speciell ordning efter
       vilka taggar som omsluter andra?
    A: Ja, ju "större" desto längre till höger, exv `s p text`
    """
    assert format in ("vrt", "xml", "formatted"), "Wrong format specified"
    if isinstance(annotations_columns, str):
        annotations_columns = annotations_columns.split()
    if isinstance(annotations_structs, str):
        annotations_structs = [x.split(":") for x in annotations_structs.split()]

    if isinstance(columns, str):
        columns = columns.split()
    structs_count = len(structs.split())
    structs = parse_structural_attributes(structs)

    assert len(annotations_columns) == len(columns), "columns and annotations_columns must contain same number of values"
    assert len(annotations_structs) == structs_count, "structs and annotations_structs must contain same number of values"

    valid_xml = util.strtobool(valid_xml)

    if format == "formatted":
        write_formatted(out, annotations_columns, annotations_structs, columns, structs, structs_count, text)
    else:
        tokens, vrt = tokens_and_vrt(order, annotations_structs, annotations_columns)
        column_nrs = [n + structs_count for (n, col) in enumerate(columns) if col and col != "-"]

        if format == "vrt":
            write_vrt(out, structs, structs_count, column_nrs, tokens, vrt)
        elif format == "xml":
            write_xml(out, structs, structs_count, columns, column_nrs, tokens, vrt, fileid, fileids, valid_xml)


def write_formatted(out, annotations_columns, annotations_structs, columns, structs, structs_count, text):
    """
    The 'formatted' XML part of the 'export' function: export xml with the same
    whitespace and indentation as in the original.
    """
    txt, anchor2pos, pos2anchor = util.corpus.read_corpus_text(text)
    structs_order = ["__token__"] + [s[0] for s in structs]
    anchors = defaultdict(dict)
    for elem, attrs in structs:
        for attr in attrs:
            struct = util.read_annotation(annotations_structs[attr[1]][0])
            for edge in struct:
                if util.edgeStart(edge) == util.edgeEnd(edge):
                    anchors[util.edgeStart(edge)].setdefault("structs", {}).setdefault((elem, anchor2pos[util.edgeEnd(edge)], "close"), []).append((attr[0], struct[edge]))
                else:
                    anchors[util.edgeStart(edge)].setdefault("structs", {}).setdefault((elem, anchor2pos[util.edgeEnd(edge)]), []).append((attr[0], struct[edge]))
                    anchors[util.edgeEnd(edge)].setdefault("close", set()).add((elem, edge))
    for n, annot in enumerate(annotations_columns):
        n += structs_count
        for tok, value in util.read_annotation_iteritems(annot):
            if n > structs_count:  # Any column except the first (the word)
                value = "|" if value == "|/|" else value
            anchors[util.edgeStart(tok)].setdefault("token", []).append(value.replace("\n", " "))
            if n == structs_count:
                anchors[util.edgeEnd(tok)].setdefault("close", set()).add(("__token__", None))
    currpos = 0

    with open(out, "w") as OUT:
        OUT.write("<corpus>")
        for pos, anchor in sorted(list(pos2anchor.items()), key=lambda x: x[0]):
            OUT.write(txt[currpos:pos].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            if anchor in anchors:
                if "close" in anchors[anchor]:
                    if ("__token__", None) in anchors[anchor]["close"]:
                        OUT.write("</w>")
                    OUT.write("".join("</%s>" % e[0] for e in sorted(anchors[anchor]["close"], key=lambda x: structs_order.index(x[0])) if not e[0] == "__token__"))

                if "structs" in anchors[anchor]:
                    for elem, annot in sorted(iter(list(anchors[anchor]["structs"].items())), key=lambda x: (-x[0][1], -structs_order.index(x[0][0]))):
                        if elem not in ("close", "token"):
                            attrstring = "".join(' %s="%s"' % (attr, val.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))
                                                 for (attr, val) in annot if val and not attr == UNDEF)
                            close = "/" if len(elem) == 3 else ""
                            OUT.write("<%s%s%s>" % (elem[0], attrstring, close))

                if "token" in anchors[anchor]:
                    attrstring = "".join(' %s="%s"' % (columns[i + 1], a.replace("&", "&amp;").replace('"', '&quot;').replace("<", "&lt;").replace(">", "&gt;"))
                                         for i, a in enumerate(anchors[anchor]["token"][1:]) if a)
                    OUT.write("<w%s>" % attrstring)

            currpos = pos
        OUT.write("</corpus>")
    util.log.info("Exported: %s", out)


def write_vrt(out, structs, structs_count, column_nrs, tokens, vrt):
    """ The VRT part of the 'export' function: write annotations to vrt file 'out'.

    >>> with tempfile.NamedTemporaryFile() as out:
    ...     write_vrt(out.name,
    ...               **example_data().without("columns"))
    ...     print(out.read().decode("UTF-8").replace('\\t', '    '))
    <text title="Kokboken" author="Jane Oliver">
    <s>
    Ett    DT
    exempel    NN
    </s>
    <s>
    Banankaka    NN
    </s>
    </text>
    <text title="Nya kokboken" author="Jane Oliver">
    <s>
    Flambera    VB
    </s>
    </text>
    <BLANKLINE>

    >>> with tempfile.NamedTemporaryFile() as out:
    ...     write_vrt(out.name,
    ...               **example_overlapping_data().without("columns"))
    ...     print(out.read().decode("UTF-8"))
    <b>
    bold
    <i>
    bold_italic
    </b>
    italic
    </i>
    <BLANKLINE>
    """
    with open(out, "w") as OUT:
        old_attr_values = dict((elem, None) for (elem, _attrs) in structs)
        for tok in tokens:
            cols = vrt[tok]
            new_attr_values = {}
            for elem, attrs in structs:
                new_attr_values[elem] = [(attr, cols[n]) for (attr, n) in attrs if cols.get(n)]
                if old_attr_values[elem] and new_attr_values[elem] != old_attr_values[elem]:
                    print("</%s>" % elem, file=OUT)
                    old_attr_values[elem] = None

            for elem, _attrs in reversed(structs):
                if any(x[1][0] for x in new_attr_values[elem]) and new_attr_values[elem] != old_attr_values[elem]:
                    attrstring = ''.join(' %s="%s"' % (attr, val[1].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))
                                         for (attr, val) in new_attr_values[elem] if not attr == UNDEF)
                    print("<%s%s>" % (elem, attrstring), file=OUT)
                    old_attr_values[elem] = new_attr_values[elem]

            # Whitespace and / needs to be replaced for CQP parsing to work. / is only allowed in the word itself.
            line = "\t".join(cols.get(n, UNDEF).replace(" ", "_").replace("/", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if n > structs_count else cols.get(n, UNDEF).replace(" ", "_").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for n in column_nrs)
            print(remove_control_characters(line), file=OUT)

        for elem, _attrs in structs:
            if old_attr_values[elem]:
                print("</%s>" % elem, file=OUT)

    util.log.info("Exported %d tokens, %d columns, %d structs: %s", len(tokens), len(column_nrs), len(structs), out)


def write_xml(out, structs, structs_count, columns, column_nrs, tokens, vrt, fileid, fileids, valid_xml):
    """ The XML part of the 'export' function: write annotations to a valid xml file, unless valid_xml == False.

    >>> with tempfile.NamedTemporaryFile() as fileids:
    ...     util.write_annotation(fileids.name, {"fileid": "kokkonster"})
    ...     with tempfile.NamedTemporaryFile() as out:
    ...         write_xml(out.name,
    ...                   fileid="fileid",
    ...                   fileids=fileids.name,
    ...                   valid_xml=True,
    ...                   **example_data())
    ...         print(out.read().decode("UTF-8"))
    <corpus>
    <text title="Kokboken" author="Jane Oliver">
    <s>
    <w pos="DT">Ett</w>
    <w pos="NN">exempel</w>
    </s>
    <s>
    <w pos="NN">Banankaka</w>
    </s>
    </text>
    <text title="Nya kokboken" author="Jane Oliver">
    <s>
    <w pos="VB">Flambera</w>
    </s>
    </text>
    </corpus>
    <BLANKLINE>

    >>> for valid_xml in [True, False]:
    ...     print('<!-- valid_xml: ' + str(valid_xml) + ' -->')
    ...     with tempfile.NamedTemporaryFile() as fileids:
    ...         util.write_annotation(fileids.name, {"fileid": "typography"})
    ...         with tempfile.NamedTemporaryFile() as out:
    ...             write_xml(out.name,
    ...                       fileid="fileid",
    ...                       fileids=fileids.name,
    ...                       valid_xml=valid_xml,
    ...                       **example_overlapping_data())
    ...             print(out.read().decode("UTF-8"))
    <!-- valid_xml: True -->
    <corpus>
    <b>
    <w>bold</w>
    <i _overlap="typography-1">
    <w>bold_italic</w>
    </i>
    </b>
    <i _overlap="typography-1">
    <w>italic</w>
    </i>
    </corpus>
    <!-- valid_xml: False -->
    <corpus>
    <b>
    <w>bold</w>
    <i>
    <w>bold_italic</w>
    </b>
    <w>italic</w>
    </i>
    </corpus>
    <BLANKLINE>
    """

    assert fileid, "fileid not specified"
    assert fileids, "fileids not specified"

    fileid = util.read_annotation(fileids)[fileid]
    overlap = False
    open_tag_stack = []
    pending_tag_stack = []
    str_buffer = ["<corpus>"]
    elemid = 0
    elemids = {}
    invalid_str_buffer = ["<corpus>"]
    old_attr_values = dict((elem, None) for (elem, _attrs) in structs)
    for tok in tokens:
        cols = vrt[tok]
        new_attr_values = {}

        # Close tags/fix overlaps
        for elem, attrs in structs:
            new_attr_values[elem] = [(attr, cols[n]) for (attr, n) in attrs if cols.get(n)]
            if old_attr_values[elem] and new_attr_values[elem] != old_attr_values[elem]:
                if not valid_xml:
                    invalid_str_buffer.append("</%s>" % elem)

                # Check for overlap
                while elem != open_tag_stack[-1][0]:
                    overlap = True
                    # Close top stack element, remember to re-open later
                    str_buffer.append("</%s>" % open_tag_stack[-1][0])
                    pending_tag_stack.append(open_tag_stack.pop())

                # Fix pending tags
                while pending_tag_stack:
                    if elem == open_tag_stack[-1][0]:
                        str_buffer.append("</%s>" % elem)
                        open_tag_stack.pop()
                    # Re-open pending tag
                    pending_elem, attrstring = pending_tag_stack[-1]
                    if not elemids.get(pending_elem):
                        elemid += 1
                        elemids[pending_elem] = elemid
                    line = '<%s _overlap="%s-%s"%s>' % (pending_elem, fileid, elemids[pending_elem], attrstring)
                    str_buffer.append(line)
                    open_tag_stack.append(pending_tag_stack.pop())
                    old_attr_values[elem] = None

                # Close last open tag from overlap
                if elem == open_tag_stack[-1][0] and not pending_tag_stack:
                    str_buffer.append("</%s>" % elem)
                    open_tag_stack.pop()
                    old_attr_values[elem] = None
                    elemids = {}

        # Open tags
        for elem, _attrs in reversed(structs):
            if any(x[1][0] for x in new_attr_values[elem]) and new_attr_values[elem] != old_attr_values[elem]:
                attrstring = ''.join(' %s="%s"' % (attr, val[1].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))
                                     for (attr, val) in new_attr_values[elem] if val and not attr == UNDEF)
                line = "<%s%s>" % (elem, attrstring)
                str_buffer.append(line)
                old_attr_values[elem] = new_attr_values[elem]
                open_tag_stack.append((elem, attrstring))
                if not valid_xml:
                    invalid_str_buffer.append("<%s%s>" % (elem, attrstring))

        # Add word annotations
        word = cols.get(structs_count, UNDEF).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        attrstring = "".join(' %s="%s"' % (columns[n - structs_count], cols.get(n, UNDEF).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")) for n in column_nrs[1:] if cols.get(n, UNDEF) != UNDEF)

        line = "<w%s>%s</w>" % (attrstring, word)
        str_buffer.append(remove_control_characters(line))
        if not valid_xml:
            invalid_str_buffer.append(remove_control_characters(line))

    # Close remaining open tags
    if open_tag_stack:
        for elem in reversed(open_tag_stack):
            str_buffer.append("</%s>" % elem[0])
    if not valid_xml:
        for elem, _attrs in structs:
            if old_attr_values[elem]:
                invalid_str_buffer.append("</%s>" % elem)

    str_buffer.append("</corpus>")
    invalid_str_buffer.append("</corpus>")

    # Convert str_buffer list to string
    str_buffer = "\n".join(str_buffer)
    invalid_str_buffer = "\n".join(invalid_str_buffer)

    if not valid_xml:
        # Write string buffer to invalid xml file
        with open(out, "w") as OUT:
            print(invalid_str_buffer, file=OUT)
    elif not overlap:
        # Write string buffer
        with open(out, "w") as OUT:
            print(str_buffer, file=OUT)
    else:
        # Go through xml structure and add missing _overlap attributes
        xmltree = etree.ElementTree(etree.fromstring(str_buffer))
        for child in xmltree.getroot().iter():
            # If child has and id, get previous element with same tag
            if child.tag != "w" and child.attrib.get("_overlap"):
                elemlist = list(xmltree.getroot().iter(child.tag))
                if child != elemlist[0]:
                    prev_elem = elemlist[elemlist.index(child) - 1]
                    # If previous element has no id, add id of child
                    if not prev_elem.attrib.get("_overlap"):
                        prev_elem.set("_overlap", child.attrib.get("_overlap"))
        xmltree.write(out, xml_declaration=False, method="xml", encoding=util.UTF8)

    util.log.info("Exported %d tokens, %d columns, %d structs: %s", len(tokens), len(column_nrs), len(structs), out)


def combine_xml(master, out, xmlfiles="", xmlfiles_list=""):
    assert master != "", "Master not specified"
    assert out != "", "Outfile not specified"
    assert (xmlfiles or xmlfiles_list), "Missing source"

    if xmlfiles:
        if isinstance(xmlfiles, str):
            xmlfiles = xmlfiles.split()
    elif xmlfiles_list:
        with open(xmlfiles_list) as insource:
            xmlfiles = [line.strip() for line in insource]

    xmlfiles.sort()

    with open(out, "w") as OUT:
        print('<corpus id="%s">' % master.replace("&", "&amp;").replace('"', "&quot;"), file=OUT)
        for infile in xmlfiles:
            util.log.info("Read: %s", infile)
            with open(infile, "r") as IN:
                # Append everything but <corpus> and </corpus>
                print(IN.read()[9:-10], end=' ', file=OUT)
        print("</corpus>", file=OUT)
        util.log.info("Exported: %s" % out)


def cwb_encode(master, columns, structs=(), vrtdir=None, vrtfiles=None, vrtlist=None,
               encoding=CWB_ENCODING, datadir=CWB_DATADIR, registry=CORPUS_REGISTRY, skip_compression=False, skip_validation=False):
    """
    Encode a number of VRT files, by calling cwb-encode.
    params, structs describe the attributes that are exported in the VRT files.
    """
    assert master != "", "Master not specified"
    assert util.single_true((vrtdir, vrtfiles, vrtlist)), "Either VRTDIR, VRTFILES or VRTLIST must be specified"
    assert datadir, "CWB_DATADIR not specified"
    assert registry, "CORPUS_REGISTRY not specified"
    if isinstance(skip_validation, str):
        skip_validation = (skip_validation.lower() == "true")
    if isinstance(skip_compression, str):
        skip_compression = (skip_compression.lower() == "true")
    if isinstance(vrtfiles, str):
        vrtfiles = vrtfiles.split()
    if isinstance(columns, str):
        columns = columns.split()
    structs = parse_structural_attributes(structs)

    corpus_registry = os.path.join(registry, master)
    corpus_datadir = os.path.join(datadir, master)
    util.system.clear_directory(corpus_datadir)

    encode_args = ["-s", "-p", "-",
                   "-d", corpus_datadir,
                   "-R", corpus_registry,
                   "-c", encoding,
                   "-x"
                   ]
    if vrtdir:
        encode_args += ["-F", vrtdir]
    elif vrtfiles:
        for vrt in vrtfiles:
            encode_args += ["-f", vrt]

    for col in columns:
        if col != "-":
            encode_args += ["-P", col]
    for struct, attrs in structs:
        attrs2 = "+".join(attr for attr, _n in attrs if not attr == UNDEF)
        if attrs2:
            attrs2 = "+" + attrs2
        encode_args += ["-S", "%s:0%s" % (struct, attrs2)]

    if vrtlist:
        # Use xargs to avoid "Argument list too long" problems
        util.system.call_binary("cwb-encode", raw_command="cat %s | xargs cat | %%s %s" % (vrtlist, " ".join(encode_args)), verbose=True, use_shell=True)
    else:
        util.system.call_binary("cwb-encode", encode_args, verbose=True)

    index_args = ["-V", "-r", registry, master.upper()]
    util.system.call_binary("cwb-makeall", index_args, verbose=True)
    util.log.info("Encoded and indexed %d columns, %d structs", len(columns), len(structs))

    if not skip_compression:
        util.log.info("Compressing corpus files...")
        compress_args = ["-A", master.upper()]
        if skip_validation:
            compress_args.insert(0, "-T")
            util.log.info("Skipping validation")
        # Compress token stream
        util.system.call_binary("cwb-huffcode", compress_args)
        util.log.info("Removing uncompressed token stream...")
        for f in glob(os.path.join(corpus_datadir, "*.corpus")):
            os.remove(f)
        # Compress index files
        util.system.call_binary("cwb-compress-rdx", compress_args)
        util.log.info("Removing uncompressed index files...")
        for f in glob(os.path.join(corpus_datadir, "*.corpus.rev")):
            os.remove(f)
        for f in glob(os.path.join(corpus_datadir, "*.corpus.rdx")):
            os.remove(f)
        util.log.info("Compression done.")


def cwb_align(master, other, link, aligndir=ALIGNDIR):
    """
    Align 'master' corpus with 'other' corpus, using the 'link' annotation for alignment.
    """

    util.system.make_directory(aligndir)
    alignfile = os.path.join(aligndir, master + ".align")
    util.log.info("Aligning %s <-> %s", master, other)

    try:
        [(link_name, [(link_attr, _path)])] = parse_structural_attributes(link)
    except ValueError:
        raise ValueError("You have to specify exactly one alignment link.")
    link_attr = link_name + "_" + link_attr

    # Align linked chunks
    args = ["-v", "-o", alignfile, "-V", link_attr, master, other, link_name]
    result, _ = util.system.call_binary("cwb-align", args, verbose=True)
    with open(alignfile + ".result", "w") as F:
        print(result, file=F)
    _, lastline = result.rsplit("Alignment complete.", 1)
    util.log.info("%s", lastline.strip())
    if " 0 alignment" in lastline.strip():
        util.log.warning("No alignment regions created")
    util.log.info("Alignment file/result: %s/.result", alignfile)

    # Add alignment parameter to registry
    # cwb-regedit is not installed by default, so we skip it and modify the regfile directly instead:
    regfile = os.path.join(os.environ["CORPUS_REGISTRY"], master)
    with open(regfile, "r") as F:
        skip_align = ("ALIGNED %s" % other) in F.read()

    if not skip_align:
        with open(regfile, "a") as F:
            print(file=F)
            print("# Added by cwb.py", file=F)
            print("ALIGNED", other, file=F)
        util.log.info("Added alignment to registry: %s", regfile)
    # args = [master, ":add", ":a", other]
    # result, _ = util.system.call_binary("cwb-regedit", args, verbose=True)
    # util.log.info("%s", result.strip())

    # Encode the alignments into CWB
    args = ["-v", "-D", alignfile]
    result, _ = util.system.call_binary("cwb-align-encode", args, verbose=True)
    util.log.info("%s", result.strip())


def parse_structural_attributes(structural_atts):
    """
    >>> parse_structural_attributes("s - text:title text:author")
    [('s', [('__UNDEF__', 0)]), ('text', [('title', 2), ('author', 3)])]
    """

    if isinstance(structural_atts, str):
        structural_atts = structural_atts.split()
    structs = {}
    order = []
    for n, struct in enumerate(structural_atts):
        assert not struct or struct == "-" or "." not in struct, "Struct should contain ':' or be equal to '-': %s" % struct

        if ":" in struct:
            elem, attr = struct.split(":")
        else:
            elem = struct
            attr = UNDEF
        if struct and not struct == "-":
            if elem not in structs:
                structs[elem] = []
                order.append(elem)
            structs[elem].append((attr, n))
    return [(elem, structs[elem]) for elem in order]


def remove_control_characters(text):
    return text.translate(dict((ord(c), None) for c in [chr(i) for i in list(range(9)) + list(range(11, 13)) + list(range(14, 32)) + [127]]))


def vrt_iterate(tokens, vrt, trail=[0]):
    """
    Yield segments from vrt separated using the structural attributes from trail.

    >>> tokens = ["w:1", "w:2", "w:3", "w:4", "w:5"]
    >>> vrt = {
    ...     "w:1": [[1, "A", "w:1-1"], "word1", "pos1"],
    ...     "w:2": [[2, "B", "w:2-3"], "word2", "pos2"],
    ...     "w:3": [[2, "B", "w:2-3"], "word3", "pos3"],
    ...     "w:4": [[3, "B", "w:4-5"], "word4", "pos4"],
    ...     "w:5": [[3, "B", "w:4-5"], "word5", "pos5"]
    ... }
    >>> list(vrt_iterate(tokens, vrt))          # doctest: +NORMALIZE_WHITESPACE
    [(['A', 'w:1-1'], [['word1', 'pos1']]),
     (['B', 'w:2-3'], [['word2', 'pos2'], ['word3', 'pos3']]),
     (['B', 'w:4-5'], [['word4', 'pos4'], ['word5', 'pos5']])]

    >>> tokens = ['w:0','w:1','w:2','w:3','w:4','w:5']
    >>> vrt = {
    ...     'w:0': [[0, 'text:0', 'w:0-1'], [0, 's:0', 'w:0-1'], 'word0'],
    ...     'w:1': [[0, 'text:0', 'w:0-1'], [0, 's:0', 'w:0-1'], 'word1'],
    ...     'w:2': [[0, 'text:0', 'w:0-1'], [1, 's:1', 'w:1-2'], 'word2'],
    ...     'w:3': [[0, 'text:0', 'w:0-1'], [1, 's:1', 'w:1-2'], 'word3'],
    ...     'w:4': [[1, 'text:1', 'w:1-2'], [2, 's:2', 'w:2-3'], 'word4'],
    ...     'w:5': [[1, 'text:1', 'w:1-2'], [2, 's:2', 'w:2-3'], 'word5'],
    ... }
    >>> list(vrt_iterate(tokens, vrt, trail=[1]))
    ...                                         # doctest: +NORMALIZE_WHITESPACE
    [(['s:0', 'w:0-1'], [['word0'], ['word1']]),
     (['s:1', 'w:1-2'], [['word2'], ['word3']]),
     (['s:2', 'w:2-3'], [['word4'], ['word5']])]
    >>> [ (text, list(sent))
    ...   for text, sent in vrt_iterate(tokens, vrt, trail=[0,1]) ]
    ...                                         # doctest: +NORMALIZE_WHITESPACE
    [(['text:0', 'w:0-1'],
      [(['s:0', 'w:0-1'], [['word0'], ['word1']]),
       (['s:1', 'w:1-2'], [['word2'], ['word3']])]),
     (['text:1', 'w:1-2'],
      [(['s:2', 'w:2-3'], [['word4'], ['word5']])])]

    """
    cols = []
    toks = []
    for tok, next_tok in zip(tokens, it.chain(tokens[1:], (None,))):

        cols.append(vrt[tok][trail[-1] + 1:])
        toks.append(tok)

        if next_tok is None:
            next = None
        else:
            next = vrt[next_tok][trail[0]][0]

        now = vrt[tok][trail[0]][0]
        if now != next:
            if len(trail[1:]):
                yield vrt[tok][trail[0]][1:], vrt_iterate(toks, vrt, trail[1:])
            else:
                yield vrt[tok][trail[0]][1:], cols
            cols = []
            toks = []


class DictWithWithout(dict):
    """A dictionary with a without function that excludes some elements."""

    def without(self, *keys):
        """
        Return a copy of the dictionary without these keys.

        >>> DictWithWithout(apa=1, bepa=2).without("apa")
        {'bepa': 2}
        """
        return DictWithWithout(
            **{k: v for k, v in list(self.items()) if k not in keys})


def example_data():
    """Example data to test the write_* functions."""
    # Structs come in the reverse nesting order:
    structs = [["s", [[UNDEF, 0]]],
               ["text", [["title", 1], ["author", 2]]]]
    structs_count = 3
    columns = ["word", "pos"]
    column_nrs = [3, 4]
    # The names and the order of the tokens:
    tokens = ["w:1", "w:2", "w:3", "w:4"]
    vrt = {
        "w:1": ListWithGet([
            [1, ""],
            [1, "Kokboken"],
            [1, "Jane Oliver"],
            "Ett",
            "DT"
        ]),
        "w:2": ListWithGet([
            [1, ""],
            [1, "Kokboken"],
            [1, "Jane Oliver"],
            "exempel",
            "NN"
        ]),
        "w:3": ListWithGet([
            [2, ""],
            [1, "Kokboken"],
            [1, "Jane Oliver"],
            "Banankaka",
            "NN"
        ]),
        "w:4": ListWithGet([
            [3, ""],
            [2, "Nya kokboken"],
            [2, "Jane Oliver"],
            "Flambera",
            "VB"
        ])
    }
    return DictWithWithout(**locals())


def example_overlapping_data():
    """Overlapping data to test the write_* functions."""
    structs = [["b", [[UNDEF, 0]]], ["i", [[UNDEF, 1]]]]
    structs_count = 2
    columns = ["word"]
    column_nrs = [2]
    tokens = ["w:1", "w:2", "w:3"]
    vrt = {
        "w:1": ListWithGet([
            [1, ""],
            [],
            "bold"
        ]),
        "w:2": ListWithGet([
            [1, ""],
            [2, ""],
            "bold_italic"
        ]),
        "w:3": ListWithGet([
            [],
            [2, ""],
            "italic"
        ]),
    }
    return DictWithWithout(**locals())


if __name__ == "__main__":
    util.run.main(export=export,
                  encode=cwb_encode,
                  align=cwb_align,
                  combine_xml=combine_xml)
