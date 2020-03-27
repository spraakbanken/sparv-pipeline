"""Tools for exporting, encoding and aligning corpora for Corpus Workbench."""

import os
from glob import glob

import sparv.util as util

ALIGNDIR = "annotations/align"
UNDEF = "__UNDEF__"

CWB_ENCODING = os.environ.get("CWB_ENCODING", "utf8")
CWB_DATADIR = os.environ.get("CWB_DATADIR")
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


def export(doc, export_dir, token, word, annotations, original_annotations=None):
    """Export annotations to vrt in export_dir.

    - doc: name of the original document
    - token: name of the token level annotation span
    - word: annotation containing the token strings.
    - annotations: list of elements:attributes (annotations) to include.
    - original_annotations: list of elements:attributes from the original document
      to be kept. If not specified, everything will be kep.
    """
    # TODO: cwb needs a fixed order of attributes... how do we guarantee this?
    # TODO: certain characters need to be escaped in order to make cwb happy:

    # # Whitespace and / needs to be replaced for CQP parsing to work. / is only allowed in the word itself.
    # line = "\t".join(cols.get(n, UNDEF).replace(" ", "_").replace("/", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if n > structs_count else cols.get(n, UNDEF).replace(" ", "_").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for n in column_nrs)
    # print(util.remove_control_characters(line), file=OUT)

    # Create export dir
    os.makedirs(os.path.dirname(export_dir), exist_ok=True)

    # Read words
    word_annotation = list(util.read_annotation(doc, word))

    # Add original_annotations to annotations
    annotations = util.split(annotations)
    original_annotations = util.split(original_annotations)
    if not original_annotations:
        original_annotations = util.split(util.read_data(doc, "@structure"))
    annotations.extend(original_annotations)

    sorted_spans, annotation_dict = util.gather_annotations(doc, annotations)

    vrt = []
    open_elements = []

    # Go through sorted_spans and add to vrt, line by line
    for span in sorted_spans:
        # Close element and pop stack if top stack element is no parent to current span
        while len(open_elements) and not util.is_child(span[0], open_elements[-1][0]):
            vrt.append("</%s>" % open_elements[-1][1])
            open_elements.pop()
        # Create token line
        if span[1] == token:
            tline = [word_annotation[span[2]]]
            tline.extend(token_annotations(token, annotation_dict, span[2]))
            vrt.append("\t".join(tline))
        # Create line with structural info
        else:
            open_elements.append(span)
            attrs = make_attr_str(span[1], annotation_dict, span[2])
            vrt.append("<%s %s>" % (span[1], attrs))

    # Close remaining open elements
    while len(open_elements):
        vrt.append("</%s>" % open_elements[-1][1])
        open_elements.pop()

    # Write result to file
    vrt = "\n".join(vrt)
    out_file = os.path.join(export_dir, "%s_export.vrt" % doc)
    with open(out_file, "w") as f:
        f.write(vrt)
    util.log.info("Exported: %s", out_file)


def make_attr_str(annotation, annotation_dict, index):
    """Create a string with attributes and values for a struct element."""
    attrs = []
    for name, annotation in annotation_dict[annotation].items():
        if name != "@span":
            attrs.append('%s="%s"' % (name, annotation[index]))
    return " ".join(attrs)


def token_annotations(token, annotation_dict, index):
    """Return iterator for token annotations."""
    # TODO: Order attributes
    # TODO: Handle missing attrs with UNDEF
    for name, annotation in annotation_dict[token].items():
        if name != "@span":
            yield annotation[index]


def write_vrt(out, structs, structs_count, column_nrs, tokens, vrt):
    """Kept as reference for now, to be removed soon."""
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


######################################################################
# Saving as Corpus Workbench data file


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


if __name__ == "__main__":
    util.run.main(export=export,
                  encode=cwb_encode,
                  align=cwb_align)
