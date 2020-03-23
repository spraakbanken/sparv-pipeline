"""Tools for exporting, encoding and aligning corpora for Corpus Workbench."""

import os
from glob import glob
from collections import defaultdict
import itertools as it

import sparv.util as util

ALIGNDIR = "annotations/align"
UNDEF = "__UNDEF__"

CWB_ENCODING = os.environ.get("CWB_ENCODING", "utf8")
CWB_DATADIR = os.environ.get("CWB_DATADIR")
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


######################################################################
# Saving as Corpus Workbench data file

class ListWithGet(list):
    """Lists with a get function just like dict's."""

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


def vrt_table(annotations_structs, annotations_columns, text, token):
    """
    Return a table suitable for printing as a vrt file from annotations.

    The structs are a pair of annotation and its parent.
    """
    structs_count = len(annotations_structs)
    parents = {}

    text = util.corpus.read_corpus_text(text)
    token = list(util.read_annotation_iterkeys(token))

    for annot in annotations_structs:
        if annot not in parents:
            parents[annot] = util.get_parents(text, None, annot, token, orphan_alert=True)

    vrt = defaultdict(ListWithGet)

    for annot in annotations_structs:
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
            in list(parents[annot].items())
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


def tokens_and_vrt(order, annotations_structs, annotations_columns, text, token):
    """Return the tokens in order and the vrt table."""
    vrt = vrt_table(annotations_structs, annotations_columns, text, token)
    sortkey = util.read_annotation(order).get
    tokens = sorted(vrt, key=sortkey)
    return tokens, vrt


def export(format, out, order, annotations_columns, annotations_structs, text=None, token=None, fileid=None, fileids=None, valid_xml=True, columns=(), structs=(), encoding=CWB_ENCODING):
    """Export 'annotations' to the VRT or XML file 'out'.

    The order of the annotation keys is decided by the annotation 'order'.
    The columns to be exported are taken from 'columns', default all 'annotations'.
    The structural attributes are specified by 'structs', default no structs.
    If an attribute in 'columns' or 'structs' is "-", that annotation is skipped.
    The structs are specified by "elem:attr", giving <elem attr=N> xml tags.
    """
    assert format in ("vrt", "xml", "formatted"), "Wrong format specified"
    if isinstance(annotations_columns, str):
        annotations_columns = annotations_columns.split()
    if isinstance(annotations_structs, str):
        annotations_structs = [x for x in annotations_structs.split()]

    if isinstance(columns, str):
        columns = columns.split()
    if isinstance(columns, str):
        structs_count = len(structs.split())
    else:
        structs_count = len(structs)
    structs = parse_structural_attributes(structs)

    assert len(annotations_columns) == len(columns), "columns and annotations_columns must contain same number of values"
    assert len(annotations_structs) == structs_count, "structs and annotations_structs must contain same number of values"

    valid_xml = util.strtobool(valid_xml)

    if format == "formatted":
        write_formatted(out, annotations_columns, annotations_structs, columns, structs, structs_count, text)
    else:
        tokens, vrt = tokens_and_vrt(order, annotations_structs, annotations_columns, text, token)
        column_nrs = [n + structs_count for (n, col) in enumerate(columns) if col and col != "-"]

        if format == "vrt":
            write_vrt(out, structs, structs_count, column_nrs, tokens, vrt)
        elif format == "xml":
            write_xml(out, structs, structs_count, columns, column_nrs, tokens, vrt, fileid, fileids, valid_xml)


def write_vrt(out, structs, structs_count, column_nrs, tokens, vrt):
    r"""Write annotations to vrt file 'out'.

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
            print(util.remove_control_characters(line), file=OUT)

        for elem, _attrs in structs:
            if old_attr_values[elem]:
                print("</%s>" % elem, file=OUT)

    util.log.info("Exported %d tokens, %d columns, %d structs: %s", len(tokens), len(column_nrs), len(structs), out)


def cwb_encode(master, columns, structs=(), vrtdir=None, vrtfiles=None, vrtlist=None,
               encoding=CWB_ENCODING, datadir=CWB_DATADIR, registry=CORPUS_REGISTRY, skip_compression=False, skip_validation=False):
    """Encode a number of VRT files, by calling cwb-encode.

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


def cwb_align(master, other, link, aligndir=ALIGNDIR, encoding=CWB_ENCODING):
    """Align 'master' corpus with 'other' corpus, using the 'link' annotation for alignment."""
    os.makedirs(aligndir, exist_ok=True)
    alignfile = os.path.join(aligndir, master + ".align")
    util.log.info("Aligning %s <-> %s", master, other)

    try:
        [(link_name, [(link_attr, _path)])] = parse_structural_attributes(link)
    except ValueError:
        raise ValueError("You have to specify exactly one alignment link.")
    link_attr = link_name + "_" + link_attr

    # Align linked chunks
    args = ["-v", "-o", alignfile, "-V", link_attr, master, other, link_name]
    result, _ = util.system.call_binary("cwb-align", args, encoding=encoding, verbose=True)
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
    result, _ = util.system.call_binary("cwb-align-encode", args, encoding=encoding, verbose=True)
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
                  align=cwb_align)
