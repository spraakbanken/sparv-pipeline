# -*- coding: utf-8 -*-

"""
Tools for exporting, encoding and aligning corpora for Corpus Workbench.
"""

import os
#from tempfile import TemporaryFile
from glob import glob
from collections import defaultdict, Counter
import xml.etree.cElementTree as etree
import tempfile
import itertools as it

import util

ALIGNDIR = "annotations/align"
UNDEF = u"__UNDEF__"

CWB_ENCODING = os.environ.get("CWB_ENCODING", "utf8")
CWB_DATADIR = os.environ.get("CWB_DATADIR")
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


######################################################################
# Saving as Corpus Workbench data file

def chain(annotations, default=None):
    """Create a functional composition of a list of annotations.
    E.g., token.sentence + sentence.id -> token.sentence-id

    >>> from pprint import pprint
    >>> pprint(
    ...   chain([{"w:1": "s:A",
    ...           "w:2": "s:A",
    ...           "w:3": "s:B",
    ...           "w:4": "s:C",
    ...           "w:5": "s:missing"},
    ...          {"s:A": "text:I",
    ...           "s:B": "text:II",
    ...           "s:C": "text:mystery"},
    ...          {"text:I": "The Bible",
    ...           "text:II": "The Samannaphala Sutta"}],
    ...         default="The Principia Discordia"))
    {'w:1': 'The Bible',
     'w:2': 'The Bible',
     'w:3': 'The Samannaphala Sutta',
     'w:4': 'The Principia Discordia',
     'w:5': 'The Principia Discordia'}
    """
    def follow(key):
        for annot in annotations:
            try:
                key = annot[key]
            except KeyError:
                return default
        return key
    return dict((key, follow(key)) for key in annotations[0])


class ListWithGet(list):
    """
    Lists with a get function just like dict's.
    """
    def get(self, n, default=None):
        """
        Lookup and if the index is out of bounds return the default value.

        >>> xs = ListWithGet('abc')
        >>> xs
        ['a', 'b', 'c']
        >>> [ xs.get(i, 'default_'+str(i)) for i in range(-1,5) ]
        ['default_-1', 'a', 'b', 'c', 'default_3', 'default_4']
        """
        if n >= 0 and n < len(self):
            return self[n]
        else:
            return default


