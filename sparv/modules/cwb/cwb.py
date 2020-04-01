"""Tools for exporting, encoding and aligning corpora for Corpus Workbench."""

import os
from glob import glob

import sparv.util as util

ALIGNDIR = "annotations/align"

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
      to be kept. If not specified, everything will be kept.
    """
    # Create export dir
    os.makedirs(os.path.dirname(export_dir), exist_ok=True)

    # Read words
    word_annotation = list(util.read_annotation(doc, word))

    # Add original_annotations to annotations
    annotations = util.split_tuples_list(annotations)
    original_annotations = util.split_tuples_list(original_annotations)
    if not original_annotations:
        original_annotations = util.split_tuples_list(util.read_data(doc, "@structure"))
    annotations.extend(original_annotations)

    # Create dictionary for renamed annotations
    annotation_names = dict((a, b) for a, b in annotations if b)

    # Get the names of all token annotations (but not token itself)
    token_annotations = [util.split_annotation(i[0])[1] for i in annotations if util.split_annotation(i[0])[0] == token and i[0] != token]

    spans_dict, annotation_dict = util.gather_annotations(doc, [i[0] for i in annotations])

    # Go through spans_dict and add to vrt, line by line
    vrt = []
    for pos, spans in sorted(spans_dict.items()):
        for instruction, name, index in spans:

            # Create token line
            if name == token and instruction == "open":
                vrt.append(make_token_line(word_annotation[index], token, token_annotations, annotation_dict, index))

            # Create line with structural annotation
            elif name != token:
                annot_name = annotation_names.get(name, name)
                # Open structural element
                if instruction == "open":
                    attrs = make_attr_str(name, annotation_dict, annotation_names, index)
                    if attrs:
                        vrt.append("<%s %s>" % (annot_name, attrs))
                    else:
                        vrt.append("<%s>" % annot_name)
                # Close element
                else:
                    vrt.append("</%s>" % annot_name)

    # Write result to file
    vrt = "\n".join(vrt)
    out_file = os.path.join(export_dir, "%s_export.vrt" % doc)
    with open(out_file, "w") as f:
        f.write(vrt)
    util.log.info("Exported: %s", out_file)


def make_attr_str(annotation, annotation_dict, annotation_names, index):
    """Create a string with attributes and values for a struct element."""
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        if name != "@span":
            annot_name = annotation_names.get(":".join([annotation, name]), name)
            # Escape special characters in value
            value = annot[index].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            attrs.append('%s="%s"' % (annot_name, value))
    return " ".join(attrs)


def make_token_line(word, token, token_annotations, annotation_dict, index):
    """Create a string with the token and its annotations.

    Whitespace and / need to be replaced for CQP parsing to work. / is only allowed in the word itself.
    """
    line = [word.replace(" ", "_").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")]
    for attr in token_annotations:
        if attr not in annotation_dict[token]:
            attr_str = util.UNDEF
        else:
            attr_str = annotation_dict[token][attr][index]
        line.append(attr_str.replace(" ", "_").replace("/", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    line = "\t".join(line)
    return util.remove_control_characters(line)


def cwb_encode(corpus, columns, structs=(), vrtdir=None, vrtfiles=None, vrtlist=None,
               encoding=CWB_ENCODING, datadir=CWB_DATADIR, registry=CORPUS_REGISTRY, skip_compression=False, skip_validation=False):
    """Encode a number of vrt files, by calling cwb-encode.

    params, structs describe the attributes that are exported in the vrt files.
    """
    assert corpus != "", "Corpus not specified"
    assert util.single_true((vrtdir, vrtfiles, vrtlist)), "One of the following must be specified: vrtdir, vrtfiles, vrtlist"
    assert datadir, "CWB_DATADIR not specified"
    assert registry, "CORPUS_REGISTRY not specified"

    skip_validation = util.strtobool(skip_validation)
    skip_compression = util.strtobool(skip_compression)
    vrtfiles = util.split(vrtfiles)
    columns = util.split(columns)
    structs = parse_structural_attributes(structs)

    corpus_registry = os.path.join(registry, corpus)
    corpus_datadir = os.path.join(datadir, corpus)
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
        attrs2 = "+".join(attr for attr, _n in attrs if not attr == util.UNDEF)
        if attrs2:
            attrs2 = "+" + attrs2
        encode_args += ["-S", "%s:0%s" % (struct, attrs2)]

    if vrtlist:
        # Use xargs to avoid "Argument list too long" problems
        util.system.call_binary("cwb-encode", raw_command="cat %s | xargs cat | %%s %s" % (vrtlist, " ".join(encode_args)), verbose=True, use_shell=True)
    else:
        util.system.call_binary("cwb-encode", encode_args, verbose=True)

    index_args = ["-V", "-r", registry, corpus.upper()]
    util.system.call_binary("cwb-makeall", index_args, verbose=True)
    util.log.info("Encoded and indexed %d columns, %d structs", len(columns), len(structs))

    if not skip_compression:
        util.log.info("Compressing corpus files...")
        compress_args = ["-A", corpus.upper()]
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


def cwb_align(corpus, other, link, aligndir=ALIGNDIR, encoding=CWB_ENCODING):
    """Align 'corpus' with 'other' corpus, using the 'link' annotation for alignment."""
    os.makedirs(aligndir, exist_ok=True)
    alignfile = os.path.join(aligndir, corpus + ".align")
    util.log.info("Aligning %s <-> %s", corpus, other)

    try:
        [(link_name, [(link_attr, _path)])] = parse_structural_attributes(link)
    except ValueError:
        raise ValueError("You have to specify exactly one alignment link.")
    link_attr = link_name + "_" + link_attr

    # Align linked chunks
    args = ["-v", "-o", alignfile, "-V", link_attr, corpus, other, link_name]
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
    regfile = os.path.join(os.environ["CORPUS_REGISTRY"], corpus)
    with open(regfile, "r") as F:
        skip_align = ("ALIGNED %s" % other) in F.read()

    if not skip_align:
        with open(regfile, "a") as F:
            print(file=F)
            print("# Added by cwb.py", file=F)
            print("ALIGNED", other, file=F)
        util.log.info("Added alignment to registry: %s", regfile)
    # args = [corpus, ":add", ":a", other]
    # result, _ = util.system.call_binary("cwb-regedit", args, verbose=True)
    # util.log.info("%s", result.strip())

    # Encode the alignments into CWB
    args = ["-v", "-D", alignfile]
    result, _ = util.system.call_binary("cwb-align-encode", args, encoding=encoding, verbose=True)
    util.log.info("%s", result.strip())


def parse_structural_attributes(structural_atts):
    """Parse a list of annotations (element:attribute) into a list of tuples.

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
            attr = util.UNDEF
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
