"""Tools for exporting, encoding and aligning corpora for Corpus Workbench."""

import logging
import os
from glob import glob
from typing import Optional

import sparv.util as util
from sparv import (AllDocuments, Annotation, Config, Corpus, Document, Export, ExportAnnotations, ExportInput,
                   exporter)
from sparv.core import paths

log = logging.getLogger(__name__)


@exporter("VRT export")
def vrt(doc: str = Document,
        out: str = Export("vrt/{doc}.vrt"),
        token: str = Annotation("<token>"),
        word: str = Annotation("<token:word>"),
        annotations: list = ExportAnnotations(export_type="vrt_export"),
        original_annotations: Optional[list] = Config("vrt_export.original_annotations"),
        remove_namespaces: bool = Config("export.remove_export_namespaces", False)):
    """Export annotations to vrt in export_dir.

    - doc: name of the original document
    - word: annotation containing the token strings.
    - annotations: list of elements:attributes (annotations) to include.
    - original_annotations: list of elements:attributes from the original document
      to be kept. If not specified, everything will be kept.
    """
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Read words
    word_annotation = list(util.read_annotation(doc, word))

    # Get annotation spans, annotations list etc.
    annotations, token_annotations, export_names = util.get_annotation_names(doc, token, annotations,
                                                                             original_annotations, remove_namespaces)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names)

    # Go through spans_dict and add to vrt, line by line
    vrt = []
    for _pos, instruction, span in span_positions:
        # Create token line
        if span.name == token and instruction == "open":
            vrt.append(make_token_line(word_annotation[span.index], token, token_annotations, annotation_dict,
                                       span.index))

        # Create line with structural annotation
        elif span.name != token:
            # Open structural element
            if instruction == "open":
                attrs = make_attr_str(span.name, annotation_dict, export_names, span.index)
                if attrs:
                    vrt.append("<%s %s>" % (span.export, attrs))
                else:
                    vrt.append("<%s>" % span.export)
            # Close element
            else:
                vrt.append("</%s>" % span.export)

    # Write result to file
    vrt = "\n".join(vrt)
    with open(out, "w") as f:
        f.write(vrt)
    log.info("Exported: %s", out)


def make_attr_str(annotation, annotation_dict, export_names, index):
    """Create a string with attributes and values for a struct element."""
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(":".join([annotation, name]), name)
        # Escape special characters in value
        value = annot[index].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        attrs.append('%s="%s"' % (export_name, value))
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


@exporter("CWB encode", config=[
    Config("cwb.corpus_registry", default=paths.corpus_registry),
    Config("cwb.cwb_datadir", default=paths.cwb_datadir),
    Config("cwb.encoding", default=paths.cwb_encoding),
    Config("cwb.skip_compression", False),
    Config("cwb.skip_validation", False)
])
def encode(corpus: str = Corpus,
           annotations: str = ExportAnnotations(export_type="vrt_export", is_input=False),
           original_annotations: Optional[list] = Config("vrt_export.original_annotations"),
           docs: list = AllDocuments,
           words: str = Annotation("<token:word>", all_docs=True),
           vrtfiles: str = ExportInput("vrt/{doc}.vrt", all_docs=True),
           out: str = Export("[cwb.corpus_registry]/[id]", absolute_path=True),
           token: str = Annotation("<token>", all_docs=True),
           encoding: str = Config("cwb.encoding"),
           datadir: str = Config("cwb.cwb_datadir"),
           registry: str = Config("cwb.corpus_registry"),
           remove_namespaces: bool = Config("remove_export_namespaces", False),
           skip_compression: Optional[bool] = Config("cwb.skip_compression"),
           skip_validation: Optional[bool] = Config("cwb.skip_validation")):
    """Encode a number of vrt files, by calling cwb-encode."""
    assert datadir, "CWB_DATADIR not specified"
    assert registry, "CORPUS_REGISTRY not specified"

    # Get vrt files
    vrtfiles = [vrtfiles.replace("{doc}", doc) for doc in docs]
    vrtfiles.sort()

    # Word annotation should always be included in CWB export
    annotations.insert(0, words)

    # Get annotation names
    annotations, token_annotations, export_names = util.get_annotation_names(docs, token, annotations,
                                                                             original_annotations, remove_namespaces,
                                                                             keep_struct_refs=True)

    # Get VRT columns and structs
    token_annotations = [(token + ":" + i) for i in token_annotations]
    columns = [export_names.get(i, i) for i in token_annotations]
    struct_annotations = [export_names.get(i, i) for i in annotations if not i.startswith(token)]
    structs = parse_structural_attributes(struct_annotations)

    corpus_registry = os.path.join(registry, corpus)
    corpus_datadir = os.path.join(datadir, corpus)
    util.system.clear_directory(corpus_datadir)

    encode_args = ["-s", "-p", "-",
                   "-d", corpus_datadir,
                   "-R", corpus_registry,
                   "-c", encoding,
                   "-x"
                   ]

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

    util.system.call_binary("cwb-encode", encode_args, verbose=True)
    # Use xargs to avoid "Argument list too long" problems
    # util.system.call_binary("cwb-encode", raw_command="cat %s | xargs cat | %%s %s" % (vrtfiles, " ".join(encode_args)), verbose=True, use_shell=True)

    index_args = ["-V", "-r", registry, corpus.upper()]
    util.system.call_binary("cwb-makeall", index_args, verbose=True)
    log.info("Encoded and indexed %d columns, %d structs", len(columns), len(structs))

    if not skip_compression:
        log.info("Compressing corpus files...")
        compress_args = ["-A", corpus.upper()]
        if skip_validation:
            compress_args.insert(0, "-T")
            log.info("Skipping validation")
        # Compress token stream
        util.system.call_binary("cwb-huffcode", compress_args)
        log.info("Removing uncompressed token stream...")
        for f in glob(os.path.join(corpus_datadir, "*.corpus")):
            os.remove(f)
        # Compress index files
        util.system.call_binary("cwb-compress-rdx", compress_args)
        log.info("Removing uncompressed index files...")
        for f in glob(os.path.join(corpus_datadir, "*.corpus.rev")):
            os.remove(f)
        for f in glob(os.path.join(corpus_datadir, "*.corpus.rdx")):
            os.remove(f)
        log.info("Compression done.")


# TODO: Add snake-support!
def cwb_align(corpus, other, link, aligndir="annotations/align", encoding: str = Config("cwb.encoding", "utf8")):
    """Align 'corpus' with 'other' corpus, using the 'link' annotation for alignment."""
    os.makedirs(aligndir, exist_ok=True)
    alignfile = os.path.join(aligndir, corpus + ".align")
    log.info("Aligning %s <-> %s", corpus, other)

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
    log.info("%s", lastline.strip())
    if " 0 alignment" in lastline.strip():
        log.warning("No alignment regions created")
    log.info("Alignment file/result: %s/.result", alignfile)

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
        log.info("Added alignment to registry: %s", regfile)
    # args = [corpus, ":add", ":a", other]
    # result, _ = util.system.call_binary("cwb-regedit", args, verbose=True)
    # log.info("%s", result.strip())

    # Encode the alignments into CWB
    args = ["-v", "-D", alignfile]
    result, _ = util.system.call_binary("cwb-align-encode", args, encoding=encoding, verbose=True)
    log.info("%s", result.strip())


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

        # Why did we not allow "." before? I can see no problems with CWB, so let's allow "." for now.
        # assert not struct or struct == "-" or "." not in struct, "Struct should contain ':' or be equal to '-': %s" % struct

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
    util.run.main(align=cwb_align)