def vrt_table(annotations_structs, annotations_columns):
    """
    Returns a table suitable for printing as a vrt file from annotations.

    The structs are a pair of annotation and its parent.
    """
    structs_count = len(annotations_structs)
    parents = {}
    for annot, parent_annotation in annotations_structs:
        if not parent_annotation in parents:
            parents[parent_annotation] = util.read_annotation(parent_annotation)

    vrt = defaultdict(ListWithGet)

    for n, annot in enumerate(annotations_structs):
        # Enumerate structural attributes, to handle attributes without values
        enumerated_struct = dict(
            (item[0], [i, item[1]])
            for i, item in enumerate(util.read_annotation(annot[0]).items(), 1))
                          # Must enumerate from 1, due to the use of any() later
        token_annotations = chain([parents[annot[1]], enumerated_struct])
        for tok, value in token_annotations.iteritems():
            if not value:
                value = ["", ""]

            value[1] = "|" if value[1] == "|/|" else value[1]
            value[1] = value[1].replace("\n", " ") if value[1] else ""
            vrt[tok].append(value)

    for n, annot in enumerate(annotations_columns):
        n += structs_count
        for tok, value in util.read_annotation_iteritems(annot):
            if n > structs_count:  # Any column except the first (the word)
                value = "|" if value == "|/|" else value
            vrt[tok].append(value.replace("\n", " "))

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
    """
    assert format in ("vrt", "xml", "txt", "formatted"), "Wrong format specified"
    if isinstance(annotations_columns, basestring):
        annotations_columns = annotations_columns.split()
    if isinstance(annotations_structs, basestring):
        annotations_structs = [x.split(":") for x in annotations_structs.split()]

    if format == "txt":
        assert len(columns) == 0 == len(structs), "columns and structs should be empty with txt output, use the annotations arguments instead"
        assert len(annotations_columns) <= 1, "use zero columns for label output, one column for token output"
        assert len(annotations_structs) == 1, "use one structural attribute"
        structs_count = 1
    else:
        if isinstance(columns, basestring):
            columns = columns.split()
        structs_count = len(structs.split())
        structs = parse_structural_attributes(structs)

        assert len(annotations_columns) == len(columns), "columns and annotations_columns must contain same number of values"
        assert len(annotations_structs) == structs_count, "structs and annotations_structs must contain same number of values"

    valid_xml = util.strtobool(valid_xml)

    if format == "formatted":
        write_formatted(out, annotations_columns, annotations_structs, columns, structs, structs_count, text, encoding)
    else:
        tokens, vrt = tokens_and_vrt(order, annotations_structs, annotations_columns)
        column_nrs = [n+structs_count for (n, col) in enumerate(columns) if col and col != "-"]

        if format == "vrt":
            write_vrt(out, structs, structs_count, column_nrs, tokens, vrt, encoding)
        elif format == "txt":
            if len(annotations_columns) == 1:
                write_words(out, tokens, vrt)
            else:
                write_labels(out, tokens, vrt)
        elif format == "xml":
            write_xml(out, structs, structs_count, columns, column_nrs, tokens, vrt, fileid, fileids, valid_xml, encoding)


def write_formatted(out, annotations_columns, annotations_structs, columns, structs, structs_count, text, encoding):
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
        for pos, anchor in sorted(pos2anchor.items(), key=lambda x: x[0]):
            OUT.write(txt[currpos:pos].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").encode(encoding))
            if anchor in anchors:
                if "close" in anchors[anchor]:
                    if ("__token__", None) in anchors[anchor]["close"]:
                        OUT.write("</w>")
                    OUT.write(''.join('</%s>' % e[0] for e in sorted(anchors[anchor]["close"], key=lambda x: structs_order.index(x[0])) if not e[0] == "__token__").encode(encoding))

                if "structs" in anchors[anchor]:
                    for elem, annot in sorted(anchors[anchor]["structs"].iteritems(), key=lambda x: (-x[0][1], -structs_order.index(x[0][0]))):
                        if not elem in ("close", "token"):
                            attrstring = ''.join(' %s="%s"' % (attr, val.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))
                                                 for (attr, val) in annot if val and not attr == UNDEF).encode(encoding)
                            close = "/" if len(elem) == 3 else ""
                            OUT.write("<%s%s%s>" % (elem[0].encode(encoding), attrstring, close))

                if "token" in anchors[anchor]:
                    attrstring = "".join(' %s="%s"' % (columns[i + 1], a.replace("&", "&amp;").replace('"', '&quot;').replace("<", "&lt;").replace(">", "&gt;"))
                                         for i, a in enumerate(anchors[anchor]["token"][1:]) if a).encode(encoding)
                    OUT.write("<w%s>" % attrstring)

            currpos = pos
        OUT.write("</corpus>")
    util.log.info("Exported: %s", out)


def write_vrt(out, structs, structs_count, column_nrs, tokens, vrt, encoding):
    """ The VRT part of the 'export' function: write annotations to vrt file 'out'.

    >>> with tempfile.NamedTemporaryFile() as out:
    ...     write_vrt(out.name,
    ...               encoding="utf8",
    ...               **example_data().without("columns"))
    ...     print(out.read().replace('\\t','    '))
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
    ...               encoding="utf8",
    ...               **example_overlapping_data().without("columns"))
    ...     print(out.read())
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
                    print >>OUT, "</%s>" % elem.encode(encoding)
                    old_attr_values[elem] = None

            for elem, _attrs in reversed(structs):
                if any(x[1][0] for x in new_attr_values[elem]) and new_attr_values[elem] != old_attr_values[elem]:
                    attrstring = ''.join(' %s="%s"' % (attr, val[1].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))
                                         for (attr, val) in new_attr_values[elem] if not attr == UNDEF).encode(encoding)
                    print >>OUT, "<%s%s>" % (elem.encode(encoding), attrstring)
                    old_attr_values[elem] = new_attr_values[elem]

            # Whitespace and / needs to be replaced for CQP parsing to work. / is only allowed in the word itself.
            line = "\t".join(cols.get(n, UNDEF).replace(" ", "_").replace("/", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if n > structs_count else cols.get(n, UNDEF).replace(" ", "_").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for n in column_nrs)
            print >>OUT, remove_control_characters(line).encode(encoding)

        for elem, _attrs in structs:
            if old_attr_values[elem]:
                print >>OUT, "</%s>" % elem.encode(encoding)

    util.log.info("Exported %d tokens, %d columns, %d structs: %s", len(tokens), len(column_nrs), len(structs), out)


def fmt(x, encoding='utf-8'):
    return remove_control_characters(x).encode(encoding)


def write_labels(out, tokens, vrt):
    """Write a structural attribute to out, separated by lines.

    Each entry in vrt should have one column: the struct.

    >>> tokens = [u"w:1", u"w:2", u"w:3", u"w:4", u"w:5"]
    >>> vrt = {
    ...     u"w:1": [[1, u"A"]],
    ...     u"w:2": [[2, u"B"]],
    ...     u"w:3": [[2, u"B"]],
    ...     u"w:4": [[3, u"B"]],
    ...     u"w:5": [[3, u"B"]]
    ... }
    >>> with tempfile.NamedTemporaryFile() as out:
    ...     write_labels(out.name, tokens, vrt)
    ...     print out.read(),
    A
    B
    B
    """
    lines = 0
    with open(out, "w") as OUT:
        for label, _ in vrt_iterate(tokens, vrt, project=lambda *_: None):
            print >>OUT, fmt(label)
            lines += 1

    util.log.info("Exported %s lines to %s", lines, out)


def vrt_iterate(tokens, vrt, project=lambda col: col[1],
                             project_struct=lambda label, _last_token: label):
    """
    Yields documents from vrt separated using the first column in vrt,
    together with each token's column projected using the supplied function.

    >>> tokens = [u"w:1", u"w:2", u"w:3", u"w:4", u"w:5"]
    >>> vrt = {
    ...     u"w:1": [[1, u"A"], u"word1", u"pos1"],
    ...     u"w:2": [[2, u"B"], u"word2", u"pos2"],
    ...     u"w:3": [[2, u"B"], u"word3", u"pos3"],
    ...     u"w:4": [[3, u"B"], u"word4", u"pos4"],
    ...     u"w:5": [[3, u"B"], u"word5", u"pos5"]
    ... }
    >>> list(vrt_iterate(tokens, vrt))          # doctest: +NORMALIZE_WHITESPACE
    [(u'A', [u'word1']),
     (u'B', [u'word2', u'word3']),
     (u'B', [u'word4', u'word5'])]
    >>> pos = lambda col: col[2]
    >>> list(vrt_iterate(tokens, vrt, project=pos))
    ...                                         # doctest: +NORMALIZE_WHITESPACE
    [(u'A', [u'pos1']),
     (u'B', [u'pos2', u'pos3']),
     (u'B', [u'pos4', u'pos5'])]
    >>> last_tok = lambda _label, tok: tok
    >>> list(vrt_iterate(tokens, vrt, project_struct=last_tok))
    ...                                         # doctest: +NORMALIZE_WHITESPACE
    [(u'w:1', [u'word1']),
     (u'w:3', [u'word2', u'word3']),
     (u'w:5', [u'word4', u'word5'])]
    """
    words = []
    for tok, next_tok in it.izip(tokens, it.chain(tokens[1:], (None,))):

        words.append(project(vrt[tok]))

        if next_tok is None:
            next = None
        else:
            next, _label = vrt[next_tok][0]

        now, label = vrt[tok][0]
        if now != next:
            yield project_struct(label, tok), words
            words = []


def write_words(out, tokens, vrt):
    """Write the tokens to out, separated by line at each structural boundary.

    Each entry in vrt should have two columns: first struct, then word.

    >>> tokens = [u"w:1", u"w:2", u"w:3", u"w:4", u"w:5"]
    >>> vrt = {
    ...     u"w:1": [[1, u"A"], u"word1"],
    ...     u"w:2": [[2, u"B"], u"word2"],
    ...     u"w:3": [[2, u"B"], u"word3"],
    ...     u"w:4": [[3, u"B"], u"word4"],
    ...     u"w:5": [[3, u"B"], u"word5"]
    ... }
    >>> with tempfile.NamedTemporaryFile() as out:
    ...     write_words(out.name, tokens, vrt)
    ...     print out.read(),
    word1
    word2 word3
    word4 word5
    """
    lines = 0
    with open(out, "w") as OUT:
        for _, words in vrt_iterate(tokens, vrt):
            print >>OUT, ' '.join(fmt(w) for w in words)
            lines += 1

    util.log.info("Exported %d tokens in %s lines to %s", len(tokens), lines, out)


def write_xml(out, structs, structs_count, columns, column_nrs, tokens, vrt, fileid, fileids, valid_xml, encoding):
    """ The XML part of the 'export' function: write annotations to a valid xml file, unless valid_xml == False.

    >>> with tempfile.NamedTemporaryFile() as fileids:
    ...     util.write_annotation(fileids.name, {"fileid": "kokkonster"})
    ...     with tempfile.NamedTemporaryFile() as out:
    ...         write_xml(out.name,
    ...                   fileid="fileid",
    ...                   fileids=fileids.name,
    ...                   valid_xml=True,
    ...                   encoding="utf8",
    ...                   **example_data())
    ...         print(out.read())
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
    ...                       encoding="utf8",
    ...                       **example_overlapping_data())
    ...             print(out.read())
    <!-- valid_xml: True -->
    <corpus>
    <b>
    <w>bold</w>
    <i _id="typography-1">
    <w>bold_italic</w>
    </i>
    </b>
    <i _id="typography-1">
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

    fileid = util.read_annotation(fileids)[fileid].encode(encoding)
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
                    invalid_str_buffer.append("</%s>" % elem.encode(encoding))

                # Check for overlap
                while elem != open_tag_stack[-1][0]:
                    overlap = True
                    # Close top stack element, remember to re-open later
                    str_buffer.append("</%s>" % open_tag_stack[-1][0].encode(encoding))
                    pending_tag_stack.append(open_tag_stack.pop())

                # Fix pending tags
                while pending_tag_stack:
                    if elem == open_tag_stack[-1][0]:
                        str_buffer.append("</%s>" % elem.encode(encoding))
                        open_tag_stack.pop()
                    # Re-open pending tag
                    pending_elem, attrstring = pending_tag_stack[-1]
                    if not elemids.get(pending_elem):
                        elemid += 1
                        elemids[pending_elem] = elemid
                    line = '<%s _id="%s-%s"%s>' % (pending_elem.encode(encoding), fileid, elemids[pending_elem], attrstring)
                    str_buffer.append(line)
                    open_tag_stack.append(pending_tag_stack.pop())
                    old_attr_values[elem] = None

                # Close last open tag from overlap
                if elem == open_tag_stack[-1][0] and not pending_tag_stack:
                    str_buffer.append("</%s>" % elem.encode(encoding))
                    open_tag_stack.pop()
                    old_attr_values[elem] = None
                    elemids = {}

        # Open tags
        for elem, _attrs in reversed(structs):
            if any(x[1][0] for x in new_attr_values[elem]) and new_attr_values[elem] != old_attr_values[elem]:
                attrstring = ''.join(' %s="%s"' % (attr, val[1].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))
                                     for (attr, val) in new_attr_values[elem] if val and not attr == UNDEF).encode(encoding)
                line = "<%s%s>" % (elem.encode(encoding), attrstring)
                str_buffer.append(line)
                old_attr_values[elem] = new_attr_values[elem]
                open_tag_stack.append((elem, attrstring))
                if not valid_xml:
                    invalid_str_buffer.append("<%s%s>" % (elem.encode(encoding), attrstring))

        # Add word annotations
        word = cols.get(structs_count, UNDEF).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        attrstring = "".join(' %s="%s"' % (columns[n-structs_count], cols.get(n, UNDEF).replace("&", "&amp;").replace('"', '&quot;').replace("<", "&lt;").replace(">", "&gt;")) for n in column_nrs[1:] if cols.get(n))
        line = "<w%s>%s</w>" % (attrstring, word)
        str_buffer.append(remove_control_characters(line).encode(encoding))
        if not valid_xml:
            invalid_str_buffer.append(remove_control_characters(line).encode(encoding))

    # Close remaining open tags
    if open_tag_stack:
        for elem in reversed(open_tag_stack):
            str_buffer.append("</%s>" % elem[0].encode(encoding))
    if not valid_xml:
        for elem, _attrs in structs:
            if old_attr_values[elem]:
                invalid_str_buffer.append("</%s>" % elem.encode(encoding))

    str_buffer.append("</corpus>")
    invalid_str_buffer.append("</corpus>")

    # Convert str_buffer list to string
    str_buffer = "\n".join(str_buffer)
    invalid_str_buffer = "\n".join(invalid_str_buffer)

    if not valid_xml:
        # Write string buffer to invalid xml file
        with open(out, "w") as OUT:
            print >>OUT, invalid_str_buffer
    elif not overlap:
        # Write string buffer
        with open(out, "w") as OUT:
            print >>OUT, str_buffer
    else:
        # Go through xml structure and add missing _id attributes
        xmltree = etree.ElementTree(etree.fromstring(str_buffer))
        for child in xmltree.getroot().iter():
            # If child has and id, get previous element with same tag
            if child.tag != "w" and child.attrib.get("_id"):
                elemlist = list(xmltree.getroot().iter(child.tag))
                if child != elemlist[0]:
                    prev_elem = elemlist[elemlist.index(child) - 1]
                    # If previous element has no id, add id of child
                    if not prev_elem.attrib.get("_id"):
                        prev_elem.set('_id', child.attrib.get("_id"))
        xmltree.write(out, encoding=encoding, xml_declaration=False, method="xml")

    util.log.info("Exported %d tokens, %d columns, %d structs: %s", len(tokens), len(column_nrs), len(structs), out)


def combine_xml(master, out, xmlfiles="", xmlfiles_list=""):
    assert master != "", "Master not specified"
    assert out != "", "Outfile not specified"
    assert (xmlfiles or xmlfiles_list), "Missing source"

    if xmlfiles:
        if isinstance(xmlfiles, basestring): xmlfiles = xmlfiles.split()
    elif xmlfiles_list:
        with open(xmlfiles_list) as insource:
            xmlfiles = [line.strip() for line in insource]

    xmlfiles.sort()

    with open(out, "w") as OUT:
        print >>OUT, '<corpus id="%s">' % master.replace("&", "&amp;").replace('"', '&quot;')
        for infile in xmlfiles:
            util.log.info("Read: %s", infile)
            with open(infile, "r") as IN:
                # Append everything but <corpus> and </corpus>
                print >>OUT, IN.read()[9:-10],
        print >>OUT, "</corpus>"
        util.log.info("Exported: %s" % out)


def cwb_encode(master, columns, structs=(), vrtdir=None, vrtfiles=None,
               encoding=CWB_ENCODING, datadir=CWB_DATADIR, registry=CORPUS_REGISTRY, skip_compression=False, skip_validation=False):
    """
    Encode a number of VRT files, by calling cwb-encode.
    params, structs describe the attributes that are exported in the VRT files.
    """
    assert master != "", "Master not specified"
    assert bool(vrtdir) != bool(vrtfiles), "Either VRTDIR or VRTFILES must be specified"
    assert datadir, "CWB_DATADIR not specified"
    assert registry, "CORPUS_REGISTRY not specified"
    if isinstance(skip_validation, basestring):
        skip_validation = (skip_validation.lower() == "true")
    if isinstance(skip_compression, basestring):
        skip_compression = (skip_compression.lower() == "true")
    if isinstance(vrtfiles, basestring):
        vrtfiles = vrtfiles.split()
    if isinstance(columns, basestring):
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
    if vrtfiles:
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
        print >>F, result
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
            print >>F
            print >>F, "# Added by cwb.py"
            print >>F, "ALIGNED", other
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
    >>> parse_structural_attributes('s - text:title text:author')
    [('s', [(u'__UNDEF__', 0)]), ('text', [('title', 2), ('author', 3)])]
    """

    if isinstance(structural_atts, basestring):
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
    return text.translate(dict((ord(c), None) for c in [chr(i) for i in range(9) + range(11, 13) + range(14, 32) + [127]]))


class DictWithWithout(dict):
    """A dictionary with an without function that excludes some elements."""

    def without(self, *keys):
        """
        Returns a copy of the dictionary without these keys.

        >>> DictWithWithout(apa=1, bepa=2).without("apa")
        {'bepa': 2}
        """
        return DictWithWithout(
            **{k: v for k, v in self.iteritems() if k not in keys})


def example_data():
    """Example data to test the write_* functions."""
    # Structs come in the reverse nesting order:
    structs = [["s", [[UNDEF, 0]]],
               ["text", [["title", 1], ["author", 2]]]]
    structs_count = 3
    columns = ["word", "pos"]
    column_nrs = [3, 4]
    # The names and the order of the tokens:
    tokens = [u"w:1", u"w:2", u"w:3", u"w:4"]
    vrt = {
        u"w:1": ListWithGet([
            [1, u""],
            [1, u"Kokboken"],
            [1, u"Jane Oliver"],
            u"Ett",
            u"DT"
        ]),
        u"w:2": ListWithGet([
            [1, u""],
            [1, u"Kokboken"],
            [1, u"Jane Oliver"],
            u"exempel",
            u"NN"
        ]),
        u"w:3": ListWithGet([
            [2, u""],
            [1, u"Kokboken"],
            [1, u"Jane Oliver"],
            u"Banankaka",
            u"NN"
        ]),
        u"w:4": ListWithGet([
            [3, u""],
            [2, u"Nya kokboken"],
            [2, u"Jane Oliver"],
            u"Flambera",
            u"VB"
        ])
      }
    return DictWithWithout(**locals())


def example_overlapping_data():
    """Overlapping data to test the write_* functions."""
    structs = [["b", [[UNDEF, 0]]], ["i", [[UNDEF, 1]]]]
    structs_count = 2
    columns = ["word"]
    column_nrs = [2]
    tokens = [u"w:1", u"w:2", u"w:3"]
    vrt = {
        u"w:1": ListWithGet([
            [1, u""],
            [],
            u"bold"
        ]),
        u"w:2": ListWithGet([
            [1, u""],
            [2, u""],
            u"bold_italic"
        ]),
        u"w:3": ListWithGet([
            [],
            [2, u""],
            u"italic"
        ]),
      }
    return DictWithWithout(**locals())


if __name__ == '__main__':
    util.run.main(export=export,
                  encode=cwb_encode,
                  align=cwb_align,
                  combine_xml=combine_xml)
